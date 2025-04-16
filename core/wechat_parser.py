import requests
import logging
import hashlib
from datetime import datetime
import pytz  # 添加时区支持
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .config_manager import load_config  # 添加导入

logger = logging.getLogger("wechat_parser")

class WeChatParser:
    """Parser for WeChat public account content, which needs special handling"""
    
    def __init__(self):
        """Initialize the WeChat parser"""
        # Setup warnings filter to suppress XMLParsedAsHTMLWarning
        try:
            from bs4 import XMLParsedAsHTMLWarning
            import warnings
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        except ImportError:
            pass
            
        # 从配置加载时区处理设置
        config = load_config()
        general_settings = config.get("global_settings", {}).get("general_settings", {})
        self.assume_utc = False  # 修正：无时区信息的日期不应假定为UTC
        logger.info(f"无时区信息时将保留原始时间（假定为本地时间）")
    
    def _convert_to_local_time(self, dt: datetime) -> datetime:
        """
        转换时间到本地时区，特别处理WeChat的时间格式
        
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
        
        # 无时区信息的时间，假设为UTC时间（Atom和RSS标准通常是UTC）
        logger.debug(f"时间 {dt} 无时区信息，假定为UTC时间并转换为本地时间")
        utc_dt = dt.replace(tzinfo=pytz.UTC)
        return utc_dt.astimezone(datetime.now().astimezone().tzinfo)
    
    def parse_wechat_source(self, feed_url: str, items_count: int = 10) -> Dict[str, Any]:
        """Parse WeChat specific sources which don't follow standard feed formats
        
        Args:
            feed_url: Feed URL to parse
            items_count: Number of items to return
            
        Returns:
            Dictionary containing parsed items or error information
        """
        try:
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
                items, feed_title = self._parse_xml_content(html_content, items_count, feed_url)
            
            # If XML parsing didn't work or no items found, try direct HTML parsing
            if not items:
                items, feed_title = self._parse_html_content(html_content, feed_url)
            
            # If we have items, return them
            if items:
                # Ensure each item has a title, link, and unique identifier for database tracking
                for item in items:
                    if not item.get('title'):
                        item['title'] = "未知标题"
                    if not item.get('link'):
                        item['link'] = feed_url
                
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
    
    def _parse_xml_content(self, html_content: str, items_count: int, feed_url: str) -> tuple:
        """Parse WeChat content as XML/RSS/ATOM format
        
        Returns:
            Tuple of (items_list, feed_title)
        """
        items = []
        feed_title = None
        
        logger.info("Content appears to be XML/RSS format, trying XML parser")
        try:
            # Try to use lxml if available
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
                items = self._process_rss_items(rss_items, items_count, feed_url, feed_title)
            
            # Try ATOM entries if no RSS items were found
            if not items:
                atom_entries = soup.find_all('entry')
                if atom_entries:
                    logger.info(f"Found {len(atom_entries)} Atom entries")
                    items = self._process_atom_entries(atom_entries, items_count, feed_url, feed_title)
                    
        except Exception as e:
            logger.warning(f"Error parsing as XML: {str(e)}")
        
        return items, feed_title
    
    def _process_rss_items(self, rss_items, items_count, feed_url, feed_title) -> List[Dict]:
        """Process RSS items into structured data"""
        items = []
        
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
                    content = self._extract_article_content(desc_soup)
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
                    article_content = self._extract_article_content(content_soup)
                    if article_content:
                        content = article_content
                    else:
                        content = content_encoded.get_text(strip=True)
                except Exception:
                    content = content_encoded.get_text(strip=True)
            
            link_tag = item.find('link')
            link = link_tag.text if link_tag else feed_url
            
            pub_date_tag = item.find('pubDate')
            if pub_date_tag and pub_date_tag.text:
                try:
                    # 尝试解析RSS日期格式
                    from email.utils import parsedate_to_datetime
                    pub_datetime = parsedate_to_datetime(pub_date_tag.text)
                    # 转换为本地时区
                    pub_datetime = self._convert_to_local_time(pub_datetime)
                    published = pub_datetime.isoformat()
                except Exception:
                    published = pub_date_tag.text
            else:
                published = datetime.now().isoformat()
            
            items.append({
                "title": title,
                "content": content,
                "link": link,
                "published": published,
                "source": feed_title or "微信公众号",
                "feed_url": feed_url  # 添加feed_url以便后续获取标签
            })
        
        return items
    
    def _process_atom_entries(self, atom_entries, items_count, feed_url, feed_title) -> List[Dict]:
        """Process Atom entries into structured data"""
        items = []
        
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
                        content = self._extract_article_content(content_soup)
                        if not content:
                            content = content_tag.get_text(strip=True)
                    except Exception:
                        content = content_tag.get_text(strip=True)
                else:
                    content = content_tag.get_text(strip=True)
            
            link_tag = entry.find('link')
            link = link_tag.get('href') if link_tag and link_tag.has_attr('href') else feed_url
            
            pub_date_tag = entry.find('published') or entry.find('updated')
            if pub_date_tag and pub_date_tag.text:
                try:
                    # 尝试解析ISO格式日期
                    # 'Z'后缀表示UTC时间，将其替换成正确的时区格式
                    pub_text = pub_date_tag.text.replace('Z', '+00:00')
                    pub_datetime = datetime.fromisoformat(pub_text)
                    # 转换为本地时区
                    pub_datetime = self._convert_to_local_time(pub_datetime)
                    published = pub_datetime.isoformat()
                except ValueError:
                    published = pub_date_tag.text
            else:
                published = datetime.now().isoformat()
            
            items.append({
                "title": title,
                "content": content,
                "link": link,
                "published": published,
                "source": feed_title or "微信公众号",
                "feed_url": feed_url  # 添加feed_url以便后续获取标签
            })
        
        return items
    
    def _parse_html_content(self, html_content, feed_url) -> tuple:
        """Parse WeChat content as direct HTML
        
        Returns:
            Tuple of (items_list, feed_title)
        """
        items = []
        feed_title = None
        
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
                "source": feed_title or "微信公众号",  # Use the extracted source name
                "feed_url": feed_url  # 添加feed_url以便后续获取标签
            })
            
            logger.info(f"Extracted WeChat article with title: '{title}' and content length: {len(content)} characters")
            
        except Exception as e:
            logger.error(f"Error in HTML parsing: {str(e)}")
        
        return items, feed_title
    
    def _extract_article_content(self, soup):
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
