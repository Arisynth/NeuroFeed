import schedule
import time
import threading
import logging
import queue
import sys  # Add the missing sys import
from datetime import datetime, timedelta
from core.config_manager import load_config, save_config, get_tasks, save_task
from core.rss_parser import RssParser
from ai_processor.filter import ContentFilter
from ai_processor.summarizer import NewsSummarizer
from typing import Dict, List, Any
from core.email_sender import EmailSender, EmailSendError
from .news_db_manager import NewsDBManager
from .log_manager import LogManager
from core.status_manager import StatusManager
from core.task_status import TaskStatus

# 替换现有的日志设置
log_manager = LogManager()
logger = log_manager.get_logger("scheduler")

# Global variables for task queue management
task_queue = queue.Queue()
task_processing_thread = None
is_task_running = False
task_lock = threading.Lock()  # For thread-safe operations on shared variables

def execute_task(task_id=None):
    """将任务放入队列而不是直接执行"""
    logger.info(f"将任务 ID:{task_id or '所有任务'} 放入执行队列")
    task_queue.put(task_id)
    ensure_processor_running()

def process_task_queue():
    """处理任务队列的后台线程"""
    global is_task_running
    
    logger.info("任务队列处理线程已启动")
    
    while True:
        try:
            # 从队列获取下一个任务
            task_id = task_queue.get(block=True, timeout=300)  # 5分钟超时
            
            with task_lock:
                is_task_running = True
            
            logger.info(f"\n=====================================================")
            logger.info(f"从队列中取出任务 ID:{task_id or '所有任务'} 开始执行")
            logger.info(f"队列中剩余任务数量: {task_queue.qsize()}")
            logger.info(f"=====================================================\n")
            
            try:
                # 实际执行任务
                _execute_task(task_id)
                logger.info(f"任务 ID:{task_id or '所有任务'} 执行完成")
                
            except Exception as e:
                # 捕获任务执行过程中的异常，但不退出线程
                import traceback
                logger.error(f"执行任务 ID:{task_id} 时发生异常: {str(e)}")
                logger.error(f"异常详情:\n{traceback.format_exc()}")
                
                # 通知状态管理器任务失败
                try:
                    status_manager = StatusManager()
                    status_manager.update_task(
                        task_id,
                        status=TaskStatus.FAILED,
                        message=f"任务执行失败: {str(e)}",
                        error=str(e)
                    )
                except Exception as status_error:
                    logger.error(f"更新任务状态失败: {str(status_error)}")
            
            finally:
                # 无论发生什么，确保标记队列任务完成
                task_queue.task_done()
                
                with task_lock:
                    is_task_running = False
                    
                logger.info(f"\n=====================================================")
                logger.info(f"任务 ID:{task_id or '所有任务'} 处理完成，线程准备处理下一个任务")
                logger.info(f"队列中剩余任务数量: {task_queue.qsize()}")
                logger.info(f"=====================================================\n")
            
        except queue.Empty:
            # 队列超时，但继续等待
            logger.info("任务队列空闲5分钟，继续等待新任务...")
            continue
            
        except Exception as e:
            # 捕获其他异常，但不退出线程
            import traceback
            logger.error(f"任务队列处理异常: {str(e)}")
            logger.error(f"详细追踪:\n{traceback.format_exc()}")
            
            with task_lock:
                is_task_running = False
                
            # 短暂暂停后继续
            time.sleep(5)
            continue  # 明确继续循环

def ensure_processor_running():
    """确保任务处理线程在运行"""
    global task_processing_thread
    
    with task_lock:
        # 检查线程是否已存在且正在运行
        if task_processing_thread is None or not task_processing_thread.is_alive():
            logger.info("启动新的任务队列处理线程")
            # 创建新线程前先尝试清理可能存在的旧线程
            if task_processing_thread is not None:
                logger.warning("检测到旧处理线程已死，正在创建新线程")
            
            task_processing_thread = threading.Thread(target=process_task_queue, daemon=True)
            task_processing_thread.name = "TaskProcessorThread"  # 为线程命名方便调试
            task_processing_thread.start()
            
            # 短暂等待确保线程启动
            time.sleep(0.1)
            logger.info(f"任务处理线程已启动: {task_processing_thread.name}, 活动状态: {task_processing_thread.is_alive()}")
        else:
            logger.info(f"任务处理线程已在运行中: {task_processing_thread.name}, 活动状态: {task_processing_thread.is_alive()}")
            # 增加一个健康检查，即使线程状态为alive，也打印更多信息以便调试
            logger.info(f"队列信息 - 大小: {task_queue.qsize()}, 当前任务状态: {'执行中' if is_task_running else '空闲'}")

def _execute_task(task_id=None):
    """实际执行任务的函数 (被process_task_queue调用)"""
    logger.info(f"\n=====================================================")
    logger.info(f"开始执行{'指定' if task_id else '所有'}任务")
    logger.info(f"=====================================================\n")
    
    # 获取状态管理器实例
    status_manager = StatusManager.instance()
    
    # Check if we have a status task ID for this task
    global _task_status_map
    if not hasattr(sys.modules[__name__], '_task_status_map'):
        _task_status_map = {}
    
    # Use existing status task ID if available, otherwise create a new one
    if task_id and task_id in _task_status_map:
        task_state_id = _task_status_map[task_id]
        logger.info(f"使用已有的状态任务ID: {task_state_id} 用于任务 {task_id}")
    else:
        task_state_id = status_manager.create_task("RSS处理任务")
        logger.info(f"创建新的状态任务ID: {task_state_id}")
        if task_id:
            _task_status_map[task_id] = task_state_id
    
    status_manager.update_task(task_state_id, 
                             status=TaskStatus.RUNNING,
                             message="正在加载任务配置...")
    
    # 加载配置和任务
    config = load_config()
    tasks = get_tasks()
    
    # Debug: 记录找到的所有任务
    task_ids = [task.task_id for task in tasks]
    logger.info(f"找到 {len(tasks)} 个任务: {task_ids}")
    
    # 如果指定了task_id，只处理该任务
    if (task_id):
        logger.info(f"查找任务ID: {task_id}")
        # 直接从任务列表中查找匹配的任务
        matching_tasks = []
        for task in tasks:
            logger.info(f"比较任务: {task.name} (ID: {task.task_id}) vs 目标ID: {task_id}")
            if task.task_id == task_id:
                logger.info(f"找到匹配任务: {task.name}")
                matching_tasks.append(task)
        
        tasks = matching_tasks
        if not tasks:
            # 详细记录配置中的任务
            raw_tasks = config.get("tasks", [])
            logger.info(f"从配置中找到 {len(raw_tasks)} 个原始任务")
            for i, task_dict in enumerate(raw_tasks):
                raw_id = task_dict.get("id", "无ID")
                raw_name = task_dict.get("name", "无名称")
                logger.info(f"原始任务 #{i+1}: {raw_name} (ID: {raw_id})")
                
            # 尝试重新从配置加载任务
            logger.warning(f"找不到任务ID {task_id}，尝试直接从配置加载")
            for task_dict in raw_tasks:
                if task_dict.get("id") == task_id:
                    from core.task_model import Task
                    tasks = [Task.from_dict(task_dict)]
                    logger.info(f"从原始配置成功加载任务: {task_dict.get('name')} (ID: {task_id})")
                    break
        
        if not tasks:
            logger.error(f"找不到ID为 {task_id} 的任务，无法继续执行")
            return
    
    # 初始化RSS解析器、内容过滤器和摘要生成器
    status_manager.update_task(task_state_id, message="正在初始化服务...")
    rss_parser = RssParser()
    # 确保使用最新配置
    is_skipping = rss_parser.refresh_settings()
    logger.info(f"任务执行器 - 跳过已处理文章: {'是' if is_skipping else '否'}")
    
    try:
        content_filter = ContentFilter(config)
        summarizer = NewsSummarizer(config)
        status_manager.update_task(task_state_id, progress=10)
    except Exception as e:
        status_manager.update_task(task_state_id,
                                 status=TaskStatus.FAILED,
                                 error=str(e))
        logger.error(f"初始化AI服务失败: {str(e)}")
        logger.error("任务执行中止，AI服务是必须的")
        return
    
    # 逐个处理任务
    total_tasks = len(tasks)
    for task_index, task in enumerate(tasks):
        try:
            current_progress = 10 + (task_index / total_tasks * 90)  # 10%-100%
            status_manager.update_task(task_state_id,
                                     message=f"处理任务: {task.name}",
                                     progress=int(current_progress))
            
            logger.info(f"\n=====================================================")
            logger.info(f"开始处理任务: {task.name} (ID: {task.task_id})")
            logger.info(f"=====================================================\n")
            
            logger.info(f"任务详情:")
            logger.info(f"  - 名称: {task.name}")
            logger.info(f"  - RSS源数量: {len(task.rss_feeds)}")
            logger.info(f"  - 接收者数量: {len(task.recipients)}")
            
            if task.last_run:
                logger.info(f"  - 上次运行时间: {task.last_run}")
            else:
                logger.info(f"  - 首次运行")
            
            # 构建feed配置列表
            feed_configs = []
            logger.info(f"\n============ RSS源配置 ============")
            for idx, feed_url in enumerate(task.rss_feeds):
                items_count = task.get_feed_items_count(feed_url)
                feed_labels = task.get_feed_labels(feed_url)
                logger.info(f"RSS源 #{idx+1}:")
                logger.info(f"  URL: {feed_url}")
                logger.info(f"  获取条目数: {items_count}")
                logger.info(f"  标签: {feed_labels}")
                
                # 获取历史状态
                status_info = task.feeds_status.get(feed_url, {})
                last_status = status_info.get("status", "未知")
                last_fetch = status_info.get("last_fetch", "从未")
                logger.info(f"  上次状态: {last_status}")
                logger.info(f"  上次获取时间: {last_fetch}")
                
                feed_configs.append({
                    "url": feed_url,
                    "items_count": items_count
                })
            
            # 获取用户兴趣标签
            global_interests = config.get("global_settings", {}).get("user_interests", [])
            logger.info(f"\n全局兴趣标签: {global_interests} (仅用作默认值)")
            
            # 批量获取RSS feed - 现在传递task_id和recipients
            logger.info(f"\n============ 开始获取Feed内容 ============")
            logger.info(f"准备获取 {len(feed_configs)} 个RSS源")
            feed_results = rss_parser.fetch_multiple_feeds(feed_configs, task.task_id, task.recipients)
            
            # 更新feed状态和收集统计信息
            total_items = 0
            success_feeds = 0
            failed_feeds = 0
            
            logger.info(f"\n============ RSS源获取结果 ============")
            for feed_url, result in feed_results.items():
                status = result["status"]
                items_count = len(result.get("items", []))
                total_items += items_count
                
                if status == "success":
                    success_feeds += 1
                    logger.info(f"Feed获取成功: {feed_url}")
                    logger.info(f"  - 获取到 {items_count} 条内容")
                    if "feed_info" in result:
                        feed_info = result["feed_info"]
                        logger.info(f"  - Feed标题: {feed_info.get('title', '未知')}")
                else:
                    failed_feeds += 1
                    error_msg = result.get("error", "未知错误")
                    logger.error(f"Feed获取失败: {feed_url}")
                    logger.error(f"  - 错误: {error_msg}")
                
                task.update_feed_status(feed_url, result["status"])
            
            logger.info(f"\n============ RSS源获取统计 ============")
            logger.info(f"总Feed数: {len(feed_configs)}")
            logger.info(f"成功Feed数: {success_feeds}")
            logger.info(f"失败Feed数: {failed_feeds}")
            logger.info(f"总条目数: {total_items}")
            
            # 收集所有内容
            status_manager.update_task(task_state_id, message=f"正在获取RSS内容...")
            all_contents = []
            logger.info(f"\n============ 整合内容 ============")
            for feed_url, result in feed_results.items():
                if result["status"] == "success":
                    items = result.get("items", [])
                    
                    # 为每个条目添加feed特定标签
                    feed_labels = task.get_feed_labels(feed_url)
                    logger.info(f"从 {feed_url} 添加 {len(items)} 条内容，标签: {feed_labels}")
                    
                    for i, item in enumerate(items):
                        item["feed_url"] = feed_url
                        item["feed_labels"] = feed_labels
                        title = item.get("title", "无标题")
                        # 只记录前3个条目的详细信息，避免日志过多
                        if i < 3:
                            logger.info(f"  - 条目 #{i+1}: {title}")
                    
                    all_contents.extend(items)
            
            if not all_contents:
                logger.warning(f"任务 {task.name} 未获取到任何内容，跳过过滤步骤")
                continue
            
            # 应用内容过滤器 - 传入所有内容但不再传入全局兴趣标签
            logger.info(f"\n============ 开始内容过滤 ============")
            logger.info(f"待过滤内容总数: {len(all_contents)}")
            logger.info(f"AI模型: {content_filter.ollama_model or content_filter.openai_model}")
            
            # RSS获取完成后更新进度
            status_manager.update_task(task_state_id, 
                                     message=f"正在进行AI内容过滤...",
                                     progress=int(current_progress + 30))
            
            try:
                kept_contents, discarded_contents = content_filter.filter_content_batch(all_contents)
                status_manager.update_task(task_state_id,
                                         message=f"正在生成内容摘要...",
                                         progress=int(current_progress + 60))
                
                # 标记丢弃的内容为已处理 - 使用新的任务特定标记
                for content in discarded_contents:
                    if "article_id" in content:
                        article_id = content["article_id"]
                        # 标记为在当前任务中被丢弃
                        success = rss_parser.db_manager.mark_as_discarded_for_task(article_id, task.task_id)
                        if success:
                            logger.info(f"已标记文章为在任务 {task.task_id} 中丢弃: {content.get('title', '无标题')} (ID: {article_id})")
                        else:
                            logger.warning(f"标记丢弃文章失败: {content.get('title', '无标题')} (ID: {article_id})")
            except Exception as e:
                logger.error(f"AI内容过滤失败: {str(e)}")
                logger.error("由于AI过滤不可用，任务无法继续")
                continue  # 跳过当前任务
            
            # 记录过滤结果的详细统计
            logger.info(f"\n============ 过滤结果 ============")
            logger.info(f"任务: {task.name}")
            logger.info(f"总内容数: {len(all_contents)}")
            logger.info(f"保留内容数: {len(kept_contents)} ({len(kept_contents)/len(all_contents)*100:.1f}%)")
            logger.info(f"丢弃内容数: {len(discarded_contents)} ({len(discarded_contents)/len(all_contents)*100:.1f}%)")
            
            # 按标签统计
            logger.info(f"\n============ 标签匹配统计 ============")
            tag_stats = {}
            matched_count = 0
            for content in kept_contents:
                if "evaluation" in content:
                    eval_data = content["evaluation"]
                    if eval_data["interest_match"]["is_match"]:
                        matched_count += 1
                        for tag in eval_data["interest_match"]["matched_tags"]:
                            if tag in tag_stats:
                                tag_stats[tag] += 1
                            else:
                                tag_stats[tag] = 1
            
            logger.info(f"匹配兴趣标签的内容: {matched_count}/{len(kept_contents)}")
            for tag, count in tag_stats.items():
                logger.info(f"  - 标签 '{tag}': {count} 条")
            
            # 为保留的内容生成摘要
            if kept_contents:
                logger.info(f"\n============ 开始生成新闻简报 ============")
                logger.info(f"需要生成简报的内容数: {len(kept_contents)}")
                
                try:
                    # 生成简报
                    summarized_contents = summarizer.generate_summaries(kept_contents)
                    
                    # 记录简报结果
                    ai_summarized = sum(1 for c in summarized_contents if c.get("summary_method") == "ai")
                    simple_summarized = sum(1 for c in summarized_contents if c.get("summary_method") == "simple")
                    original_summarized = sum(1 for c in summarized_contents if c.get("summary_method") == "original")
                    
                    logger.info(f"\n============ 简报生成结果 ============")
                    logger.info(f"AI生成简报: {ai_summarized}/{len(summarized_contents)}")
                    logger.info(f"简单摘要: {simple_summarized}/{len(summarized_contents)}")
                    logger.info(f"原始摘要: {original_summarized}/{len(summarized_contents)}")
                    
                    # 显示一些简报示例
                    examples_count = min(3, len(summarized_contents))
                    if examples_count > 0:
                        logger.info(f"\n============ 简报示例 ============")
                        for i in range(examples_count):
                            content = summarized_contents[i]
                            title = content.get("title", "无标题")
                            brief = content.get("news_brief", "")
                            method = content.get("summary_method", "未知")
                            logger.info(f"示例 #{i+1} ({method}): {title}")
                            logger.info(f"简报内容:\n{brief}")  # 显示完整简报
                    
                    # 更新过滤后的内容为简报后的内容
                    kept_contents = summarized_contents
                except Exception as e:
                    logger.error(f"生成新闻简报失败: {str(e)}")
                    logger.error("将使用未生成简报的原始内容继续")
            
            # 如果有收件人，则发送邮件
            if kept_contents and task.recipients:
                status_manager.update_task(task_state_id,
                                         message=f"正在发送邮件...",
                                         progress=int(current_progress + 80))
                
                logger.info(f"\n============ 开始发送邮件 ============")
                logger.info(f"任务: {task.name}")
                logger.info(f"收件人数量: {len(task.recipients)}")
                
                try:
                    # 创建邮件发送器
                    email_sender = EmailSender(config)
                    
                    # 发送简报
                    results = email_sender.send_digest(task.name, kept_contents, task.recipients)
                    
                    # 更新收件人状态
                    for recipient, result in results.items():
                        status = result.get("status", "fail")
                        task.update_recipient_status(recipient, status)
                        
                        # 如果成功发送，标记该收件人已收到文章
                        if status == "success":
                            for content in kept_contents:
                                if "article_id" in content:
                                    article_id = content["article_id"]
                                    success = rss_parser.db_manager.mark_as_sent_to_recipient(article_id, recipient)
                                    if not success:
                                        logger.warning(f"标记文章为已发送给 {recipient} 失败: {content.get('title', '无标题')}")
                    
                    # 记录邮件发送结果
                    success_count = sum(1 for r in results.values() if r.get("status") == "success")
                    logger.info(f"邮件发送完成: {success_count}/{len(task.recipients)}成功")
                    
                    # 如果全部成功，不再全部标记为已处理，因为我们已经按收件人标记了
                    if success_count == len(task.recipients):
                        logger.info("所有邮件发送成功")
                    else:
                        logger.warning(f"部分邮件发送失败: {len(task.recipients) - success_count} 个失败")
                        for recipient, result in results.items():
                            if result.get("status") != "success":
                                error = result.get("error", "未知错误")
                                logger.warning(f"  - {recipient}: {error}")
                except Exception as e:
                    logger.error(f"邮件发送过程中出错: {str(e)}")
            
            # 更新任务的last_run时间
            task.update_task_run()
            save_task(task)
            
            # TODO: 存储过滤后的内容，以便后续加工
            logger.info(f"\n============ 任务执行完成 ============")
            logger.info(f"任务: {task.name}")
            logger.info(f"保留内容数: {len(kept_contents)}")
            logger.info(f"总耗时: {(datetime.now() - datetime.fromisoformat(task.last_run)).total_seconds():.2f} 秒")
            
        except Exception as e:
            status_manager.update_task(task_state_id,
                                     message=f"任务 {task.name} 执行出错",
                                     error=str(e))
            import traceback
            logger.error(f"\n============ 任务执行出错 ============")
            logger.error(f"任务: {task.name}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误信息: {str(e)}")
            logger.error(f"详细追踪:\n{traceback.format_exc()}")
    
    # 任务全部完成
    status_manager.update_task(task_state_id,
                             status=TaskStatus.COMPLETED,
                             progress=100,
                             message="所有任务执行完成")
    
    logger.info(f"\n=====================================================")
    logger.info(f"所有任务执行完成")
    logger.info(f"=====================================================\n")

def setup_scheduled_tasks():
    """设置所有定时任务"""
    logger.info("设置定时任务")
    
    # 清除现有任务
    schedule.clear()
    
    # 加载所有任务
    tasks = get_tasks()
    
    # 为每个任务设置定时
    task_count = 0
    scheduled_count = 0
    for task in tasks:
        task_schedule = task.schedule
        if not task_schedule:
            logger.warning(f"任务 {task.name} (ID: {task.task_id}) 没有调度信息，跳过")
            continue
        
        # 获取调度参数
        weeks = task_schedule.get("weeks", 1)  # 默认每周执行
        time_str = task_schedule.get("time", "08:00")  # 默认上午8点
        days = task_schedule.get("days", list(range(7)))  # 默认所有天
        
        task_count += 1
        
        if not days:
            logger.warning(f"任务 {task.name} (ID: {task.task_id}) 没有选择任何天，跳过调度")
            continue
        
        # 创建闭包保存task_id
        def create_job(task_id):
            return lambda: execute_task(task_id)
        
        # 检查上次运行时间，以支持多周运行一次的情况
        job_restricted = False
        if weeks > 1 and task.last_run:
            try:
                last_run = datetime.fromisoformat(task.last_run)
                now = datetime.now()
                days_since_last_run = (now - last_run).days
                
                # 如果距离上次运行未满配置的周数，暂不调度
                if days_since_last_run < weeks * 7 - 1:  # -1是为了避免临界情况
                    logger.info(f"任务 {task.name} (ID: {task.task_id}) 配置为每 {weeks} 周运行一次，"
                               f"距离上次运行仅过去 {days_since_last_run} 天, 暂时不调度")
                    job_restricted = True
            except Exception as e:
                logger.error(f"处理多周运行一次任务时出错: {str(e)}")
        
        # 如果没有限制，为每个选定的天添加调度
        if not job_restricted:
            # 日期名称映射
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_methods = [
                schedule.every().monday,
                schedule.every().tuesday,
                schedule.every().wednesday,
                schedule.every().thursday,
                schedule.every().friday,
                schedule.every().saturday,
                schedule.every().sunday
            ]
            
            for day_index in days:
                if day_index < 0 or day_index > 6:
                    logger.warning(f"忽略无效的星期日索引: {day_index}")
                    continue
                
                day_name = day_names[day_index]
                day_method = day_methods[day_index]
                
                logger.info(f"设置任务 {task.name} (ID: {task.task_id}) 在{day_name} {time_str} 执行")
                day_method.at(time_str).do(create_job(task.task_id))
                scheduled_count += 1
    
    logger.info(f"定时任务设置完成，共 {task_count} 个任务中的 {scheduled_count} 个调度点被设置")
    
    # 输出接下来24小时内将执行的任务
    log_upcoming_tasks()

def log_upcoming_tasks(hours_ahead=24):
    """记录接下来几小时内将执行的任务"""
    now = datetime.now()
    end_time = now + timedelta(hours=hours_ahead)
    
    logger.info(f"\n============ 未来 {hours_ahead} 小时内将执行的定时任务 ============")
    
    # 获取所有任务
    jobs = schedule.get_jobs()
    if not jobs:
        logger.info("没有设置任何定时任务")
        return
    
    # 计算下一次运行时间并排序
    upcoming_jobs = []
    for job in jobs:
        next_run = job.next_run
        if next_run and next_run <= end_time:
            upcoming_jobs.append((next_run, job))
    
    # 按时间排序
    upcoming_jobs.sort(key=lambda x: x[0])
    
    # 显示任务
    if upcoming_jobs:
        for next_run, job in upcoming_jobs:
            time_diff = next_run - now
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            logger.info(f"任务将在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 执行 (还有 {hours}小时{minutes}分钟)")
            logger.info(f"- 任务描述: {job.job_func.__name__}")
    else:
        logger.info(f"未来 {hours_ahead} 小时内没有定时任务")

def reload_scheduled_tasks():
    """重新加载所有定时任务 - 可在调度设置更改后调用"""
    logger.info("重新加载定时任务...")
    setup_scheduled_tasks()
    logger.info("定时任务重新加载完成")
    return get_scheduler_status()

def start_scheduler():
    """启动调度器"""
    logger.info("启动任务调度器")
    
    # 设置定时任务
    setup_scheduled_tasks()
    
    # 确保任务处理线程已启动
    ensure_processor_running()
    
    # 存储线程引用以便后续检查
    scheduler_thread = None
    
    # 在单独的线程中运行调度器
    def run_scheduler():
        logger.info("调度器线程已启动")
        last_check = datetime.now()
        
        while True:
            schedule.run_pending()
            
            # 每小时记录一次调度器状态
            now = datetime.now()
            if (now - last_check).total_seconds() > 3600:  # 1小时
                logger.info("调度器正在运行 - 定期状态检查")
                log_upcoming_tasks()
                last_check = now
                
            time.sleep(60)  # 每分钟检查一次待执行的任务
    
    # 创建并启动线程
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("调度器已在后台启动")
    return scheduler_thread

def get_scheduler_status():
    """获取调度器状态信息"""
    with task_lock:
        queue_size = task_queue.qsize()
        current_running = is_task_running
    
    status = {
        "active_jobs": len(schedule.get_jobs()),
        "queue_size": queue_size,
        "is_task_running": current_running,
        "next_jobs": []
    }
    
    # 获取接下来24小时内的任务
    now = datetime.now()
    end_time = now + timedelta(hours=24)
    
    for job in schedule.get_jobs():
        next_run = job.next_run
        if next_run and next_run <= end_time:
            time_to_run = (next_run - now).total_seconds() / 60  # 分钟
            status["next_jobs"].append({
                "time": next_run.strftime("%Y-%m-%d %H:%M:%S"),
                "minutes_from_now": round(time_to_run),
                "description": job.job_func.__name__
            })
    
    # 按执行时间排序
    status["next_jobs"].sort(key=lambda x: x["minutes_from_now"])
    return status

def run_task_now(task_id):
    """立即执行指定任务 (放入队列)"""
    logger.info(f"立即执行任务 ID: {task_id}")
    
    # 获取状态管理器，创建任务状态
    status_manager = StatusManager.instance()
    status_task_id = status_manager.create_task(f"执行任务 {task_id}")
    logger.info(f"创建状态任务ID: {status_task_id} 用于追踪任务 {task_id} 的执行")
    
    status_manager.update_task(
        status_task_id,
        status=TaskStatus.PENDING,
        message="任务已加入队列，等待执行..."
    )
    
    # Store the status_task_id in a global dictionary to track it during execution
    # This ensures the original task_id is linked to the status_task_id
    global _task_status_map
    if not hasattr(sys.modules[__name__], '_task_status_map'):
        _task_status_map = {}
    _task_status_map[task_id] = status_task_id
    
    # 将任务添加到队列而不是创建新线程
    execute_task(task_id)
    
    # 返回当前队列状态及状态追踪ID
    with task_lock:
        return {
            "queued": True,
            "position": task_queue.qsize(),
            "is_task_running": is_task_running,
            "status_task_id": status_task_id  # Return this so UI can track it
        }

class Scheduler:
    def __init__(self):
        self.db_manager = NewsDBManager()
        self.setup_cleanup_task()
    
    def setup_cleanup_task(self):
        """Set up daily cleanup of old articles."""
        # Schedule cleanup to run once a day
        # Adjust this according to your existing scheduling mechanism
        # If using something like APScheduler:
        # self.scheduler.add_job(self.cleanup_old_articles, 'interval', days=1)
        pass
    
    def cleanup_old_articles(self):
        """Run the database cleanup task to remove articles older than 7 days."""
        try:
            removed_count = self.db_manager.clean_old_articles(days=7)
            logger.info(f"Database cleanup completed: {removed_count} old articles removed")
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")