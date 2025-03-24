import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
from core.config_manager import load_config, save_config, get_tasks, save_task
from core.rss_parser import RssParser
from ai_processor.filter import ContentFilter
from ai_processor.summarizer import NewsSummarizer
from typing import Dict, List, Any
from core.email_sender import EmailSender, EmailSendError
from .news_db_manager import NewsDBManager

# Fix the logging format string issue
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scheduler")

def execute_task(task_id=None):
    """执行指定任务或所有任务"""
    logger.info(f"\n=====================================================")
    logger.info(f"开始执行{'指定' if task_id else '所有'}任务")
    logger.info(f"=====================================================\n")
    
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
    rss_parser = RssParser()
    # 确保使用最新配置
    is_skipping = rss_parser.refresh_settings()
    logger.info(f"任务执行器 - 跳过已处理文章: {'是' if is_skipping else '否'}")
    
    try:
        content_filter = ContentFilter(config)
        summarizer = NewsSummarizer(config)
    except Exception as e:
        logger.error(f"初始化AI服务失败: {str(e)}")
        logger.error("任务执行中止，AI服务是必须的")
        return
    
    # 逐个处理任务
    for task in tasks:
        try:
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
            
            # 批量获取RSS feed
            logger.info(f"\n============ 开始获取Feed内容 ============")
            logger.info(f"准备获取 {len(feed_configs)} 个RSS源")
            feed_results = rss_parser.fetch_multiple_feeds(feed_configs)
            
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
            
            try:
                kept_contents, discarded_contents = content_filter.filter_content_batch(all_contents)
                
                # 标记丢弃的内容为已处理
                for content in discarded_contents:
                    if "article_id" in content:
                        article_id = content["article_id"]
                        success = rss_parser.db_manager.mark_as_processed(article_id)
                        if success:
                            logger.info(f"已标记丢弃文章为已处理: {content.get('title', '无标题')} (ID: {article_id})")
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
                    
                    # 记录邮件发送结果
                    success_count = sum(1 for r in results.values() if r.get("status") == "success")
                    logger.info(f"邮件发送完成: {success_count}/{len(task.recipients)}成功")
                    
                    # 如果全部成功，标记所有内容为已处理
                    if success_count == len(task.recipients):
                        logger.info("所有邮件发送成功")
                        # 标记所有已发送的内容为已处理
                        for content in kept_contents:
                            if "article_id" in content:
                                article_id = content["article_id"]
                                success = rss_parser.db_manager.mark_as_processed(article_id)
                                if success:
                                    logger.info(f"已标记发送文章为已处理: {content.get('title', '无标题')} (ID: {article_id})")
                                else:
                                    logger.warning(f"标记发送文章失败: {content.get('title', '无标题')} (ID: {article_id})")
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
            import traceback
            logger.error(f"\n============ 任务执行出错 ============")
            logger.error(f"任务: {task.name}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误信息: {str(e)}")
            logger.error(f"详细追踪:\n{traceback.format_exc()}")
    
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
    for task in tasks:
        task_schedule = task.schedule
        schedule_type = task_schedule.get("type", "daily")
        
        if schedule_type == "daily":
            # 每日执行
            time_str = task_schedule.get("time", "08:00")
            logger.info(f"设置任务 {task.name} (ID: {task.task_id}) 每日 {time_str} 执行")
            
            # 创建闭包保存task_id
            def create_job(task_id):
                return lambda: execute_task(task_id)
            
            # 添加到定时任务
            schedule.every().day.at(time_str).do(create_job(task.task_id))
            task_count += 1
        
        # 可以添加更多类型的定时 (weekly, hourly等)
    
    logger.info(f"定时任务设置完成，共 {task_count} 个任务被调度")
    
    # 输出接下来24小时内将执行的任务
    log_upcoming_tasks()

def log_upcoming_tasks(hours_ahead=24):
    """记录接下来几小时内将执行的任务"""
    now = datetime.now()
    end_time = now + timedelta(hours=hours_ahead)
    
    logger.info(f"\n============ 未来 {hours_ahead} 小时内的定时任务 ============")
    
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

def start_scheduler():
    """启动调度器"""
    logger.info("启动任务调度器")
    
    # 设置定时任务
    setup_scheduled_tasks()
    
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
    status = {
        "active_jobs": len(schedule.get_jobs()),
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
    """立即执行指定任务"""
    logger.info(f"立即执行任务 ID: {task_id}")
    
    # 在单独的线程中执行，避免阻塞主线程
    threading.Thread(target=lambda: execute_task(task_id), daemon=True).start()

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