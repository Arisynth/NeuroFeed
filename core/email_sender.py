import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# 配置日志
logger = logging.getLogger("email_sender")

class EmailSendError(Exception):
    """表示邮件发送过程中的错误"""
    pass

class EmailSender:
    """负责将新闻简报发送到指定收件人"""
    
    def __init__(self, config=None):
        """初始化邮件发送器
        
        Args:
            config: 包含邮件设置的配置字典
        """
        self.config = config or {}
        # 从配置加载邮件设置
        global_settings = self.config.get("global_settings", {})
        self.email_settings = global_settings.get("email_settings", {})
        
        # SMTP设置
        self.smtp_server = self.email_settings.get("smtp_server", "")
        self.smtp_port = self.email_settings.get("smtp_port", 587)
        self.smtp_security = self.email_settings.get("smtp_security", "STARTTLS")
        
        # 发件人设置
        self.sender_email = self.email_settings.get("sender_email", "")
        self.email_password = self.email_settings.get("email_password", "")
        
        # 验证必要的设置是否存在
        if not all([self.smtp_server, self.sender_email, self.email_password]):
            logger.warning("邮件设置不完整，需要在设置中配置SMTP服务器、发件人和密码")
    
    def send_digest(self, task_name: str, contents: List[Dict[str, Any]], 
                    recipients: List[str]) -> Dict[str, Dict[str, Any]]:
        """向收件人发送简报邮件"""
        if not contents:
            logger.warning("没有内容可发送")
            return {recipient: {"status": "fail", "error": "没有内容可发送"} for recipient in recipients}
        
        if not recipients:
            logger.warning("没有收件人")
            return {}
        
        # 验证邮件设置
        if not all([self.smtp_server, self.sender_email, self.email_password]):
            error_msg = "邮件设置不完整，无法发送"
            logger.error(error_msg)
            return {recipient: {"status": "fail", "error": error_msg} for recipient in recipients}
        
        # 按源分组内容
        grouped_contents = self._group_by_source(contents)
        
        # 创建邮件主题
        current_date = datetime.now().strftime("%Y年%m月%d日")
        subject = f"NewsDigest - {task_name} 新闻简报 ({current_date})"
        
        # 创建HTML邮件内容
        html_content = self._create_html_digest(grouped_contents, task_name, current_date)
        
        # 发送邮件并跟踪状态
        results = {}
        
        try:
            # 连接SMTP服务器
            smtp = self._connect_to_smtp()
            
            for recipient in recipients:
                try:
                    # 为每个收件人创建邮件
                    msg = MIMEMultipart()
                    msg['From'] = self.sender_email
                    msg['To'] = recipient
                    msg['Subject'] = subject
                    
                    # 添加HTML内容
                    msg.attach(MIMEText(html_content, 'html'))
                    
                    # 发送邮件
                    logger.info(f"正在发送邮件到: {recipient}")
                    smtp.sendmail(self.sender_email, recipient, msg.as_string())
                    logger.info(f"成功发送邮件到: {recipient}")
                    
                    results[recipient] = {"status": "success"}
                except Exception as e:
                    error_msg = f"发送邮件到 {recipient} 失败: {str(e)}"
                    logger.error(error_msg)
                    results[recipient] = {"status": "fail", "error": str(e)}
            
            # 关闭连接
            smtp.quit()
            
        except Exception as e:
            error_msg = f"SMTP连接错误: {str(e)}"
            logger.error(error_msg)
            # 所有收件人都标记为失败
            for recipient in recipients:
                if recipient not in results:
                    results[recipient] = {"status": "fail", "error": error_msg}
        
        return results
    
    def _connect_to_smtp(self) -> smtplib.SMTP:
        """连接到SMTP服务器"""
        logger.info(f"连接到SMTP服务器: {self.smtp_server}:{self.smtp_port} (安全性: {self.smtp_security})")
        
        try:
            # 根据安全设置选择连接方式
            if self.smtp_security == "SSL/TLS":
                smtp = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
            else:
                smtp = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                
                # 如果是STARTTLS，需要额外的TLS加密
                if self.smtp_security == "STARTTLS":
                    smtp.starttls()
            
            # 使用基本认证
            logger.info("使用基本认证")
            smtp.login(self.sender_email, self.email_password)
            
            logger.info("SMTP连接和登录成功")
            return smtp
            
        except Exception as e:
            error_msg = f"连接SMTP服务器失败: {str(e)}"
            logger.error(error_msg)
            raise EmailSendError(error_msg)
    
    def _group_by_source(self, contents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """将内容按照来源分组"""
        grouped_contents = {}
        
        for content in contents:
            source = content.get("source", "未知来源")
            if source not in grouped_contents:
                grouped_contents[source] = []
            
            grouped_contents[source].append(content)
        
        return grouped_contents
    
    def _create_html_digest(self, grouped_contents: Dict[str, List[Dict[str, Any]]], 
                           task_name: str, date_str: str) -> str:
        """创建HTML格式的邮件内容"""
        # 使用内联CSS的样式
        css_styles = """
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }
            .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
            .header h1 { margin: 0; font-size: 24px; }
            .header p { margin: 5px 0 0; font-size: 16px; }
            .source { background-color: #f8f9fa; border-left: 4px solid #2c3e50; padding: 10px; margin: 20px 0 10px; }
            .source h2 { margin: 0; font-size: 20px; color: #2c3e50; }
            .news-item { padding: 10px 10px 10px 20px; margin-bottom: 15px; border-bottom: 1px solid #eee; }
            .news-item:last-child { border-bottom: none; }
            .news-item h3 { margin: 0 0 10px; font-size: 18px; }
            .news-item .category { display: inline-block; background-color: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 12px; margin-left: 5px; }
            .news-item .content { margin: 10px 0; }
            .news-item .link { text-decoration: none; color: #3498db; font-weight: bold; }
            .news-item .link:hover { text-decoration: underline; }
            .footer { text-align: center; font-size: 12px; color: #7f8c8d; margin-top: 30px; padding: 10px; border-top: 1px solid #eee; }
        </style>
        """
        
        # 构建HTML头部
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>NewsDigest - {task_name}</title>
            {css_styles}
        </head>
        <body>
            <div class="header">
                <h1>NewsDigest - {task_name}</h1>
                <p>{date_str} 新闻简报</p>
            </div>
        """
        
        # 为每个来源添加内容
        for source, contents in grouped_contents.items():
            html += f"""
            <div class="source">
                <h2>{source}</h2>
            </div>
            """
            
            # 添加该来源的所有新闻
            for content in contents:
                title = content.get("title", "无标题")
                news_brief = content.get("news_brief", "无内容")
                link = content.get("link", "#")
                
                # 获取标签/分类（如果有）
                tags = []
                if "feed_labels" in content and content["feed_labels"]:
                    tags = content["feed_labels"]
                elif "evaluation" in content and "interest_match" in content["evaluation"]:
                    matched_tags = content["evaluation"]["interest_match"].get("matched_tags", [])
                    if matched_tags:
                        tags = matched_tags
                
                # 构建分类标签HTML
                categories_html = ""
                for tag in tags:
                    categories_html += f'<span class="category">{tag}</span>'
                
                html += f"""
                <div class="news-item">
                    <h3>{title} {categories_html}</h3>
                    <div class="content">{news_brief}</div>
                    <a href="{link}" class="link" target="_blank">阅读原文</a>
                </div>
                """
        
        # 添加页脚
        html += f"""
            <div class="footer">
                <p>此邮件由NewsDigest自动生成 - {date_str}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_test_email(self, recipient: str) -> Tuple[bool, str]:
        """发送测试邮件"""
        if not all([self.smtp_server, self.sender_email, self.email_password]):
            return False, "邮件设置不完整，无法发送。请检查SMTP服务器、发件人和密码。"
        
        try:
            # 连接SMTP服务器
            smtp = self._connect_to_smtp()
            
            # 创建测试邮件
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = "NewsDigest - 测试邮件"
            
            # 测试邮件内容
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; }
                    .header { background-color: #2c3e50; color: white; padding: 10px; text-align: center; }
                    .content { padding: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>NewsDigest 测试邮件</h2>
                    </div>
                    <div class="content">
                        <p>这是一封测试邮件，用于验证您的邮件配置是否正确。</p>
                        <p>如果您收到这封邮件，说明您的邮件服务配置成功！</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # 发送邮件
            smtp.sendmail(self.sender_email, recipient, msg.as_string())
            
            # 关闭连接
            smtp.quit()
            
            return True, "测试邮件发送成功"
            
        except Exception as e:
            error_msg = f"发送测试邮件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
