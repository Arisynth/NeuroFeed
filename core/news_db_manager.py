import sqlite3
import os
import datetime
from pathlib import Path

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
        
        # New table to track sent articles per recipient
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT,
            recipient TEXT,
            sent_date TEXT,
            UNIQUE(article_id, recipient)
        )
        ''')
        
        conn.commit()
        conn.close()
    
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
    
    def clean_old_articles(self, days=7):
        """
        Remove articles older than specified number of days.
        
        Args:
            days (int): Number of days to keep articles (default: 7)
            
        Returns:
            int: Number of articles removed
        """
        try:
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
    def mark_as_sent_to_recipient(self, article_id, recipient):
        """
        Mark an article as sent to a specific recipient.
        
        Args:
            article_id (str): Unique identifier for the article
            recipient (str): Email address of the recipient
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            # Insert or replace (in case it was already marked)
            cursor.execute('''
            INSERT OR REPLACE INTO sent_articles (article_id, recipient, sent_date)
            VALUES (?, ?, ?)
            ''', (article_id, recipient, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking article as sent to recipient: {e}")
            return False
    
    def is_article_sent_to_recipient(self, article_id, recipient):
        """
        Check if an article was sent to a specific recipient.
        
        Args:
            article_id (str): Unique identifier for the article
            recipient (str): Email address of the recipient
            
        Returns:
            bool: True if article was sent to the recipient, False otherwise
        """
        try:
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
