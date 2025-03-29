import feedparser
import requests
from datetime import datetime
import time
import logging
from typing import List, Dict, Any, Optional
import hashlib
from bs4 import BeautifulSoup
from .news_db_manager import NewsDBManager
from .config_manager import load_config

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
        # 从配置加载是否跳过已处理文章的设置（初始值）
        config = load_config()
        # 修复：更正配置路径访问方式
        self.skip_processed = config.get("global_settings", {}).get("general_settings", {}).get("skip_processed_articles", False)
        logger.info(f"初始化时 - 跳过已处理文章: {'是' if self.skip_processed else '否'}")
        logger.debug(f"配置内容: {config}")
    
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
            
            # 通过显式返回布尔值避免任何转换问题
            return self.skip_processed is True
        except Exception as e:
            logger.error(f"刷新设置时出错: {e}")
            return False
    
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
            
            # 使用feedparser解析RSS Feed
            logger.info(f"解析RSS Feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            # Check if this is a WeChat source that needs special handling
            is_wechat_source = "WXS_" in feed_url or "weixin" in feed_url
            
            # Use special handling for WeChat sources regardless of whether feedparser succeeded
            if is_wechat_source:
                logger.info(f"Detected WeChat source, using specialized parser: {feed_url}")
                return self._parse_wechat_source(feed_url, items_count)
            
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
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_date = datetime(*entry.updated_parsed[:6]).isoformat()
                
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

    def _parse_wechat_source(self, feed_url: str, items_count: int = 10) -> Dict[str, Any]:
        """Special parser for WeChat sources which don't follow standard feed formats"""
        try:
            # 1. Setup warnings filter to suppress XMLParsedAsHTMLWarning
            from bs4 import XMLParsedAsHTMLWarning
            import warnings
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            
            # Download the content
            logger.info(f"Downloading WeChat content from: {feed_url}")
            response = requests.get(feed_url, timeout=15)
            response.encoding = 'utf-8'  # WeChat often uses UTF-8
            
            # Save the HTML for debugging if needed
            html_content = response.text
            logger.debug(f"Raw content length: {len(html_content)} bytes")
            
            # Check if it might be RSS/XML format
            is_xml = '<rss' in html_content[:1000] or '<?xml' in html_content[:1000] or '<feed' in html_content[:1000]
            
            items = []
            feed_title = None  # Store the top-level feed title to use as source
            
            # First attempt: Try parsing as XML if it looks like XML
            if is_xml:
                logger.info("Content appears to be XML/RSS format, trying XML parser")
                try:
                    # Fix: Don't pass both parser and features parameters
                    try:
                        import lxml
                        soup = BeautifulSoup(html_content, features="xml")
                        logger.info("Using lxml for XML parsing")
                    except ImportError:
                        soup = BeautifulSoup(html_content, "html.parser")
                        logger.warning("lxml not installed, using html.parser for XML which may be less effective")
                    
                    # Extract the feed title from the top level <title> element
                    feed_title_element = soup.find('title')  # Get the top-level title
                    if feed_title_element:
                        feed_title = feed_title_element.text.strip()
                        logger.info(f"Found feed title: {feed_title}")
                    
                    # Look for RSS items
                    rss_items = soup.find_all('item') or []
                    if rss_items:
                        logger.info(f"Found {len(rss_items)} RSS items")
                        
                        for item in rss_items[:items_count]:
                            title_tag = item.find('title')
                            title = title_tag.text.strip() if title_tag else "无标题"
                            
                            # Try several places for content
                            content = ""
                            
                            # 1. Try description tag with potential CDATA
                            description_tag = item.find('description')
                            if description_tag and description_tag.string:
                                try:
                                    # Parse the description as HTML and extract actual content
                                    desc_soup = BeautifulSoup(description_tag.string, 'html.parser')
                                    
                                    # Extract just the article text content
                                    content = self._extract_wechat_article_content(desc_soup)
                                    if not content:
                                        content = description_tag.get_text(strip=True)
                                        
                                except Exception as e:
                                    logger.warning(f"Error parsing description: {e}")
                                    content = description_tag.get_text(strip=True)
                            
                            # 2. Try content:encoded tag (common in RSS)
                            content_encoded = item.find('content:encoded') or item.find('encoded')
                            if content_encoded and not content:
                                try:
                                    content_soup = BeautifulSoup(content_encoded.string, 'html.parser')
                                    article_content = self._extract_wechat_article_content(content_soup)
                                    if article_content:
                                        content = article_content
                                    else:
                                        content = content_encoded.get_text(strip=True)
                                except Exception:
                                    content = content_encoded.get_text(strip=True)
                            
                            link_tag = item.find('link')
                            link = link_tag.text if link_tag else feed_url
                            
                            pub_date_tag = item.find('pubDate')
                            published = pub_date_tag.text if pub_date_tag else datetime.now().isoformat()
                            
                            items.append({
                                "title": title,
                                "content": content,
                                "link": link,
                                "published": published,
                                "source": feed_title or "微信公众号"  # Use feed title instead of hardcoded value
                            })
                    
                    # Try ATOM entries if no RSS items were found
                    if not items:
                        atom_entries = soup.find_all('entry')
                        if atom_entries:
                            logger.info(f"Found {len(atom_entries)} Atom entries")
                            
                            for entry in atom_entries[:items_count]:
                                title_tag = entry.find('title')
                                title = title_tag.text.strip() if title_tag else "无标题"
                                
                                content_tag = entry.find('content') or entry.find('summary')
                                content = ""
                                if content_tag:
                                    # If content appears to be HTML, parse it
                                    if content_tag.string and ('<' in content_tag.string and '>' in content_tag.string):
                                        try:
                                            content_soup = BeautifulSoup(content_tag.string, 'html.parser')
                                            # Extract just the article text content
                                            content = self._extract_wechat_article_content(content_soup)
                                            if not content:
                                                content = content_tag.get_text(strip=True)
                                        except Exception:
                                            content = content_tag.get_text(strip=True)
                                    else:
                                        content = content_tag.get_text(strip=True)
                                
                                link_tag = entry.find('link')
                                link = link_tag.get('href') if link_tag and link_tag.has_attr('href') else feed_url
                                
                                pub_date_tag = entry.find('published') or entry.find('updated')
                                published = pub_date_tag.text if pub_date_tag else datetime.now().isoformat()
                                
                                items.append({
                                    "title": title,
                                    "content": content,
                                    "link": link,
                                    "published": published,
                                    "source": feed_title or "微信公众号"  # Use feed title instead of hardcoded value
                                })
                except Exception as e:
                    logger.warning(f"Error parsing as XML: {str(e)}")
            
            # If XML parsing didn't work or no items found, try direct HTML parsing
            if not items:
                logger.info("Parsing as WeChat HTML article")
                
                try:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Get the title - try multiple possible elements
                    title_element = (
                        soup.find('h1', class_='rich_media_title') or 
                        soup.find('h2', class_='rich_media_title') or
                        soup.find('meta', property='og:title') or
                        soup.find('meta', attrs={'name': 'twitter:title'}) or
                        soup.title
                    )
                    
                    # If we haven't found a feed title yet, try to find it
                    if not feed_title:
                        # Look for meta elements that might contain the account name
                        account_element = (
                            soup.find('meta', property='og:site_name') or
                            soup.find('meta', attrs={'name': 'twitter:site'}) or
                            soup.find('meta', attrs={'name': 'application-name'}) or
                            # WeChat often puts the account name in a div with class rich_media_meta
                            soup.find('div', class_='rich_media_meta_nickname') or
                            soup.find('a', class_='rich_media_meta_link')
                        )
                        
                        if account_element:
                            if account_element.get('content'):
                                feed_title = account_element.get('content').strip()
                            elif hasattr(account_element, 'text'):
                                feed_title = account_element.text.strip()
                    
                    # If still no feed title, use the page title
                    if not feed_title and soup.title:
                        feed_title = soup.title.text.strip()
                    
                    title = ""
                    if title_element:
                        if title_element.string:
                            title = title_element.string.strip()
                        elif title_element.get('content'):
                            title = title_element.get('content').strip()
                        elif hasattr(title_element, 'text'):
                            title = title_element.text.strip()
                    
                    if not title:
                        title = "未知标题"
                    
                    logger.info(f"Found title: {title[:100]}")
                    
                    # Look for content in several possible locations
                    content_div = (
                        soup.find('div', class_='rich_media_content') or
                        soup.find('div', id='js_content') or
                        soup.find('div', class_='content') or
                        soup.find('div', class_='text') or
                        soup.find('article') or
                        soup.find('section', class_='article')
                    )
                    
                    content = ""
                    if content_div:
                        content = self._get_clean_text_content(content_div)
                        logger.info(f"Extracted plain text content with length: {len(content)} characters")
                    else:
                        # Try looking for main content in other ways
                        logger.info("No main content div found, trying alternative methods")
                        
                        # Try to extract text from the body
                        body = soup.find('body')
                        if body:
                            content = self._get_clean_text_content(body)
                            logger.info(f"Extracted {len(content)} characters from body")
                    
                    # If we found content, create an item
                    items.append({
                        "title": title,
                        "content": content,
                        "link": feed_url,
                        "published": datetime.now().isoformat(),
                        "source": feed_title or "微信公众号"  # Use the extracted source name
                    })
                    
                    logger.info(f"Extracted WeChat article with title: '{title}' and content length: {len(content)} characters")
                    
                except Exception as e:
                    logger.error(f"Error in HTML parsing: {str(e)}")
            
            # If we have items, return them
            if items:
                logger.info(f"Successfully extracted {len(items)} items from source: {feed_title or '未知来源'}")
                return {
                    "status": "success",
                    "items": items[:items_count]
                }
            else:
                logger.warning("No items could be extracted")
                return {
                    "status": "fail",
                    "error": "无法提取内容",
                    "items": []
                }
        except Exception as e:
            import traceback
            logger.error(f"Error in WeChat parser: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "fail",
                "error": f"微信内容解析失败: {str(e)}",
                "items": []
            }

    def _extract_wechat_article_content(self, soup):
        """Extract the actual article content from WeChat HTML as plain text"""
        # Look for the main article content in WeChat-specific elements
        content_div = (
            soup.find('div', class_='rich_media_content') or
            soup.find('div', id='js_content') or
            soup.find('div', class_='content') or
            soup.find('section', class_='rich_media_wrp') or
            soup.find('div', class_='rich_media_area_primary')
        )
        
        if content_div:
            # Remove scripts and styles that might be in the content
            for script in content_div.find_all(['script', 'style']):
                script.decompose()
            
            # Extract plain text from the content div
            return self._get_clean_text_content(content_div)
        
        # If no specific content div was found, try to extract the article text
        # Try to find the article body
        article = soup.find('div', class_='rich_media_area_primary_inner') or soup.find('div', class_='rich_media_inner')
        
        if article:
            # Extract the paragraphs
            paragraphs = article.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5'])
            if paragraphs:
                text_content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                if text_content:
                    return text_content
        
        # Last resort: look for any paragraph with substantial content
        paragraphs = soup.find_all('p')
        significant_paras = [p for p in paragraphs if len(p.get_text(strip=True)) > 20]
        if significant_paras:
            return '\n\n'.join([p.get_text(strip=True) for p in significant_paras[:20]])
        
        # If we get here, try to extract all text from the body
        body = soup.find('body')
        if body:
            return self._get_clean_text_content(body)
        
        # As a last resort, get all text from the soup
        return self._get_clean_text_content(soup)

    def _get_clean_text_content(self, element):
        """Extract clean text content from an HTML element"""
        # Get all text without HTML tags
        text = element.get_text(separator='\n', strip=True)
        
        # Clean up the text - remove excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n\n'.join(lines)

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
