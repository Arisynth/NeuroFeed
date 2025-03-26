import smtplib
import logging
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from core.encryption import decrypt_password

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
        
        # 解密密码
        encrypted_password = self.email_settings.get("email_password", "")
        self.email_password = decrypt_password(encrypted_password)
        
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
        
        # 对内容进行排序，而不是按源分组
        sorted_contents = self._sort_contents(contents)
        
        # 创建邮件主题
        current_date = datetime.now().strftime("%Y年%m月%d日")
        subject = f"NewsDigest - {task_name} 新闻简报 ({current_date})"
        
        # 创建HTML邮件内容
        html_content = self._create_html_digest(sorted_contents, task_name, current_date)
        
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
    
    def _sort_contents(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据重要性、时效性和趣味性对内容进行排序
        
        排序优先级：重要性 > 时效性 > 趣味性 > 获取时间
        """
        def get_sort_key(item):
            # 从评估结果中获取排序指标，如果缺失则提供默认值
            evaluation = item.get("evaluation", {})
            
            # 获取重要性分数，确保是数字类型
            importance = evaluation.get("importance", {})
            importance_score = 3  # 默认为中等重要性（3分）
            
            # 如果是字典（来自AI评估），直接映射rating值到分数
            if isinstance(importance, dict) and "rating" in importance:
                rating = importance.get("rating")
                if rating == "极低":
                    importance_score = 1
                elif rating == "低":
                    importance_score = 2
                elif rating == "中":
                    importance_score = 3
                elif rating == "高":
                    importance_score = 4
                elif rating == "极高":
                    importance_score = 5
            
            # 获取时效性分数，确保是数字类型
            timeliness = evaluation.get("timeliness", {})
            timeliness_score = 3  # 默认为中等时效性（3分）
            
            # 如果是字典（来自AI评估），直接映射rating值到分数
            if isinstance(timeliness, dict) and "rating" in timeliness:
                rating = timeliness.get("rating")
                if rating == "极低":
                    timeliness_score = 1
                elif rating == "低":
                    timeliness_score = 2
                elif rating == "中":
                    timeliness_score = 3
                elif rating == "高":
                    timeliness_score = 4
                elif rating == "极高":
                    timeliness_score = 5
            
            # 获取趣味性分数，确保是数字类型 - 修复键名为interest_level
            interest_level = evaluation.get("interest_level", {})
            interest_score = 3  # 默认为中等趣味性（3分）
            
            # 如果是字典（来自AI评估），直接映射rating值到分数
            if isinstance(interest_level, dict) and "rating" in interest_level:
                rating = interest_level.get("rating")
                if rating == "极低":
                    interest_score = 1
                elif rating == "低":
                    interest_score = 2
                elif rating == "中":
                    interest_score = 3
                elif rating == "高":
                    interest_score = 4
                elif rating == "极高":
                    interest_score = 5
            
            # 获取发布/获取时间，如果没有则使用当前时间
            pub_time = item.get("pub_date", datetime.now().isoformat())
            
            # 返回排序键（负值使得大值排在前面）
            return (-importance_score, -timeliness_score, -interest_score, pub_time)
        
        # 对内容列表进行排序并返回
        return sorted(contents, key=get_sort_key)
    
    def _create_html_digest(self, sorted_contents: List[Dict[str, Any]], 
                           task_name: str, date_str: str) -> str:
        """创建HTML格式的邮件内容"""
        # 使用内联CSS的样式
        css_styles = """
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }
            .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
            .header h1 { margin: 0; font-size: 24px; }
            .header p { margin: 5px 0 0; font-size: 16px; }
            .news-section { margin: 20px 0; }
            .news-item { padding: 15px; margin-bottom: 15px; border-bottom: 1px solid #eee; }
            .news-item:last-child { border-bottom: none; }
            .news-item h3 { margin: 0 0 10px; font-size: 18px; }
            .news-item .meta { font-size: 13px; color: #7f8c8d; margin-bottom: 10px; line-height: 1.5; }
            .news-item .source { font-weight: bold; color: #2c3e50; display: block; }
            .news-item .pubdate { display: block; color: #7f8c8d; margin-top: 3px; }
            .news-item .rating { display: flex; margin-top: 3px; }
            .news-item .rating .star { color: #f39c12; margin-right: 2px; }
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
            <div class="news-section">
        """
        
        # 添加排序后的所有新闻
        for content in sorted_contents:
            title = content.get("title", "无标题")
            news_brief = content.get("news_brief", "无内容")
            # 将Markdown转换为HTML，而不是完全移除
            news_brief = self._convert_markdown_to_html(news_brief)
            link = content.get("link", "#")
            source = content.get("source", "未知来源")
            
            # 获取并格式化发布时间
            pub_date_html = ""
            pub_date = content.get("published", "")
            if pub_date:
                try:
                    # 尝试解析ISO格式日期
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(pub_date)
                    formatted_date = date_obj.strftime("%Y年%m月%d日 %H:%M")
                    pub_date_html = f'<span class="pubdate">发布时间: {formatted_date}</span>'
                except (ValueError, TypeError):
                    # 如果解析失败，直接使用原始字符串
                    pub_date_html = f'<span class="pubdate">发布时间: {pub_date}</span>'
            
            # 获取评估数据，用于显示重要性等级
            evaluation = content.get("evaluation", {})
            
            # 直接映射重要性评级到星星数量（1-5星）
            star_count = 3  # 默认为3星（中等重要性）
            importance = evaluation.get("importance", {})
            
            # 如果importance是字典（来自AI评估），直接映射rating值到星星数
            if isinstance(importance, dict) and "rating" in importance:
                rating = importance.get("rating")
                if rating == "极低":
                    star_count = 1
                elif rating == "低":
                    star_count = 2
                elif rating == "中":
                    star_count = 3
                elif rating == "高":
                    star_count = 4
                elif rating == "极高":
                    star_count = 5
            
            # 构建重要性星级显示
            importance_stars = '<div class="rating">' + '<span class="star">★</span>' * star_count + '</div>'
            
            # 标签获取逻辑
            tags = []
            if "evaluation" in content and "interest_match" in content["evaluation"]:
                matched_tags = content["evaluation"]["interest_match"].get("matched_tags", [])
                if matched_tags:
                    tags = matched_tags
            elif "feed_labels" in content and content["feed_labels"]:
                tags = content["feed_labels"]
            
            # 构建分类标签HTML
            categories_html = ""
            for tag in tags:
                categories_html += f'<span class="category">{tag}</span>'
            
            html += f"""
            <div class="news-item">
                <h3>{title} {categories_html}</h3>
                <div class="meta">
                    <span class="source">来源: {source}</span>
                    {pub_date_html}
                    {importance_stars}
                </div>
                <div class="content">{news_brief}</div>
                <a href="{link}" class="link" target="_blank">阅读原文</a>
            </div>
            """
        
        # 添加页脚
        html += f"""
            </div>
            <div class="footer">
                <p>此邮件由NewsDigest自动生成 - {date_str}</p>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def _convert_markdown_to_html(self, text: str) -> str:
        """将Markdown格式转换为HTML格式，保留结构但移除不需要的标记
        
        Args:
            text: 包含Markdown格式的文本
            
        Returns:
            转换为HTML的文本，保留列表等结构
        """
        if not text:
            return ""
        
        # 处理特殊字符，避免HTML转义问题
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 保存列表状态
        in_ordered_list = False
        in_unordered_list = False
        list_html = ""
        result = []
        
        # 先处理列表 - 将整个文本分行处理
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检查是否是有序列表项
            ordered_list_match = re.match(r'^(\d+)\.[ \t]+(.*)', line)
            if ordered_list_match:
                if not in_ordered_list:
                    # 开始新的有序列表
                    if list_html:
                        result.append(list_html)
                    list_html = "<ol>"
                    in_ordered_list = True
                    in_unordered_list = False
                
                # 添加列表项
                list_html += f"<li>{ordered_list_match.group(2)}</li>"
            
            # 检查是否是无序列表项
            elif re.match(r'^[-*+][ \t]+', line):
                content = re.sub(r'^[-*+][ \t]+', '', line)
                if not in_unordered_list:
                    # 开始新的无序列表
                    if list_html:
                        result.append(list_html)
                    list_html = "<ul>"
                    in_unordered_list = True
                    in_ordered_list = False
                
                # 添加列表项
                list_html += f"<li>{content}</li>"
            
            else:
                # 不是列表项，如果正在处理列表则结束列表
                if in_ordered_list:
                    list_html += "</ol>"
                    result.append(list_html)
                    list_html = ""
                    in_ordered_list = False
                elif in_unordered_list:
                    list_html += "</ul>"
                    result.append(list_html)
                    list_html = ""
                    in_unordered_list = False
                
                # 添加普通段落
                if line:
                    result.append(line)
                else:
                    result.append("<br>")
            
            i += 1
        
        # 处理可能未关闭的列表
        if in_ordered_list:
            list_html += "</ol>"
            result.append(list_html)
        elif in_unordered_list:
            list_html += "</ul>"
            result.append(list_html)
        
        # 合并处理列表后的结果
        text = "\n".join(result)
        
        # 移除不需要的Markdown格式但保留内容
        replacements = [
            # 移除标题标记
            (r'#{1,6}\s+(.+?)(?:\n|$)', r'\1\n'),
            # 移除粗体
            (r'\*\*(.+?)\*\*', r'\1'),
            (r'__(.+?)__', r'\1'),
            # 移除斜体
            (r'\*([^\*]+?)\*', r'\1'),
            (r'_([^_]+?)_', r'\1'),
            # 移除分隔符
            (r'(-{3,}|\*{3,}|_{3,})\n', r'<hr>\n'),
            # 处理引用为HTML blockquote
            (r'(?:^|\n)>\s*(.+?)(?:\n|$)', r'\n<blockquote>\1</blockquote>\n'),
            # 移除代码块
            (r'```[\s\S]*?```', r''),
            # 移除行内代码
            (r'`(.+?)`', r'\1'),
            # 处理链接，保留链接文字
            (r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>'),
            # 处理换行符
            (r'\n\n+', r'<br><br>'),
            # 确保段落有正确的HTML标签
            (r'<br><br>', r'</p><p>'),
        ]
        
        # 应用替换规则
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        
        # 确保整个文本被段落标签包裹
        if not text.startswith('<'):
            text = f"<p>{text}"
        if not text.endswith('>'):
            text = f"{text}</p>"
        
        # 替换连续的换行为空行
        text = text.replace("\n\n", "<br>")
        text = text.replace("\n", " ")
        
        return text
    
    def _group_by_source(self, contents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """将内容按照来源分组"""
        grouped_contents = {}
        
        for content in contents:
            source = content.get("source", "未知来源")
            if source not in grouped_contents:
                grouped_contents[source] = []
            
            grouped_contents[source].append(content)
        
        return grouped_contents
    
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
