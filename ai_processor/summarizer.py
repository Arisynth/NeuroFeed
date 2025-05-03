import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_processor.ai_utils import AiService, AiException
from core.localization import get_current_language

# 配置日志
logger = logging.getLogger("summarizer")

class NewsSummarizer:
    """新闻内容简报生成器，用于将新闻内容转换为简洁完整的概要"""
    
    def __init__(self, config=None):
        """初始化简报生成器
        
        Args:
            config: 包含AI设置的配置字典
            
        Raises:
            AiException: 当AI服务不可用时
        """
        self.config = config or {}
        # 初始化AI服务，如果不可用会抛出异常
        self.ai_service = AiService(config)
        
        # 加载简报生成配置
        global_settings = self.config.get("global_settings", {})
        self.summarize_settings = global_settings.get("summarize_settings", {})
        
        # 简报风格设置
        self.brief_style = self.summarize_settings.get("style", "informative")
        
        # 直接使用core.localization中的语言设置，确保与UI一致
        self.language = get_current_language()
        
        # 验证是否正确获取了语言设置
        general_settings = global_settings.get("general_settings", {})
        config_language = general_settings.get("language", "zh")
        
        logger.info(f"NewsSummarizer initialized with language from localization: {self.language}")
        logger.info(f"Language in config: {config_language}")
        
        if self.language != config_language:
            logger.warning(f"Language mismatch: localization={self.language}, config={config_language}. Using {self.language}.")
    
    def generate_summaries(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为一组新闻内容生成简报概要
        
        Args:
            contents: 新闻内容列表
            
        Returns:
            添加了简报概要的内容列表
            
        Raises:
            AiException: 当批处理中出现致命错误时
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
                # 如果是连续的多个错误，可能是AI服务问题，应该中断流程
                if index > 0 and index % 3 == 0 and len(summarized_contents) == 0:
                    raise AiException(f"连续多条内容生成简报失败，可能是AI服务存在问题: {str(e)}")
                # 将错误信息添加到内容中
                content["error"] = str(e)
                content["news_brief"] = f"[生成简报失败: {str(e)}]"
                content["summary_method"] = "error"
                summarized_contents.append(content)
        
        logger.info(f"简报生成完成: {len(summarized_contents)}/{len(contents)} 成功")
        return summarized_contents
    
    def generate_summary(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """为单个新闻内容生成简报概要
        
        Args:
            content: 新闻内容
            
        Returns:
            添加了简报概要的内容
            
        Raises:
            AiException: 当简报生成失败时
        """
        title = content.get("title", "")
        article_content = content.get("content", "")
        
        # 处理标题过长的情况
        if len(title) > 70:
            title = self._summarize_long_title(title)
            content["original_title"] = content.get("title", "")
            content["title"] = title
            logger.info(f"标题过长已简化为: {title}")
            
        # 记录原内容长度
        original_content_length = len(article_content)
        logger.info(f"原始内容长度: {original_content_length} 字符")
        
        # 如果文章内容为空或太短，直接使用原内容作为简报
        if not article_content or len(article_content) < 100:
            logger.warning(f"内容太短 ({len(article_content)} 字符)，直接使用原内容作为简报")
            content["news_brief"] = article_content or "无内容可显示"
            content["summary_method"] = "original"
            return content
        
        # 使用AI生成简报
        news_brief = self._generate_ai_summary(content)
        
        # 检查简报是否生成成功
        if not news_brief:
            raise AiException("AI未能生成有效简报")
        
        logger.info(f"AI简报生成成功，长度: {len(news_brief)} 字符")
        content["news_brief"] = news_brief
        content["summary_method"] = "ai"
        
        # 记录完整的简报内容
        logger.info(f"生成的简报内容: \n{news_brief}")
        
        return content
    
    def _summarize_long_title(self, title: str) -> str:
        """对过长的标题进行简化摘要
        
        Args:
            title: 原始标题
            
        Returns:
            简化后的标题
        """
        if len(title) <= 70:
            return title
            
        logger.info(f"标题过长 ({len(title)} 字符)，正在生成简化标题")
        
        try:
            # 准备AI提示词
            prompt = f"""请为以下过长的标题生成一个简短版本，控制在70个字符以内，同时保持原意：

{title}

请直接输出简化后的标题，不要添加任何解释或前缀。"""

            # 如果需要输出英文标题
            if self.language == "en":
                prompt += "\n请用英文输出简化后的标题。"

            # 调用AI
            response = self.ai_service.call_ai(prompt, max_retries=2)
            
            # 清除可能的思考过程
            cleaned_response = self._clean_thinking_process(response)
            if cleaned_response != response:
                logger.info(f"在简化标题过程中检测到并清理了AI思考过程")
                response = cleaned_response
            
            # 处理AI响应
            short_title = response.strip()
            
            # 确保标题确实被缩短了
            if len(short_title) > 70:
                short_title = short_title[:67] + "..."
                
            # 验证简化标题不为空
            if not short_title:
                return title[:67] + "..."
                
            return short_title
            
        except Exception as e:
            logger.error(f"简化标题时出错: {str(e)}")
            # 如果AI简化失败，使用简单截断
            return title[:67] + "..."
    
    def _is_language_match(self, text: str, target_language: str) -> bool:
        """检测文本是否主要使用指定的语言
        
        Args:
            text: 要检查的文本
            target_language: 目标语言 ("zh" 或 "en")
            
        Returns:
            如果文本主要使用目标语言返回True，否则返回False
        """
        if not text:
            return False
        
        if target_language == "zh":
            # 检测中文字符的正则表达式
            pattern = re.compile(r'[\u4e00-\u9fff]')
            # 如果中文字符占比超过1%，认为是中文
            return len(pattern.findall(text)) / len(text) > 0.01
        elif target_language == "en":
            # 检测英文单词的正则表达式
            pattern = re.compile(r'[a-zA-Z]')
            # 如果英文字符占比超过30%，认为是英文
            return len(pattern.findall(text)) / len(text) > 0.3
        
        # 默认返回False
        return False
    
    def _is_chinese_title(self, text: str) -> bool:
        """检测标题是否已经主要是中文
        
        Args:
            text: 要检查的文本
            
        Returns:
            如果文本主要是中文返回True，否则返回False
        """
        # 复用语言匹配检测功能
        return self._is_language_match(text, "zh")
    
    def _clean_thinking_process(self, text: str) -> str:
        """清除AI推理模型中的思考过程（被<think></think>包裹的内容）
        
        Args:
            text: AI响应文本
            
        Returns:
            清除思考过程后的文本
        """
        # 使用非贪婪匹配移除所有<think>...</think>标记之间的内容
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        return cleaned_text
    
    def _generate_ai_summary(self, content: Dict[str, Any]) -> str:
        """使用AI生成新闻简报
        
        Args:
            content: 新闻内容
            
        Returns:
            生成的简报文本
            
        Raises:
            AiException: 当简报生成失败时
        """
        title = content.get("title", "")
        article_content = content.get("content", "")
        
        # Log the language setting being used - add more details for debugging
        logger.info(f"Generating summary using language: {self.language} (en=English, zh=Chinese)")
        
        # 准备AI提示词
        prompt = self._build_summary_prompt(title, article_content)
        
        # Log more detailed info about the prompt language
        prompt_language = "ENGLISH" if "IN ENGLISH ONLY" in prompt or "English summary" in prompt else "CHINESE"
        logger.info(f"Created {prompt_language} prompt based on language setting: {self.language}")
        
        # Log the prompt being sent to the AI (first 200 chars)
        prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
        logger.info(f"Sending prompt to AI (preview): {prompt_preview}")
        
        # 调用AI
        response = self.ai_service.call_ai(prompt, max_retries=2)
        
        # 清除可能的思考过程
        cleaned_response = self._clean_thinking_process(response)
        if cleaned_response != response:
            logger.info(f"检测到并清理了AI思考过程，清理前长度: {len(response)} 字符，清理后: {len(cleaned_response)} 字符")
            response = cleaned_response
        
        # Log part of the AI response to see what language it's responding in
        response_preview = response[:200] + "..." if len(response) > 200 else response
        logger.info(f"Received AI response (preview): {response_preview}")
        
        # 处理AI响应
        brief = response.strip()
        
        # 判断标题是否需要翻译(不匹配目标语言)
        original_title = content.get("title", "")
        title_matches_language = self._is_language_match(original_title, self.language)
        logger.info(f"Title language match with {self.language}: {title_matches_language}")
        
        if not title_matches_language:
            # 从AI回复中提取翻译标题的正则表达式模式
            title_patterns = []
            
            if self.language == "zh":
                title_patterns = [
                    r"(?:标题[：:]\s*)(.+?)(?:\n|$)",   # 标题：翻译的标题
                    r"(?:^|\n)#\s+(.+?)(?:\n|$)",      # # 翻译的标题
                    r"(?:^|\n)【(.+?)】(?:\n|$)",      # 【翻译的标题】
                    r"(?:^|\n)「(.+?)」(?:\n|$)"       # 「翻译的标题」
                ]
            elif self.language == "en":
                title_patterns = [
                    r"(?:Title[：:]\s*)(.+?)(?:\n|$)",  # Title: Translated title
                    r"(?:^|\n)#\s+(.+?)(?:\n|$)",      # # Translated title
                    r"(?:^|\n)\*\*(.+?)\*\*(?:\n|$)"   # **Translated title**
                ]
            
            for pattern in title_patterns:
                match = re.search(pattern, brief)
                if match:
                    translated_title = match.group(1).strip()
                    # 移除已提取的标题部分
                    brief = re.sub(pattern, '', brief, 1).strip()
                    
                    # 如果找到了翻译的标题，更新内容
                    if translated_title and translated_title != original_title:
                        logger.info(f"提取到翻译标题: '{translated_title}'")
                        # 保存原始标题
                        if "original_title" not in content:
                            content["original_title"] = original_title
                        # 更新为翻译的标题
                        content["title"] = translated_title
                    break
        
        # 验证简报内容
        if len(brief) < 5:  # 简报过短表示可能有问题
            raise AiException(f"生成的简报内容过短 ({len(brief)} 字符)")
            
        return brief.strip()
    
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
        
        # Double check the language setting before building prompt
        logger.info(f"Building prompt with language setting: {self.language}")
        
        # 检测标题是否与目标语言匹配
        title_matches_language = self._is_language_match(title, self.language)
        logger.info(f"Title '{title[:30]}...' matches language {self.language}: {title_matches_language}")
        
        # 根据简报风格调整提示词
        style_description = ""
        if self.brief_style == "informative":
            style_description = "客观、信息丰富的" if self.language == "zh" else "objective and informative"
        elif self.brief_style == "concise":
            style_description = "简明扼要的" if self.language == "zh" else "concise"
        elif self.brief_style == "conversational":
            style_description = "通俗易懂的" if self.language == "zh" else "conversational"
        
        # 确定输出语言
        output_language = "中文" if self.language == "zh" else "English"
        
        # Force lowercase comparison for safety
        if self.language.lower() == "en":
            # Make English requirement more explicit and align with Chinese prompt updates
            prompt = f"""Please provide an {style_description} summary of the following news article IN ENGLISH ONLY, under 300 words.

Regardless of the original language of the article, your summary **MUST be in English**.
The summary should help readers quickly understand the main content of the article to decide whether to read the original.

{"If the original title is not in English, please translate it into English and include it at the beginning using the format 'Title: [actual translated title]'" if not title_matches_language else "The title is already in English, no need to translate it."}

Please follow these requirements:
1. The summary should include the core information and main points of the article, maintaining completeness and readability. Use clear and concise language, avoiding excessive length.
2. **All content must be based on the original text. Strictly prohibit adding any information not mentioned in the original text.**
3. Avoid hallucination. **Pay attention to clarifying relationships between people, organizations, and events mentioned in the news. Carefully check data and avoid incorrect descriptions.**
4. Directly output the English summary content without extra explanations or commentary. Do not include metadata such as date, source, or reference links. Do not use introductory phrases like 'News Summary', 'Summary:', 'In summary', etc., before the summary text. Do not include closing phrases like 'End of summary'.
5. Strictly adhere to all the above requirements to ensure the generated summary meets expectations.

Title: {title}

Content:
{content}

{"First provide the translated English title using the format 'Title: [actual translated title here]', then start the summary **directly** on a new line without any prefix like 'Summary:'." if not title_matches_language else "Provide the English summary **directly** without any prefix."}
"""
            logger.info("Created ENGLISH prompt for summary generation")
        else:
            # Original Chinese prompt remains unchanged - Modify format instruction
            prompt = f"""请为以下新闻内容提供一个**300字左右，最长不超过500字**的{style_description}摘要。无论原文是什么语言，摘要语言必须为中文。摘要应帮助读者快速理解文章的主要内容，以便决定是否阅读原文。

{"如果原标题与输出语言不匹配，请将标题翻译成中文，并以“标题：[实际翻译后的标题]”的格式置于摘要之前。" if not title_matches_language else "文章标题已经与输出语言匹配，无需翻译。"}

请遵循以下要求：
1. 摘要应包含文章的核心信息和要点，保持完整性和可读性，语言简洁清晰，不要过于冗长
2. **所有内容必须基于原文，严禁添加未在原文中提及的任何信息**
3. 避免幻觉（hallucination），**注意理清新闻中的人物、组织、事件、从属等关系，仔细核对所有数据，避免在摘要中描述错误。**
4. 直接输出中文摘要内容，不要添加额外的解释或说明。不要包含当前日期、来源信息、参考链接等元数据；不要使用“摘要：”、“总结：”等任何形式的词语作为摘要内容的开头；不要包含"简报结束"、"以上就是..."等作为结尾。
5. 严格遵守以上要求，确保生成的摘要符合预期！

标题：{title}

内容：
{content}

{'请先提供翻译后的中文标题，使用格式“标题：[实际翻译后的标题]”，然后从下一行开始 **直接输出摘要正文**，不要加“摘要：”等任何前缀。**务必确保摘要基于原文，不要编造和添加任何额外信息！**' if not title_matches_language else '请 **直接提供中文摘要内容**，不要加任何前缀。**务必确保摘要基于原文，不要编造和添加任何额外信息！**'}
"""
            logger.info("Created Chinese prompt for summary generation")
            
        return prompt
