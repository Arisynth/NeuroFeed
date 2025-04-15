import feedparser
import requests
from datetime import datetime
import time
import logging
from typing import List, Dict, Any, Optional
import hashlib
from bs4 import BeautifulSoup
import pytz  # 添加时区支持
from .news_db_manager import NewsDBManager
from .config_manager import load_config
from .wechat_parser import WeChatParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rss_parser")

class RssParser:
    """RSS Feed解析器，用于获取和处理RSS Feed的内容"""
    
    def __init__(self, user_agent: str = "NeuroFeed RSS Reader/1.0"):
        """初始化RSS解析器
        
        Args:
            user_agent: 请求头中的User-Agent字段
        """
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.db_manager = NewsDBManager()
        self.wechat_parser = WeChatParser()  # Initialize the WeChat parser
        
        # 从配置加载是否跳过已处理文章的设置（初始值）
        config = load_config()
        # 修复：更正配置路径访问方式
        self.skip_processed = config.get("global_settings", {}).get("general_settings", {}).get("skip_processed_articles", False)
        logger.info(f"初始化时 - 跳过已处理文章: {'是' if self.skip_processed else '否'}")
        logger.debug(f"配置内容: {config}")
        
        # 从配置加载时区处理设置
        general_settings = config.get("global_settings", {}).get("general_settings", {})
        self.assume_utc = False  # 修正：无时区信息的日期不应假定为UTC
        logger.info(f"无时区信息时将保留原始时间（假定为本地时间）")
    
    def refresh_settings(self):
        """刷新配置设置，确保使用最新的配置值"""
        try:
            config = load_config()
            # 修复：更正配置路径访问方式
            prev_setting = self.skip_processed
            self.skip_processed = config.get("global_settings", {}).get("general_settings", {}).get("skip_processed_articles", False)
            
            logger.info(f"刷新设置 - 跳过已处理文章: {'是' if self.skip_processed else '否'}")
            logger.debug(f"设置变化: {prev_setting} -> {self.skip_processed}")
            logger.debug(f"配置结构: {config.get('global_settings', {}).get('general_settings', {})}")
            
            # 刷新时区处理设置
            general_settings = config.get("global_settings", {}).get("general_settings", {})
            self.assume_utc = False  # 修正：无时区信息的日期不应假定为UTC
            
            logger.info(f"无时区信息时将保留原始时间（假定为本地时间）")
            
            # 通过显式返回布尔值避免任何转换问题
            return self.skip_processed is True
        except Exception as e:
            logger.error(f"刷新设置时出错: {e}")
            return False
    
    def _convert_to_local_time(self, dt: datetime) -> datetime:
        """
        只对有时区信息的日期进行转换，没有时区信息的保持原样
        
        Args:
            dt: 输入的datetime对象
            
        Returns:
            datetime: 转换后的datetime对象
        """
        if dt is None:
            return None
            
        # 只有当datetime有时区信息时才进行转换
        if dt.tzinfo is not None:
            # 获取本地时区
            local_tz = datetime.now().astimezone().tzinfo
            # 转换到本地时区并返回
            logger.debug(f"转换有时区信息的时间 {dt} 到本地时区")
            return dt.astimezone(local_tz)
            
        # 无时区信息则保持原样
        logger.debug(f"时间 {dt} 无时区信息，保持原样（假定为本地时间）")
        return dt
    
    def fetch_feed(self, feed_url: str, items_count: int = 10, task_id: str = None, recipients: List[str] = None) -> Dict[str, Any]:
        """获取RSS Feed内容
        
        Args:
            feed_url: RSS Feed的URL
            items_count: 要获取的条目数量
            task_id: 当前执行的任务ID（用于跳过被该任务丢弃的文章）
            recipients: 当前任务的收件人列表（用于检查是否所有人都收到过）
        """
        try:
            # 每次获取Feed前刷新配置
            self.refresh_settings()
            
            logger.info(f"\n============ 开始获取Feed ============")
            logger.info(f"Feed URL: {feed_url}")
            logger.info(f"计划获取条目数量: {items_count}")
            logger.info(f"跳过已处理文章: {'是' if self.skip_processed else '否'}")
            if task_id:
                logger.info(f"当前任务ID: {task_id}")
            if recipients:
                logger.info(f"当前收件人: {recipients}")
            start_time = time.time()
            
            # Check if this is a WeChat source that needs special handling
            is_wechat_source = "WXS_" in feed_url or "weixin" in feed_url
            
            # Use special handling for WeChat sources
            if is_wechat_source:
                logger.info(f"Detected WeChat source, using specialized parser: {feed_url}")
                wechat_result = self.wechat_parser.parse_wechat_source(feed_url, items_count)
                
                # If WeChat parsing failed, return the error
                if wechat_result["status"] != "success":
                    return wechat_result
                
                # Process WeChat items and store them in the database
                processed_entries = []
                skipped_count = 0
                total_entries = len(wechat_result["items"])
                
                for entry in wechat_result["items"]:
                    # Generate a unique ID for this WeChat article
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', feed_url)
                    
                    # Use link + title as article_id since WeChat articles don't have consistent IDs
                    article_id = f"wechat_{hashlib.md5((link + title).encode()).hexdigest()}"
                    
                    # Check if we should skip this article
                    skip_article = False
                    skip_reason = ""
                    
                    if self.skip_processed:
                        # 检查是否对此任务丢弃过
                        if task_id and self.db_manager.is_article_discarded_for_task(article_id, task_id):
                            skip_article = True
                            skip_reason = f"在任务 {task_id} 中被丢弃过"
                        # 检查是否所有收件人都已收到
                        elif recipients and self.db_manager.is_article_sent_to_all_recipients(article_id, recipients):
                            skip_article = True
                            skip_reason = "所有收件人已收到"
                    
                    if skip_article:
                        skipped_count += 1
                        logger.info(f"跳过微信文章: {title} - 原因: {skip_reason}")
                        continue
                    
                    # Generate content hash
                    content = entry.get('content', '')
                    content_hash = hashlib.md5(content.encode()).hexdigest() if content else None
                    
                    # Store in database
                    self.db_manager.add_news_article(
                        article_id=article_id,
                        title=title,
                        link=link,
                        source=entry.get('source', '微信公众号'),
                        published_date=entry.get('published', datetime.now().isoformat()),
                        content_hash=content_hash
                    )
                    
                    # Add article_id to entry
                    entry["article_id"] = article_id
                    processed_entries.append(entry)
                
                elapsed_time = time.time() - start_time
                logger.info(f"\n============ WeChat Feed获取完成 ============")
                logger.info(f"Feed URL: {feed_url}")
                logger.info(f"获取条目数: {len(processed_entries)}")
                logger.info(f"耗时: {elapsed_time:.2f}秒")
                
                return {
                    "status": "success",
                    "items": processed_entries,
                    "feed_info": {
                        "title": processed_entries[0].get('source', '微信公众号') if processed_entries else "未知",
                        "description": "微信公众号内容",
                        "link": feed_url
                    },
                    "stats": {
                        "total_available": total_entries,
                        "processed": len(processed_entries),
                        "skipped": skipped_count
                    }
                }
            
            # 使用feedparser解析RSS Feed
            logger.info(f"解析RSS Feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            # 检查Feed是否有效
            if not feed:
                logger.warning(f"Feed无效: {feed_url}")
                return {
                    "status": "fail",
                    "error": "无效的Feed",
                    "items": []
                }
            
            if not hasattr(feed, 'entries'):
                logger.warning(f"Feed没有entries属性: {feed_url}")
                return {
                    "status": "fail",
                    "error": "Feed结构无效",
                    "items": []
                }
            
            if not feed.entries:
                logger.warning(f"Feed没有条目: {feed_url}")
                return {
                    "status": "fail",
                    "error": "Feed为空",
                    "items": []
                }
            
            # 获取指定数量的条目
            total_entries = len(feed.entries)
            logger.info(f"Feed包含 {total_entries} 条原始条目")
            
            # 处理每个条目
            logger.info(f"\n============ 处理Feed条目 ============")
            
            processed_entries = []
            skipped_count = 0
            entry_index = 0
            
            # 处理所有条目，直到达到所需数量或遍历完所有条目
            while len(processed_entries) < items_count and entry_index < total_entries:
                if entry_index >= len(feed.entries):
                    break
                    
                entry = feed.entries[entry_index]
                entry_index += 1
                
                # 获取唯一标识符
                article_id = getattr(entry, 'id', entry.link)
                
                # 增强版的跳过逻辑
                skip_article = False
                skip_reason = ""
                
                if self.skip_processed:
                    # 检查是否对此任务丢弃过
                    if task_id and self.db_manager.is_article_discarded_for_task(article_id, task_id):
                        skip_article = True
                        skip_reason = f"在任务 {task_id} 中被丢弃过"
                    
                    # 检查是否所有收件人都已收到
                    elif recipients and self.db_manager.is_article_sent_to_all_recipients(article_id, recipients):
                        skip_article = True
                        skip_reason = "所有收件人已收到"
                
                if skip_article:
                    skipped_count += 1
                    title = getattr(entry, 'title', article_id)
                    logger.info(f"跳过文章 #{entry_index}: {title} - 原因: {skip_reason}")
                    continue
                
                # 提取发布日期，如果存在
                published_date = None
                pub_datetime = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_datetime = datetime(*entry.published_parsed[:6])
                    # 注意：feedparser解析的时间通常是UTC时间，但没有时区信息
                    # 只有确认有时区信息的时间才进行转换，否则保持原样
                    if pub_datetime.tzinfo is not None:
                        pub_datetime = self._convert_to_local_time(pub_datetime)
                    published_date = pub_datetime.isoformat()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_datetime = datetime(*entry.updated_parsed[:6])
                    # 同样，只对有时区信息的时间进行转换
                    if pub_datetime.tzinfo is not None:
                        pub_datetime = self._convert_to_local_time(pub_datetime)
                    published_date = pub_datetime.isoformat()
                
                # 获取标题和链接
                title = entry.title if hasattr(entry, 'title') else "无标题"
                link = entry.link if hasattr(entry, 'link') else ""
                logger.info(f"处理条目 #{len(processed_entries)+1} (总索引 #{entry_index}): {title}")
                
                # 获取摘要
                summary = entry.summary if hasattr(entry, 'summary') else ""
                
                # 构建条目字典
                processed_entry = {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published_date,
                    "source": feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else feed_url,
                    "content": entry.content[0].value if hasattr(entry, 'content') and entry.content else summary if hasattr(entry, 'summary') else "",
                    "article_id": article_id  # 保存原始文章ID用于后续处理
                }
                
                # 记录内容长度
                content_len = len(processed_entry["content"])
                logger.info(f"条目内容长度: {content_len} 字符")
                
                processed_entries.append(processed_entry)
                
                # Generate content hash if content exists
                content_hash = None
                if hasattr(entry, 'content'):
                    content = entry.content[0].value if isinstance(entry.content, list) else entry.content
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                elif hasattr(entry, 'summary'):
                    content_hash = hashlib.md5(entry.summary.encode()).hexdigest()
                
                # Store in database
                self.db_manager.add_news_article(
                    article_id=article_id,
                    title=entry.title,
                    link=entry.link,
                    source=feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else feed_url,
                    published_date=published_date,
                    content_hash=content_hash
                )
            
            # 如果启用了跳过文章功能，记录详细的统计信息
            if self.skip_processed:
                logger.info(f"\n============ 跳过已处理文章统计 ============")
                logger.info(f"Feed包含的总条目数: {total_entries}")
                logger.info(f"跳过的已处理文章数: {skipped_count}")
                logger.info(f"成功获取的新文章数: {len(processed_entries)}")
                
                # 如果获取的文章数少于要求数量，记录原因
                if len(processed_entries) < items_count:
                    logger.info(f"注意: 获取的新文章数 ({len(processed_entries)}) 少于计划数量 ({items_count})")
                    logger.info(f"原因: Feed中所有条目都已处理完毕或没有足够的新文章")
            
            elapsed_time = time.time() - start_time
            logger.info(f"\n============ Feed获取完成 ============")
            logger.info(f"Feed URL: {feed_url}")
            logger.info(f"获取条目数: {len(processed_entries)}")
            logger.info(f"耗时: {elapsed_time:.2f}秒")
            
            return {
                "status": "success",
                "items": processed_entries,
                "feed_info": {
                    "title": feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else "未知",
                    "description": feed.feed.description if hasattr(feed, 'feed') and hasattr(feed.feed, 'description') else "无描述",
                    "link": feed.feed.link if hasattr(feed, 'feed') and hasattr(feed.feed, 'link') else feed_url
                },
                "stats": {
                    "total_available": total_entries,
                    "processed": len(processed_entries),
                    "skipped": skipped_count
                }
            }
        
        except Exception as e:
            import traceback
            logger.error(f"\n============ Feed获取失败 ============")
            logger.error(f"Feed URL: {feed_url}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误信息: {str(e)}")
            logger.error(f"详细追踪:\n{traceback.format_exc()}")
            return {
                "status": "fail",
                "error": str(e),
                "items": []
            }

    def fetch_multiple_feeds(self, feed_configs: List[Dict[str, Any]], task_id: str = None, recipients: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """批量获取多个RSS Feed
        
        Args:
            feed_configs: 包含Feed URL和配置的字典列表
                每个字典应包含'url'和'items_count'
            task_id: 当前执行的任务ID
            recipients: 当前任务的收件人列表
                
        Returns:
            URL到Feed结果的映射字典
        """
        results = {}
        
        for config in feed_configs:
            url = config.get('url')
            items_count = config.get('items_count', 10)
            
            if not url:
                continue
                
            result = self.fetch_feed(url, items_count, task_id, recipients)
            results[url] = result
            
            # 添加一个小延迟，避免过快请求
            time.sleep(0.5)
        
        return results
