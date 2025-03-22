import feedparser
import requests
from datetime import datetime
import time
import logging
from typing import List, Dict, Any, Optional

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
    
    def fetch_feed(self, feed_url: str, items_count: int = 10) -> Dict[str, Any]:
        """获取RSS Feed内容
        
        Args:
            feed_url: RSS Feed的URL
            items_count: 获取的条目数量
            
        Returns:
            包含成功/失败状态和Feed内容的字典
        """
        try:
            logger.info(f"开始获取Feed: {feed_url}, 计划获取 {items_count} 条内容")
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
            
            # 处理每个条目
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
                logger.info(f"处理条目 #{i+1}: {title[:50]}{'...' if len(title) > 50 else ''}")
                
                # 构建条目字典
                processed_entry = {
                    "title": title,
                    "link": link,
                    "summary": entry.summary if hasattr(entry, 'summary') else "",
                    "published": published_date,
                    "source": feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else feed_url,
                    "content": entry.content[0].value if hasattr(entry, 'content') and entry.content else entry.summary if hasattr(entry, 'summary') else "",
                }
                processed_entries.append(processed_entry)
            
            elapsed_time = time.time() - start_time
            logger.info(f"成功获取Feed: {feed_url}，获取了{len(processed_entries)}个条目，耗时{elapsed_time:.2f}秒")
            
            feed_title = feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else "未知"
            logger.info(f"Feed信息: 标题={feed_title}")
            
            return {
                "status": "success",
                "items": processed_entries,
                "feed_info": {
                    "title": feed_title,
                    "description": feed.feed.description if hasattr(feed, 'feed') and hasattr(feed.feed, 'description') else "",
                    "link": feed.feed.link if hasattr(feed, 'feed') and hasattr(feed.feed, 'link') else feed_url
                }
            }
        
        except Exception as e:
            import traceback
            logger.error(f"获取Feed失败: {feed_url}, 错误: {str(e)}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
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
