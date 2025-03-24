import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.email_sender import EmailSender

class TestEmailSender(unittest.TestCase):
    """测试EmailSender类的功能，不包括实际发送邮件"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_config = {
            "global_settings": {
                "email_settings": {
                    "smtp_server": "test.example.com",
                    "smtp_port": 587,
                    "smtp_security": "STARTTLS",
                    "sender_email": "test@example.com",
                    "email_password": "test_password"
                }
            }
        }
        
        # 创建测试用的新闻内容数据
        self.test_contents = [
            {
                "title": "测试新闻1",
                "news_brief": "这是测试新闻1的简介",
                "link": "https://example.com/news1",
                "source": "测试源A",
                "pub_date": "2025-03-24T10:00:00",
                "evaluation": {
                    "importance": 7,
                    "timeliness": 6,
                    "interest": 5,
                    "interest_match": {
                        "matched_tags": ["科技", "社会"]
                    }
                },
                "feed_labels": ["科技", "社会", "财经"]
            },
            {
                "title": "测试新闻2",
                "news_brief": "这是测试新闻2的简介",
                "link": "https://example.com/news2",
                "source": "测试源B",
                "pub_date": "2025-03-24T09:00:00",
                "evaluation": {
                    "importance": 9,
                    "timeliness": 8,
                    "interest": 7,
                    "interest_match": {
                        "matched_tags": ["政治", "军事"]
                    }
                }
            },
            {
                "title": "测试新闻3",
                "news_brief": "这是测试新闻3的简介",
                "link": "https://example.com/news3",
                "source": "测试源A",
                "pub_date": "2025-03-24T08:00:00",
                "evaluation": {
                    "importance": 4,
                    "timeliness": 5,
                    "interest": 6
                },
                "feed_labels": ["体育", "娱乐"]
            },
            {
                "title": "测试新闻4 - 复杂评估",
                "news_brief": "测试不同格式的评估数据",
                "link": "https://example.com/news4",
                "source": "测试源C",
                "pub_date": "2025-03-24T11:00:00",
                "evaluation": {
                    "importance": {"score": 8, "reason": "重要新闻"},
                    "timeliness": {"value": 9, "confidence": 0.9},
                    "interest": "7"  # 字符串格式
                }
            }
        ]
        
        # 初始化EmailSender
        self.email_sender = EmailSender(self.test_config)
    
    def test_sort_contents_with_various_data_formats(self):
        """测试_sort_contents能处理各种数据格式并正确排序"""
        sorted_contents = self.email_sender._sort_contents(self.test_contents)
        
        # 验证排序结果（应该按重要性逆序排序）
        # 新闻2应该是第一位(importance=9)
        # 新闻4应该是第二位(importance={"score": 8})
        # 新闻1应该是第三位(importance=7)
        # 新闻3应该是第四位(importance=4)
        self.assertEqual(sorted_contents[0]["title"], "测试新闻2")
        self.assertEqual(sorted_contents[1]["title"], "测试新闻4 - 复杂评估")
        self.assertEqual(sorted_contents[2]["title"], "测试新闻1")
        self.assertEqual(sorted_contents[3]["title"], "测试新闻3")
    
    def test_sort_contents_with_missing_fields(self):
        """测试_sort_contents对缺失字段的处理"""
        # 构建各种缺失字段的测试数据
        missing_field_contents = [
            {
                "title": "缺少评估数据",
                "news_brief": "完全没有evaluation字段",
                "source": "测试源D",
                "link": "https://example.com/missing1"
            },
            {
                "title": "缺少时间字段",
                "news_brief": "没有pub_date字段",
                "source": "测试源D",
                "link": "https://example.com/missing2",
                "evaluation": {
                    "importance": 10
                }
            },
            {
                "title": "正常数据",
                "news_brief": "完整数据作为对比",
                "source": "测试源D",
                "link": "https://example.com/normal",
                "pub_date": "2025-03-24T12:00:00",
                "evaluation": {
                    "importance": 6,
                    "timeliness": 6,
                    "interest": 6
                }
            }
        ]
        
        # 验证排序不会因缺失字段而崩溃
        try:
            sorted_contents = self.email_sender._sort_contents(missing_field_contents)
            # 缺少evaluation但应该使用默认值5，缺少importance的应该排最前（importance=10）
            self.assertEqual(sorted_contents[0]["title"], "缺少时间字段")
            self.assertEqual(sorted_contents[1]["title"], "正常数据")
            self.assertEqual(sorted_contents[2]["title"], "缺少评估数据")
        except Exception as e:
            self.fail(f"排序含有缺失字段的内容时出错: {str(e)}")
    
    def test_create_html_digest(self):
        """测试_create_html_digest生成正确的HTML内容"""
        # 首先排序内容
        sorted_contents = self.email_sender._sort_contents(self.test_contents)
        
        # 生成HTML
        task_name = "测试任务"
        date_str = "2025年03月25日"
        html_content = self.email_sender._create_html_digest(sorted_contents, task_name, date_str)
        
        # 验证HTML内容
        self.assertIsInstance(html_content, str)
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn(task_name, html_content)
        self.assertIn(date_str, html_content)
        
        # 验证所有新闻标题都在HTML中
        for content in self.test_contents:
            self.assertIn(content["title"], html_content)
            self.assertIn(content["news_brief"], html_content)
            self.assertIn(content["source"], html_content)
            self.assertIn(content["link"], html_content)
    
    @patch('smtplib.SMTP_SSL')
    @patch('smtplib.SMTP')
    def test_send_digest_connection_logic(self, mock_smtp, mock_smtp_ssl):
        """测试send_digest的SMTP连接逻辑，但不实际发送邮件"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_ssl_instance = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp_ssl_instance
        
        # 调用send_digest方法但拦截实际发送
        with patch.object(self.email_sender, '_create_html_digest', return_value='<html>测试HTML</html>'):
            # SSL/TLS测试
            self.email_sender.smtp_security = "SSL/TLS"
            self.email_sender.send_digest("测试任务", self.test_contents[:1], ["recipient@example.com"])
            mock_smtp_ssl.assert_called_once()
            mock_smtp_ssl_instance.login.assert_called_once_with(
                self.email_sender.sender_email, 
                self.email_sender.email_password
            )
            
            # STARTTLS测试
            mock_smtp.reset_mock()
            mock_smtp_instance.reset_mock()
            self.email_sender.smtp_security = "STARTTLS"
            self.email_sender.send_digest("测试任务", self.test_contents[:1], ["recipient@example.com"])
            mock_smtp.assert_called_once()
            mock_smtp_instance.starttls.assert_called_once()
            mock_smtp_instance.login.assert_called_once()
    
    def test_importance_stars_generation(self):
        """测试重要性星级显示的生成逻辑"""
        # 创建一个模拟内容，只修改importance值
        test_importance_content = [
            {
                "title": "1星新闻",
                "news_brief": "低重要性",
                "source": "测试",
                "link": "#",
                "evaluation": {"importance": 1}
            },
            {
                "title": "2星新闻",  # 修改为2星，因为5/2=2.5，向下舍入为2
                "news_brief": "中等重要性",
                "source": "测试",
                "link": "#",
                "evaluation": {"importance": 5}
            },
            {
                "title": "5星新闻",
                "news_brief": "高重要性",
                "source": "测试",
                "link": "#",
                "evaluation": {"importance": 10}
            }
        ]
        
        html_content = self.email_sender._create_html_digest(
            test_importance_content, "星级测试", "2025年03月25日"
        )
        
        # 计算每个重要性级别应该显示的星星数量
        one_star = '<span class="star">★</span>'
        two_stars = '<span class="star">★</span>' * 2  # 修改为2星
        five_stars = '<span class="star">★</span>' * 5
        
        # 验证星级显示
        self.assertIn(one_star, html_content)
        self.assertIn(two_stars, html_content)  # 修改预期
        self.assertIn(five_stars, html_content)
        
        # 验证星级位置是否在正确的新闻项中
        one_star_section = html_content.split("1星新闻")[1].split("</div>")[0]
        self.assertIn(one_star, one_star_section)
        
        three_star_section = html_content.split("2星新闻")[1].split("</div>")[0]  # 修改为2星新闻
        self.assertIn(two_stars, three_star_section)  # 修改预期
        
        five_star_section = html_content.split("5星新闻")[1].split("</div>")[0]
        self.assertIn(five_stars, five_star_section)

if __name__ == '__main__':
    unittest.main()
