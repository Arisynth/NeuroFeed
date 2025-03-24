import unittest
import tempfile
import os
import sys
import time
import datetime

# 将项目根目录添加到Python路径中，解决导入问题
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.news_db_manager import NewsDBManager

class TestNewsDBManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_news.db")
        self.db_manager = NewsDBManager(self.db_path)
    
    def tearDown(self):
        # Clean up the temporary file
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_add_article(self):
        # Test adding a new article
        result = self.db_manager.add_news_article(
            article_id="test1",
            title="Test Article",
            link="http://example.com/test",
            source="Test Source",
            published_date="2023-01-01T12:00:00",
            content_hash="abcdef123456"
        )
        self.assertTrue(result)
        
        # Test adding the same article again (should return False)
        result = self.db_manager.add_news_article(
            article_id="test1",
            title="Test Article Updated",
            link="http://example.com/test",
            source="Test Source",
            published_date="2023-01-01T12:00:00",
            content_hash="abcdef123456"
        )
        self.assertFalse(result)
    
    def test_article_exists(self):
        # Add an article
        self.db_manager.add_news_article(
            article_id="test2",
            title="Another Test",
            link="http://example.com/another",
            source="Test Source",
            published_date="2023-01-02T12:00:00",
            content_hash="xyz789"
        )
        
        # Test that the article exists
        self.assertTrue(self.db_manager.is_article_exists("test2"))
        self.assertFalse(self.db_manager.is_article_exists("nonexistent"))
    
    def test_mark_as_processed(self):
        # Add an article
        self.db_manager.add_news_article(
            article_id="test3",
            title="Processing Test",
            link="http://example.com/process",
            source="Test Source"
        )
        
        # Mark as processed
        result = self.db_manager.mark_as_processed("test3")
        self.assertTrue(result)
    
    def test_clean_old_articles(self):
        # Add an old article (simulating a 10-day old article)
        old_date = (datetime.datetime.now() - datetime.timedelta(days=10)).isoformat()
        
        # Connect directly to modify the date
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Add the article
        self.db_manager.add_news_article(
            article_id="old_article",
            title="Old Article",
            link="http://example.com/old",
            source="Test Source"
        )
        
        # Manually update the retrieved_date to make it old
        cursor.execute(
            "UPDATE news_articles SET retrieved_date = ? WHERE article_id = ?",
            (old_date, "old_article")
        )
        conn.commit()
        
        # Add a new article
        self.db_manager.add_news_article(
            article_id="new_article",
            title="New Article",
            link="http://example.com/new",
            source="Test Source"
        )
        
        # Clean old articles
        removed = self.db_manager.clean_old_articles(days=7)
        self.assertEqual(removed, 1)
        
        # Verify the old article is gone
        self.assertFalse(self.db_manager.is_article_exists("old_article"))
        self.assertTrue(self.db_manager.is_article_exists("new_article"))
        
        conn.close()
    
    def test_get_processed_status(self):
        # Add an article
        self.db_manager.add_news_article(
            article_id="test_status",
            title="Status Test",
            link="http://example.com/status",
            source="Test Source"
        )
        
        # Initially should be not processed
        self.assertFalse(self.db_manager.get_processed_status("test_status"))
        
        # Mark as processed
        self.db_manager.mark_as_processed("test_status")
        
        # Now should be processed
        self.assertTrue(self.db_manager.get_processed_status("test_status"))
        
        # Non-existent article should return False
        self.assertFalse(self.db_manager.get_processed_status("nonexistent"))
    
    def test_get_all_processed_articles(self):
        # Add multiple articles
        self.db_manager.add_news_article(
            article_id="article1",
            title="Article 1",
            link="http://example.com/1",
            source="Test Source"
        )
        
        self.db_manager.add_news_article(
            article_id="article2",
            title="Article 2",
            link="http://example.com/2",
            source="Test Source"
        )
        
        self.db_manager.add_news_article(
            article_id="article3",
            title="Article 3",
            link="http://example.com/3",
            source="Test Source"
        )
        
        # Mark some as processed
        self.db_manager.mark_as_processed("article1")
        self.db_manager.mark_as_processed("article3")
        
        # Get all processed articles
        processed = self.db_manager.get_all_processed_articles()
        
        # Should have 2 processed articles
        self.assertEqual(len(processed), 2)
        self.assertIn("article1", processed)
        self.assertIn("article3", processed)
        self.assertNotIn("article2", processed)

if __name__ == "__main__":
    unittest.main()
