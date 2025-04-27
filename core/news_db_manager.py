import sqlite3
import os
import datetime
import re
from pathlib import Path
from core.config_manager import get_general_settings  # Add this import

class NewsDBManager:
    def __init__(self, db_path=None):
        """
        Initialize the database manager for storing news articles.
        
        Args:
            db_path (str, optional): Path to the SQLite database. 
                                    Defaults to data/rss_news.db in the project directory.
        """
        if db_path is None:
            # Use the default path
            base_dir = Path(__file__).parent.parent
            db_path = os.path.join(base_dir, 'data', 'rss_news.db')
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table to store news articles
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT UNIQUE,  -- Unique identifier for the article (e.g., URL or guid)
            title TEXT,
            link TEXT,
            source TEXT,
            published_date TEXT,
            retrieved_date TEXT,     -- When we fetched the article
            content_hash TEXT,       -- Hash of content to check for duplicates
            processed INTEGER DEFAULT 0  -- Flag to mark if article was processed
        )
        ''')
        
        # New table to track discarded articles per task
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS discarded_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT,
            task_id TEXT,
            discarded_date TEXT,
            UNIQUE(article_id, task_id)
        )
        ''')
        
        # Updated table to track sent articles per recipient and task
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT,
            recipient TEXT,
            task_id TEXT,
            sent_date TEXT,
            UNIQUE(article_id, recipient, task_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def normalize_article_id(self, article_id):
        """
        规范化文章ID，特别处理微博和微信公众号链接
        
        Args:
            article_id (str): 原始文章标识符，通常是URL
            
        Returns:
            str: 规范化后的文章标识符
        """
        if not isinstance(article_id, str):
            return article_id
            
        # 处理微博链接 - 移除查询参数
        if "weibo.com" in article_id:
            # 处理类似 https://weibo.com/6983642457&displayvideo=false&showRetweeted=false/PkGZf9Jll 的情况
            pattern = r"(https://weibo\.com/\d+)(?:&[^/]+)*/([a-zA-Z0-9]+)"
            match = re.match(pattern, article_id)
            if match:
                user_id = match.group(1)
                weibo_id = match.group(2)
                return f"{user_id}/{weibo_id}"
                
            # 处理其他可能带有参数的微博链接
            pattern = r"(https://weibo\.com/\d+/[a-zA-Z0-9]+)(?:\?.*|&.*)"
            match = re.match(pattern, article_id)
            if match:
                return match.group(1)
            
        # 处理微信公众号链接 - 保留关键参数
        if "mp.weixin.qq.com" in article_id:
            # 微信公众号文章通常以 __biz, mid, idx, sn 参数作为唯一标识
            biz_match = re.search(r"__biz=([^&]+)", article_id)
            mid_match = re.search(r"mid=([^&]+)", article_id)
            idx_match = re.search(r"idx=([^&]+)", article_id)
            sn_match = re.search(r"sn=([^&]+)", article_id)
            
            if biz_match and mid_match and idx_match and sn_match:
                biz = biz_match.group(1)
                mid = mid_match.group(1)
                idx = idx_match.group(1)
                sn = sn_match.group(1)
                return f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}&sn={sn}"
                
            # 如果是简短格式的微信链接(例如 https://mp.weixin.qq.com/s/ABCDEFG)
            if "/s/" in article_id:
                parts = article_id.split("/s/")
                if len(parts) > 1:
                    identifier = parts[1].split("?")[0].split("#")[0]
                    return f"https://mp.weixin.qq.com/s/{identifier}"
            
        # 对于其他链接，移除常见的无关参数(如utm_source等)
        pattern = r"(https?://[^?#]+)(?:\?[^#]*)?(#.*)?"
        match = re.match(pattern, article_id)
        if match:
            base_url = match.group(1)
            fragment = match.group(2) or ""
            return base_url + fragment
            
        return article_id
    
    def add_news_article(self, article_id, title, link, source, published_date=None, content_hash=None):
        """
        Add a news article to the database.
        
        Args:
            article_id (str): Unique identifier for the article (URL or guid)
            title (str): Article title
            link (str): URL to the article
            source (str): Name of the RSS feed source
            published_date (str, optional): When the article was published
            content_hash (str, optional): Hash of article content to check for duplicates
        
        Returns:
            bool: True if article was added, False if it already exists
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if article already exists
            cursor.execute("SELECT id FROM news_articles WHERE article_id = ?", (article_id,))
            if cursor.fetchone():
                conn.close()
                return False  # Article already exists
            
            # Get current date in ISO format
            now = datetime.datetime.now().isoformat()
            
            # Insert the article
            cursor.execute('''
            INSERT INTO news_articles 
            (article_id, title, link, source, published_date, retrieved_date, content_hash, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (article_id, title, link, source, published_date, now, content_hash))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding article to database: {e}")
            return False
    
    def clean_old_articles(self, days=None):
        """
        Remove articles older than specified number of days.
        
        Args:
            days (int, optional): Number of days to keep articles.
                                 If None, will use the value from settings.
            
        Returns:
            int: Number of articles removed
        """
        try:
            # If days not specified, get from settings
            if days is None:
                general_settings = get_general_settings()
                days = general_settings.get("db_retention_days", 30)  # Default to 30 days if not set
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate cutoff date - 修复timedelta错误
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            # Delete old articles
            cursor.execute("DELETE FROM news_articles WHERE retrieved_date < ?", (cutoff_date,))
            deleted_count = cursor.rowcount
            
            # Also clean up the discarded and sent articles tables
            cursor.execute("DELETE FROM discarded_articles WHERE discarded_date < ?", (cutoff_date,))
            cursor.execute("DELETE FROM sent_articles WHERE sent_date < ?", (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            return deleted_count
        except Exception as e:
            print(f"Error cleaning old articles: {e}")
            return 0
    
    def is_article_exists(self, article_id):
        """
        Check if an article already exists in the database.
        
        Args:
            article_id (str): Unique identifier for the article
            
        Returns:
            bool: True if article exists, False otherwise
        """
        # 规范化article_id
        article_id = self.normalize_article_id(article_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM news_articles WHERE article_id = ?", (article_id,))
        result = cursor.fetchone() is not None
        
        conn.close()
        return result
    
    def mark_as_processed(self, article_id):
        """
        Mark an article as processed.
        
        Args:
            article_id (str): Unique identifier for the article
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查文章是否存在
            cursor.execute("SELECT id FROM news_articles WHERE article_id = ?", (article_id,))
            if not cursor.fetchone():
                print(f"Warning: Trying to mark non-existent article as processed: {article_id}")
                conn.close()
                return False
                
            cursor.execute("UPDATE news_articles SET processed = 1 WHERE article_id = ?", (article_id,))
            result = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            return result
        except Exception as e:
            print(f"Error marking article as processed: {e}")
            return False
    
    def get_processed_status(self, article_id):
        """
        Check if an article has been processed.
        
        Args:
            article_id (str): Unique identifier for the article
            
        Returns:
            bool: True if processed, False if not processed or article doesn't exist
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT processed FROM news_articles WHERE article_id = ?", (article_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            # If the article exists and processed = 1
            processed = result is not None and result[0] == 1
            return processed
        except Exception as e:
            print(f"Error checking article processed status: {e}")
            return False
    
    def get_all_processed_articles(self):
        """
        Get a list of all processed article IDs.
        
        Returns:
            list: List of processed article IDs
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT article_id FROM news_articles WHERE processed = 1")
            results = cursor.fetchall()
            
            conn.close()
            
            # Return list of article_ids
            return [row[0] for row in results]
        except Exception as e:
            print(f"Error getting processed articles: {e}")
            return []
        
    # New methods for task-specific article tracking
    def mark_as_discarded_for_task(self, article_id, task_id):
        """
        Mark an article as discarded for a specific task.
        
        Args:
            article_id (str): Unique identifier for the article
            task_id (str): ID of the task that discarded the article
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            # Insert or replace (in case it was already marked)
            cursor.execute('''
            INSERT OR REPLACE INTO discarded_articles (article_id, task_id, discarded_date)
            VALUES (?, ?, ?)
            ''', (article_id, task_id, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking article as discarded for task: {e}")
            return False
    
    def is_article_discarded_for_task(self, article_id, task_id):
        """
        Check if an article was discarded for a specific task.
        
        Args:
            article_id (str): Unique identifier for the article
            task_id (str): ID of the task
            
        Returns:
            bool: True if article was discarded for the task, False otherwise
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id FROM discarded_articles 
            WHERE article_id = ? AND task_id = ?
            ''', (article_id, task_id))
            
            result = cursor.fetchone() is not None
            
            conn.close()
            return result
        except Exception as e:
            print(f"Error checking if article was discarded for task: {e}")
            return False
    
    # New methods for recipient-specific article tracking
    def mark_as_sent_to_recipient(self, article_id, recipient, task_id=None):
        """
        Mark an article as sent to a specific recipient for a specific task.
        
        Args:
            article_id (str): Unique identifier for the article
            recipient (str): Email address of the recipient
            task_id (str, optional): ID of the task that triggered the send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            # Insert or replace (in case it was already marked)
            cursor.execute('''
            INSERT OR REPLACE INTO sent_articles (article_id, recipient, task_id, sent_date)
            VALUES (?, ?, ?, ?)
            ''', (article_id, recipient, task_id, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking article as sent to recipient for task {task_id}: {e}")
            return False
    
    def is_article_sent_to_recipient(self, article_id, recipient):
        """
        Check if an article was sent to a specific recipient (regardless of task).
        
        Args:
            article_id (str): Unique identifier for the article
            recipient (str): Email address of the recipient
            
        Returns:
            bool: True if article was sent to the recipient, False otherwise
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id FROM sent_articles 
            WHERE article_id = ? AND recipient = ?
            ''', (article_id, recipient))
            
            result = cursor.fetchone() is not None
            
            conn.close()
            return result
        except Exception as e:
            print(f"Error checking if article was sent to recipient: {e}")
            return False
    
    def is_article_sent_for_task(self, article_id, task_id):
        """
        Check if an article was sent as part of a specific task
        (i.e., sent to at least one recipient for this task).
        
        Args:
            article_id (str): Unique identifier for the article
            task_id (str): ID of the task
            
        Returns:
            bool: True if article was sent for the task, False otherwise
        """
        try:
            # 规范化article_id
            article_id = self.normalize_article_id(article_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id FROM sent_articles 
            WHERE article_id = ? AND task_id = ?
            LIMIT 1
            ''', (article_id, task_id))
            
            result = cursor.fetchone() is not None
            
            conn.close()
            return result
        except Exception as e:
            print(f"Error checking if article was sent for task {task_id}: {e}")
            return False
    
    def is_article_sent_to_all_recipients(self, article_id, recipients):
        """
        Check if an article was sent to all specified recipients.
        
        Args:
            article_id (str): Unique identifier for the article
            recipients (list): List of recipient email addresses
            
        Returns:
            bool: True if article was sent to all recipients, False otherwise
        """
        if not recipients:
            return False
            
        for recipient in recipients:
            if not self.is_article_sent_to_recipient(article_id, recipient):
                return False
        return True
    
    def migrate_normalize_article_ids(self):
        """
        迁移数据库中的所有article_id到规范化格式
        这个方法应该在应用升级后执行一次，以确保历史数据与新的规范化逻辑一致
        
        Returns:
            dict: 包含迁移统计信息的字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            stats = {
                'news_articles': 0,
                'discarded_articles': 0,
                'sent_articles': 0,
                'duplicates_removed': 0,
                'errors': 0
            }
            
            # 处理主文章表
            cursor.execute("SELECT id, article_id FROM news_articles")
            articles = cursor.fetchall()
            for id, article_id in articles:
                normalized_id = self.normalize_article_id(article_id)
                if (normalized_id != article_id):
                    try:
                        # 检查规范化后的ID是否已存在
                        cursor.execute("SELECT id FROM news_articles WHERE article_id = ?", (normalized_id,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # 如果已存在规范化的ID，则合并记录并删除当前记录
                            # 将旧记录的processed状态转移到新记录
                            cursor.execute("SELECT processed FROM news_articles WHERE id = ?", (id,))
                            is_processed = cursor.fetchone()[0]
                            if is_processed:
                                cursor.execute("UPDATE news_articles SET processed = 1 WHERE article_id = ?", (normalized_id,))
                            
                            # 删除旧记录
                            cursor.execute("DELETE FROM news_articles WHERE id = ?", (id,))
                            stats['duplicates_removed'] += 1
                        else:
                            # 更新为规范化的ID
                            cursor.execute("UPDATE news_articles SET article_id = ? WHERE id = ?", (normalized_id, id))
                            stats['news_articles'] += 1
                    except Exception as e:
                        print(f"Error migrating article {article_id}: {e}")
                        stats['errors'] += 1
            
            # 处理已丢弃文章表
            cursor.execute("SELECT id, article_id FROM discarded_articles")
            discarded = cursor.fetchall()
            for id, article_id in discarded:
                normalized_id = self.normalize_article_id(article_id)
                if (normalized_id != article_id):
                    try:
                        cursor.execute("UPDATE discarded_articles SET article_id = ? WHERE id = ?", (normalized_id, id))
                        stats['discarded_articles'] += 1
                    except Exception as e:
                        print(f"Error migrating discarded article {article_id}: {e}")
                        stats['errors'] += 1
            
            # 处理已发送文章表
            cursor.execute("SELECT id, article_id FROM sent_articles")
            sent = cursor.fetchall()
            for id, article_id in sent:
                normalized_id = self.normalize_article_id(article_id)
                if (normalized_id != article_id):
                    try:
                        cursor.execute("UPDATE sent_articles SET article_id = ? WHERE id = ?", (normalized_id, id))
                        stats['sent_articles'] += 1
                    except Exception as e:
                        print(f"Error migrating sent article {article_id}: {e}")
                        stats['errors'] += 1
            
            # 提交所有更改
            conn.commit()
            conn.close()
            
            total_updated = stats['news_articles'] + stats['discarded_articles'] + stats['sent_articles']
            print(f"数据库迁移完成: {total_updated} 条记录已更新, {stats['duplicates_removed']} 条重复记录已合并, {stats['errors']} 个错误")
            return stats
            
        except Exception as e:
            print(f"数据库迁移失败: {str(e)}")
            return {'error': str(e)}
