import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_processor.ai_utils import AiService

# 配置日志
logger = logging.getLogger("summarizer")

class NewsSummarizer:
    """新闻内容简报生成器，用于将新闻内容转换为简洁完整的概要"""
    
    def __init__(self, config=None):
        """初始化简报生成器
        
        Args:
            config: 包含AI设置的配置字典
        """
        self.config = config or {}
        self.ai_service = AiService(config)
        
        # 加载简报生成配置
        global_settings = self.config.get("global_settings", {})
        self.summarize_settings = global_settings.get("summarize_settings", {})
        
        # 简报风格设置
        self.brief_style = self.summarize_settings.get("style", "informative")
        
        # 是否使用AI，如果AI不可用，则使用简单摘要
        self.use_ai = self.ai_service.ai_available
    
    def generate_summaries(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为一组新闻内容生成简报概要
        
        Args:
            contents: 新闻内容列表
            
        Returns:
            添加了简报概要的内容列表
        """
        if not contents:
            logger.warning("没有内容需要生成简报")
            return []
        
        logger.info(f"开始为 {len(contents)} 条内容生成简报概要")
        
        summarized_contents = []
        for index, content in enumerate(contents):
            try:
                title = content.get("title", "无标题")
                logger.info(f"生成简报 ({index+1}/{len(contents)}): {title[:50]}{'...' if len(title) > 50 else ''}")
                
                # 生成简报
                summarized_content = self.generate_summary(content)
                summarized_contents.append(summarized_content)
                
            except Exception as e:
                logger.error(f"生成简报时出错: {str(e)}")
                # 添加简单摘要
                content["news_brief"] = self._generate_simple_summary(content)
                content["summary_method"] = "simple"
                summarized_contents.append(content)
        
        logger.info(f"简报生成完成: {len(summarized_contents)}/{len(contents)} 成功")
        return summarized_contents
    
    def generate_summary(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """为单个新闻内容生成简报概要
        
        Args:
            content: 新闻内容
            
        Returns:
            添加了简报概要的内容
        """
        title = content.get("title", "")
        original_summary = content.get("summary", "")
        article_content = content.get("content", "")
        
        # 记录原内容长度
        original_content_length = len(article_content)
        logger.info(f"原始内容长度: {original_content_length} 字符")
        
        # 如果文章内容为空或太短，使用原始摘要
        if not article_content or len(article_content) < 100:
            logger.info("内容太短，使用原始摘要")
            content["news_brief"] = original_summary
            content["summary_method"] = "original"
            return content
            
        # 如果AI不可用，使用简单摘要
        if not self.use_ai:
            logger.info("AI不可用，使用简单摘要")
            content["news_brief"] = self._generate_simple_summary(content)
            content["summary_method"] = "simple"
            return content
        
        # 使用AI生成简报
        news_brief = self._generate_ai_summary(content)
        
        # 如果AI简报生成成功，使用AI简报，否则使用简单摘要
        if news_brief:
            logger.info(f"AI简报生成成功，长度: {len(news_brief)} 字符")
            content["news_brief"] = news_brief
            content["summary_method"] = "ai"
            
            # 记录完整的简报内容
            logger.info(f"生成的简报内容: \n{news_brief}")
        else:
            logger.warning("AI简报生成失败，使用简单摘要")
            content["news_brief"] = self._generate_simple_summary(content)
            content["summary_method"] = "simple"
        
        return content
    
    def _generate_ai_summary(self, content: Dict[str, Any]) -> str:
        """使用AI生成新闻简报
        
        Args:
            content: 新闻内容
            
        Returns:
            生成的简报文本
        """
        title = content.get("title", "")
        article_content = content.get("content", "")
        
        # 准备AI提示词
        prompt = self._build_summary_prompt(title, article_content)
        
        # 调用AI
        response = self.ai_service.call_ai(prompt, max_retries=2)
        
        # 如果AI响应为空，返回空字符串
        if not response:
            return ""
            
        # 处理AI响应，移除可能的引号或多余格式
        brief = response.strip().strip('"\'')
        return brief
    
    def _build_summary_prompt(self, title: str, content: str) -> str:
        """构建用于生成简报的提示词
        
        Args:
            title: 新闻标题
            content: 新闻内容
            
        Returns:
            提示词
        """
        # 限制内容长度，避免超过AI上下文限制
        if len(content) > 6000:
            content = content[:6000] + "..."
            
        # 构建提示词
        current_date = datetime.now().strftime("%Y年%m月%d日")
        
        # 根据简报风格调整提示词
        style_description = ""
        if self.brief_style == "informative":
            style_description = "信息丰富、客观的"
        elif self.brief_style == "concise":
            style_description = "简明扼要的"
        elif self.brief_style == "conversational":
            style_description = "对话式、通俗易懂的"
            
        return f"""请为以下新闻生成一个{style_description}内容简报。
简报应该是完整的，有开头有结尾，包含新闻的主要信息点，让读者能快速了解新闻的要点。
简报内容应该简洁明了，但不要过于简略以至于缺失重要信息。
简报里的所有内容都必须基于新闻原文，不要编造任何信息：

标题：{title}

内容：
{content}

当前日期：{current_date}

请直接返回简报文本，不要加引号或前缀说明。
"""
    
    def _generate_simple_summary(self, content: Dict[str, Any]) -> str:
        """生成简单摘要（非AI）
        
        Args:
            content: 新闻内容
            
        Returns:
            简单摘要文本
        """
        # 如果有原始摘要，优先使用
        if content.get("summary"):
            return content["summary"]
            
        # 如果没有摘要，使用内容的前N个字符
        article_content = content.get("content", "")
        if article_content:
            # 清理内容中的HTML标签（简单实现）
            import re
            cleaned_content = re.sub(r'<[^>]+>', ' ', article_content)
            cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
            
            # 找到完整句子的结束位置
            last_period = cleaned_content[:500].rfind('。')
            last_comma = cleaned_content[:500].rfind('，')
            cut_point = max(last_period, last_comma)
            
            if cut_point > 100:  # 确保有合理的长度
                return cleaned_content[:cut_point+1]
            else:
                return cleaned_content[:300] + "..."
                
            return summary
        
        # 如果没有内容也没有摘要，返回标题
        return content.get("title", "无简报可用")
