import schedule
import time
import threading
import logging
from datetime import datetime
from core.config_manager import load_config, save_config, get_tasks, save_task
from core.rss_parser import RssParser
from ai_processor.filter import ContentFilter
from typing import Dict, List, Any

# Fix the logging format string issue
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scheduler")

def execute_task(task_id=None):
    """执行指定任务或所有任务
    
    Args:
        task_id: 特定任务ID，如果为None则执行所有任务
    """
    logger.info(f"开始执行{'指定' if task_id else '所有'}任务")
    
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
    
    # 初始化RSS解析器和内容过滤器
    rss_parser = RssParser()
    content_filter = ContentFilter(config)
    
    # 逐个处理任务
    for task in tasks:
        try:
            logger.info(f"开始处理任务: {task.name} (ID: {task.task_id})")
            logger.info(f"任务配置: {len(task.rss_feeds)} 个RSS源, {len(task.recipients)} 个接收者")
            
            # 构建feed配置列表
            feed_configs = []
            for feed_url in task.rss_feeds:
                items_count = task.get_feed_items_count(feed_url)
                feed_labels = task.get_feed_labels(feed_url)
                logger.info(f"RSS源配置: {feed_url}, 获取 {items_count} 条, 标签: {feed_labels}")
                feed_configs.append({
                    "url": feed_url,
                    "items_count": items_count
                })
            
            # 获取用户兴趣标签 - 这里不再需要全局标签，因为我们会使用每个feed特定的标签
            # 但我们仍需要知道全局配置用于某些默认值
            global_interests = config.get("global_settings", {}).get("user_interests", [])
            logger.info(f"全局兴趣标签: {global_interests} (仅用作默认值)")
            
            # 批量获取RSS feed
            logger.info(f"开始获取 {len(feed_configs)} 个RSS源")
            feed_results = rss_parser.fetch_multiple_feeds(feed_configs)
            
            # 更新feed状态
            total_items = 0
            for feed_url, result in feed_results.items():
                status = result["status"]
                items_count = len(result.get("items", []))
                total_items += items_count
                logger.info(f"RSS源 {feed_url} 获取状态: {status}, 获取到 {items_count} 条内容")
                task.update_feed_status(feed_url, result["status"])
            
            # 收集所有内容
            all_contents = []
            for feed_url, result in feed_results.items():
                if result["status"] == "success":
                    items = result.get("items", [])
                    
                    # 为每个条目添加feed特定标签
                    feed_labels = task.get_feed_labels(feed_url)
                    logger.info(f"处理RSS源 {feed_url} 的 {len(items)} 条内容, 添加标签: {feed_labels}")
                    
                    for i, item in enumerate(items):
                        item["feed_url"] = feed_url
                        item["feed_labels"] = feed_labels  # 这些是该RSS源特有的标签
                        # 记录内容摘要
                        title = item.get("title", "无标题")
                        logger.info(f"内容 #{i+1}: {title[:50]}{'...' if len(title) > 50 else ''}")
                    
                    all_contents.extend(items)
            
            if not all_contents:
                logger.warning(f"任务 {task.name} 未获取到任何内容，跳过过滤步骤")
                continue
                
            # 应用内容过滤器 - 传入所有内容但不再传入全局兴趣标签
            logger.info(f"开始过滤 {len(all_contents)} 条内容, 使用AI: {content_filter.ai_available}")
            kept_contents, discarded_contents = content_filter.filter_content_batch(all_contents)
            
            logger.info(f"任务 {task.name} 完成: 保留 {len(kept_contents)}/{len(all_contents)} 条内容, 丢弃 {len(discarded_contents)} 条")
            
            # 记录保留的内容标题
            for i, content in enumerate(kept_contents):
                title = content.get("title", "无标题")
                keep_reason = "未提供原因"
                if "evaluation" in content:
                    eval_data = content["evaluation"]
                    is_match = eval_data.get("interest_match", {}).get("is_match", False)
                    importance = eval_data.get("importance", {}).get("rating", "未知")
                    timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                    interest_level = eval_data.get("interest_level", {}).get("rating", "未知")
                    keep_reason = f"兴趣匹配: {is_match}, 重要性: {importance}, 时效性: {timeliness}, 趣味性: {interest_level}"
                logger.info(f"保留内容 #{i+1}: {title[:50]}{'...' if len(title) > 50 else ''} - {keep_reason}")
            
            # 更新任务的last_run时间
            task.update_task_run()
            save_task(task)
            
            # TODO: 存储过滤后的内容，以便后续加工
            logger.info(f"任务 {task.name} 执行完毕, 待进一步处理")
            
        except Exception as e:
            import traceback
            logger.error(f"执行任务 {task.name} 时出错: {str(e)}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    logger.info("所有任务执行完成")

def setup_scheduled_tasks():
    """设置所有定时任务"""
    logger.info("设置定时任务")
    
    # 清除现有任务
    schedule.clear()
    
    # 加载所有任务
    tasks = get_tasks()
    
    # 为每个任务设置定时
    for task in tasks:
        task_schedule = task.schedule
        schedule_type = task_schedule.get("type", "daily")
        
        if schedule_type == "daily":
            # 每日执行
            time_str = task_schedule.get("time", "08:00")
            logger.info(f"设置任务 {task.name} 每日 {time_str} 执行")
            
            # 创建闭包保存task_id
            def create_job(task_id):
                return lambda: execute_task(task_id)
            
            # 添加到定时任务
            schedule.every().day.at(time_str).do(create_job(task.task_id))
        
        # 可以添加更多类型的定时 (weekly, hourly等)
    
    logger.info("定时任务设置完成")

def start_scheduler():
    """启动调度器"""
    logger.info("启动任务调度器")
    
    # 设置定时任务
    setup_scheduled_tasks()
    
    # 在单独的线程中运行调度器
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次待执行的任务
    
    # 创建并启动线程
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("调度器已在后台启动")

def run_task_now(task_id):
    """立即执行指定任务
    
    Args:
        task_id: 要执行的任务ID
    """
    logger.info(f"立即执行任务 ID: {task_id}")
    
    # 在单独的线程中执行，避免阻塞主线程
    threading.Thread(target=lambda: execute_task(task_id), daemon=True).start()