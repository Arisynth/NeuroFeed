import feedparser
import requests
from datetime import datetime
import time
import logging
from typing import List, Dict, Any, Optional
import hashlib
from .news_db_manager import NewsDBManager

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
    
    def fetch_feed(self, feed_url: str, items_count: int = 10) -> Dict[str, Any]:
        """获取RSS Feed内容"""
        try:
            logger.info(f"\n============ 开始获取Feed ============")
            logger.info(f"Feed URL: {feed_url}")
            logger.info(f"计划获取条目数量: {items_count}")
            start_time = time.time()
            
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
            logger.info(f"Feed包含 {total_entries} 条原始条目, 将获取前 {min(items_count, total_entries)} 条")
            entries = feed.entries[:items_count]
            processed_entries = []
            
            # 显示Feed基本信息
            feed_title = feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else "未知"
            feed_desc = feed.feed.description if hasattr(feed, 'feed') and hasattr(feed.feed, 'description') else "无描述"
            feed_desc_short = feed_desc[:100] + "..." if len(feed_desc) > 100 else feed_desc
            logger.info(f"Feed标题: {feed_title}")
            logger.info(f"Feed描述: {feed_desc_short}")
            
            # 处理每个条目
            logger.info(f"\n============ 处理Feed条目 ============")
            for i, entry in enumerate(entries):
                # 提取发布日期，如果存在
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6]).isoformat()
                    logger.info(f"条目 #{i+1} 发布日期: {published_date}")
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_date = datetime(*entry.updated_parsed[:6]).isoformat()
                    logger.info(f"条目 #{i+1} 更新日期: {published_date}")
                else:
                    logger.info(f"条目 #{i+1} 无日期信息")
                
                # 获取标题和链接
                title = entry.title if hasattr(entry, 'title') else "无标题"
                link = entry.link if hasattr(entry, 'link') else ""
                logger.info(f"条目 #{i+1} 标题: {title}")
                logger.info(f"条目 #{i+1} 链接: {link}")
                
                # 获取摘要
                summary = entry.summary if hasattr(entry, 'summary') else ""
                summary_short = summary[:200] + "..." if len(summary) > 200 else summary
                logger.info(f"条目 #{i+1} 摘要: {summary_short}")
                
                # 构建条目字典
                processed_entry = {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published_date,
                    "source": feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else feed_url,
                    "content": entry.content[0].value if hasattr(entry, 'content') and entry.content else summary if hasattr(entry, 'summary') else "",
                }
                
                # 记录内容长度
                content_len = len(processed_entry["content"])
                logger.info(f"条目 #{i+1} 内容长度: {content_len} 字符")
                
                processed_entries.append(processed_entry)
                
                # Create a unique identifier - prefer guid, fallback to link
                article_id = getattr(entry, 'id', entry.link)
                
                # Generate content hash if content exists
                content_hash = None
                if hasattr(entry, 'content'):
                    content = entry.content[0].value if isinstance(entry.content, list) else entry.content
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                elif hasattr(entry, 'summary'):
                    content_hash = hashlib.md5(entry.summary.encode()).hexdigest()
                
                # Get published date if available
                published_date = None
                if hasattr(entry, 'published'):
                    published_date = entry.published
                
                # Store in database
                self.db_manager.add_news_article(
                    article_id=article_id,
                    title=entry.title,
                    link=entry.link,
                    source=feed.feed.title,
                    published_date=published_date,
                    content_hash=content_hash
                )
            
            elapsed_time = time.time() - start_time
            logger.info(f"\n============ Feed获取完成 ============")
            logger.info(f"Feed URL: {feed_url}")
            logger.info(f"获取条目数: {len(processed_entries)}")
            logger.info(f"耗时: {elapsed_time:.2f}秒")
            
            return {
                "status": "success",
                "items": processed_entries,
                "feed_info": {
                    "title": feed_title,
                    "description": feed_desc,
                    "link": feed.feed.link if hasattr(feed, 'feed') and hasattr(feed.feed, 'link') else feed_url
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

    def fetch_multiple_feeds(self, feed_configs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """批量获取多个RSS Feed
        
        Args:
            feed_configs: 包含Feed URL和配置的字典列表
                每个字典应包含'url'和'items_count'
                
        Returns:
            URL到Feed结果的映射字典
        """
        results = {}
        
        for config in feed_configs:
            url = config.get('url')
            items_count = config.get('items_count', 10)
            
            if not url:
                continue
                
            result = self.fetch_feed(url, items_count)
            results[url] = result
            
            # 添加一个小延迟，避免过快请求
            time.sleep(0.5)
        
        return results
