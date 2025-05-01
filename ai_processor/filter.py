import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone # Import timezone
from ai_processor.ai_utils import AiService, AiException
import json
import re # Import re

# 配置日志
logger = logging.getLogger("content_filter")

# 定义评分等级枚举类型
class RatingLevel(str, Enum):
    VERY_LOW = "极低"
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    VERY_HIGH = "极高"
    UNKNOWN = "未知"

class ContentFilter:
    """新闻内容过滤器，用于评估和过滤新闻条目"""

    def __init__(self, config=None):
        """初始化内容过滤器
        
        Args:
            config: 包含AI设置的配置字典
            
        Raises:
            AiException: 当AI服务不可用时
        """
        self.config = config or {}
        # 使用共享的AI服务，如果不可用会抛出异常
        self.ai_service = AiService(config)
        
        # 获取AI服务的提供商和模型信息
        self.provider = self.ai_service.provider
        self.ollama_model = getattr(self.ai_service, 'ollama_model', '')
        self.openai_model = getattr(self.ai_service, 'openai_model', '')

    def evaluate_content(self, content: Dict[str, Any], max_attempts: int = 3) -> Dict[str, Any]:
        """评估新闻内容，检查是否符合用户兴趣，并评价重要性、时效性、趣味性。
           如果AI响应格式错误，会尝试要求AI修正，最多重试 max_attempts 次。

        Args:
            content: 新闻内容
            max_attempts: 最大尝试次数 (包括首次尝试)

        Returns:
            评估后的内容，包含评估结果或错误信息
        """
        title = content.get("title", "无标题")
        summary = content.get("summary", "")
        feed_labels = content.get("feed_labels", [])
        
        # 确保我们获取了负向标签 - 如果content里没有，就从task里获取
        negative_labels = content.get("negative_labels", [])
        feed_url = content.get("feed_url")
        task = content.get("task")
        
        # 如果没有负向标签但有任务对象和feed URL，则从任务配置中获取
        if not negative_labels and task and feed_url and hasattr(task, 'get_feed_negative_labels'):
            try:
                negative_labels = task.get_feed_negative_labels(feed_url)
                # 记录从任务配置获取的标签
                logger.info(f"从任务配置获取负向标签: {negative_labels}")
                # 更新内容字典以包含这些标签供后续处理使用
                content["negative_labels"] = negative_labels
            except Exception as e:
                logger.error(f"尝试从任务获取负向标签时出错: {str(e)}")
        
        published_date = content.get("published", "未知")
        
        # 更详细地记录内容
        logger.info(f"\n============ 开始评估内容 (最多尝试 {max_attempts} 次) ============")
        logger.info(f"标题: {title}")
        logger.info(f"链接: {content.get('link', '无链接')}")
        logger.info(f"来源: {content.get('source', '未知来源')}")
        logger.info(f"RSS源标签: {feed_labels}")
        logger.info(f"RSS源反向标签: {negative_labels}")
        logger.info(f"当前时间: {datetime.now().isoformat()}")
        
        # 打印摘要（截断以防太长）
        summary_to_log = summary[:500] + "..." if len(summary) > 500 else summary
        logger.info(f"摘要: {summary_to_log}")
        
        # 打印发布时间
        if published_date != "未知":
            logger.info(f"发布时间: {published_date}")
            # 如果有发布时间，计算内容的年龄
            try:
                # Parse the date string
                pub_datetime = datetime.fromisoformat(published_date)

                # Get the current time as an aware UTC datetime
                now_aware_utc = datetime.now(timezone.utc)

                # Ensure pub_datetime is aware and in UTC
                if pub_datetime.tzinfo is None:
                    # If naive, assume UTC
                    pub_datetime_aware_utc = pub_datetime.replace(tzinfo=timezone.utc)
                    logger.info("发布时间无时区信息，假设为UTC")
                else:
                    # If aware, convert to UTC
                    pub_datetime_aware_utc = pub_datetime.astimezone(timezone.utc)

                # Calculate age using aware datetimes
                age = now_aware_utc - pub_datetime_aware_utc
                logger.info(f"内容年龄: {age.days} 天 {age.seconds//3600} 小时")
            except ValueError:
                # Catch only parsing errors
                logger.warning(f"无法解析发布时间格式: {published_date}")
            except Exception as e:
                # Catch any other unexpected errors during age calculation/conversion
                logger.error(f"计算内容年龄时出错: {e}")
        
        # 构建初始提示词
        current_prompt = self._build_evaluation_prompt(content)
        last_error = None
        evaluation_text = "" # Store last AI response for correction prompt

        for attempt in range(max_attempts):
            logger.info(f"--- 评估尝试 {attempt + 1}/{max_attempts} ---")
            if attempt > 0: # If retrying, use correction prompt
                logger.info("构建修正提示词...")
                current_prompt = self._build_correction_prompt(self._build_evaluation_prompt(content), evaluation_text, str(last_error))

            logger.info(f"向AI发送提示词长度: {len(current_prompt)} 字符")
            logger.info(f"提示词前100字符: {current_prompt[:100]}...")

            try:
                # 调用AI服务
                logger.info(f"使用{self.provider}评估内容, 模型: {self.ollama_model or self.openai_model}")
                evaluation_text = self.ai_service.call_ai(current_prompt)
                logger.info(f"AI响应长度: {len(evaluation_text)} 字符")

                # 解析评估结果 (可能会抛出 AiException)
                evaluation_result = self._parse_evaluation(evaluation_text)

                # 成功解析，记录结果
                is_match = evaluation_result["interest_match"]["is_match"]
                matched_tags = evaluation_result["interest_match"]["matched_tags"]
                negative_match = evaluation_result["negative_match"]["is_match"]
                negative_matched_tags = evaluation_result["negative_match"]["matched_tags"]
                importance = evaluation_result["importance"]["rating"]
                timeliness = evaluation_result["timeliness"]["rating"]
                interest_level = evaluation_result["interest_level"]["rating"]

                logger.info(f"评估结果 (尝试 {attempt + 1}): 兴趣匹配={is_match} {matched_tags}, 反向标签匹配={negative_match} {negative_matched_tags}, 重要性={importance}, 时效性={timeliness}, 趣味性={interest_level}")

                # 更新并返回内容字典
                content.update({
                    "evaluation": evaluation_result,
                    "keep": self._should_keep_content(evaluation_result)
                })
                logger.info(f"成功解析AI响应并完成评估 (尝试 {attempt + 1})")
                return content # Success

            except AiException as e:
                last_error = e
                logger.warning(f"评估尝试 {attempt + 1} 失败: {str(e)}")
                if attempt + 1 == max_attempts:
                    logger.error(f"已达到最大尝试次数 ({max_attempts})，评估最终失败。")
                    content.update({
                        "evaluation": {"error": f"AI评估失败 (尝试 {max_attempts} 次): {str(last_error)}"},
                        "keep": False # 标记为丢弃
                    })
                    return content # Return with error after max attempts
                else:
                    logger.info("准备重试...")
                    # Loop continues to next attempt

            except Exception as e: # Catch other unexpected errors during AI call or parsing
                 last_error = e
                 logger.error(f"评估尝试 {attempt + 1} 遇到意外错误: {str(e)}", exc_info=True)
                 # Treat unexpected errors as final failure for this item
                 content.update({
                     "evaluation": {"error": f"AI评估意外失败: {str(last_error)}"},
                     "keep": False
                 })
                 return content

        # Fallback if loop finishes unexpectedly (should not happen with returns)
        logger.error("评估逻辑异常结束")
        content.update({
            "evaluation": {"error": f"AI评估最终失败: {str(last_error)}"},
            "keep": False
        })
        return content

    def _build_evaluation_prompt(self, content: Dict[str, Any]) -> str:
        """构建用于评估内容的提示词
        
        Args:
            content: 新闻内容，包括feed_labels表示该RSS源特有的标签
            
        Returns:
            格式化的提示词
        """
        # 构建详细的提示词，要求AI评估内容并提供结构化输出
        title = content.get("title", "")
        summary = content.get("summary", "")
        full_content = content.get("content", "")
        feed_labels = content.get("feed_labels", [])
        negative_labels = content.get("negative_labels", [])
        
        # 获取当前日期时间信息
        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime("%Y年%m月%d日")
        current_time_str = current_datetime.strftime("%H:%M:%S")
        current_weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][current_datetime.weekday()]
        
        # 如果摘要或全文很长，进行截断
        if len(summary) > 1000:
            summary = summary[:1000] + "..."
        if len(full_content) > 3000:
            full_content = full_content[:3000] + "..."
        
        # 将兴趣标签格式化为字符串 - 使用RSS源特定的标签
        interests_str = ", ".join([f'"{tag}"' for tag in feed_labels])
        
        # 将反向标签格式化为字符串
        negative_interests_str = ", ".join([f'"{tag}"' for tag in negative_labels]) if negative_labels else "无反向标签"
        
        # 提取内容的发布时间（如果有）进行记录
        content_published = content.get("published", "未知")
        published_info = f"发布时间：{content_published}" if content_published else "发布时间：未提供"
        
        prompt_base = f"""请分析以下新闻内容，并根据给定标准进行评估：

## 当前时间信息
当前日期：{current_date_str} {current_weekday}
当前时间：{current_time_str}

## 新闻内容
标题：{title}
{published_info}
摘要：{summary}
全文：{full_content}

## 该RSS源关注的标签
{interests_str}

## 该RSS源的反向标签（不希望看到的内容类型）
{negative_interests_str}

## 评估要求
1. 兴趣匹配：这条新闻是否符合该RSS源关注的一个或多个标签？如果有，请指明具体匹配的标签；如果不符合任何标签，请说明。
2. 反向标签匹配：这条新闻是否符合任何反向标签？如果有，请指明具体匹配的反向标签；如果不符合任何反向标签，请说明。
3. 重要性：这条新闻的重要性如何？（极低、低、中、高、极高）
4. 时效性：考虑当前日期（{current_date_str}），该新闻的时效性如何？（极低、低、中、高、极高）
   - 极高：今日/昨日的突发新闻或重大事件
   - 高：本周内的重要发展或更新
   - 中：本月内的相关信息
   - 低：几个月前的旧闻或一般性信息
   - 极低：明显过时或与当前环境无关的内容
5. 趣味性：这条新闻的趣味性如何？（极低、低、中、高、极高）
"""
        prompt_json_format = f"""
请按以下JSON格式返回评估结果：
{{
  "interest_match": {{
    "is_match": true/false,
    "matched_tags": ["标签1", "标签2"],
    "explanation": "解释为什么匹配或不匹配"
  }},
  "negative_match": {{
    "is_match": true/false,
    "matched_tags": ["反向标签1", "反向标签2"],
    "explanation": "解释为什么匹配或不匹配反向标签"
  }},
  "importance": {{
    "rating": "极低/低/中/高/极高",
    "explanation": "解释为什么给出这个评级"
  }},
  "timeliness": {{
    "rating": "极低/低/中/高/极高",
    "explanation": "解释为什么给出这个评级"
  }},
  "interest_level": {{
    "rating": "极低/低/中/高/极高",
    "explanation": "解释为什么给出这个评级"
  }}
}}

**请务必严格遵守此JSON格式。**请只返回JSON对象，不要包含任何其他文本或注释。
"""
        return prompt_base + prompt_json_format

    def _build_correction_prompt(self, original_request_prompt: str, failed_response: str, error_message: str) -> str:
        """构建用于请求AI修正其先前格式错误的响应的提示词。"""
        # Extract the format definition part from the original prompt
        format_start_keyword = "请按以下JSON格式返回评估结果："
        format_part_index = original_request_prompt.find(format_start_keyword)
        if format_part_index != -1:
            original_format_request = original_request_prompt[format_part_index:]
        else:
            original_format_request = "请严格按照之前要求的JSON格式输出。" # Fallback

        return f"""你上一次的响应未能满足格式要求。错误详情：'{error_message}'.

这是你上次错误的响应内容（或部分内容）：
---
{failed_response[:1000]} {'...' if len(failed_response)>1000 else ''}
---

请根据以下原始请求中的格式要求，重新生成响应。请特别注意确保所有必需的字段都存在且类型正确（例如 `is_match` 必须是 `true` 或 `false`，`rating` 必须是指定的等级之一）。

原始格式要求：
---
{original_format_request}
---

请只返回修正后的JSON对象，不要包含任何额外的解释、道歉或注释。
"""

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
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """解析AI评估结果，并进行严格的结构验证
        
        Args:
            evaluation_text: AI响应文本
            
        Returns:
            解析并验证后的评估结果
            
        Raises:
            AiException: 当评估结果解析失败或结构不符合要求时
        """
        # 记录AI的完整响应
        logger.info(f"\n============ AI响应内容 ============")
        logger.info(f"AI响应原文 ({len(evaluation_text)} 字符):\n{evaluation_text}\n")
        
        # 清除可能存在的思考过程
        cleaned_text = self._clean_thinking_process(evaluation_text)
        if cleaned_text != evaluation_text:
            logger.info(f"检测到并清理了AI思考过程，清理后长度: {len(cleaned_text)} 字符")
        
        try:
            # 使用清理后的文本进行解析
            result = self.ai_service.parse_json_response(cleaned_text)
        except Exception as e:
            logger.warning(f"初次解析JSON失败: {str(e)}，尝试提取JSON块...")
            try:
                # Attempt to find and extract JSON block more robustly
                start_idx = -1
                brace_level = 0
                json_start_found = False
                potential_json = ""

                # Find the first opening brace
                first_brace = cleaned_text.find('{')
                if first_brace == -1:
                    raise ValueError("未找到JSON开始标记 '{'")

                # Iterate from the first brace to find the matching closing brace
                for i, char in enumerate(cleaned_text[first_brace:]):
                    if (char == '{'):
                        if not json_start_found:
                            start_idx = first_brace + i
                            json_start_found = True
                        brace_level += 1
                    elif char == '}':
                        brace_level -= 1

                    if json_start_found and brace_level == 0:
                        # Found the end of the main JSON object
                        potential_json = cleaned_text[start_idx : first_brace + i + 1]
                        break # Stop after finding the first complete object

                if not potential_json:
                     raise ValueError("未找到完整的JSON对象（括号不匹配或未结束）")

                result = json.loads(potential_json)
                logger.info(f"成功提取并解析JSON块: {potential_json[:100]}...")

            except Exception as e2:
                # Combine original and extraction errors for clarity
                raise AiException(f"无法解析AI响应的JSON格式: 原始错误='{str(e)}', 提取/修复错误='{str(e2)}'") from e2

        # --- Start Structure Validation ---
        required_top_level_fields = ["interest_match", "negative_match", "importance", "timeliness", "interest_level"]
        missing_top_level = [k for k in required_top_level_fields if k not in result]

        # Handle missing negative_match specifically
        if "negative_match" in missing_top_level:
            logger.warning("AI响应中缺少negative_match字段，使用默认值")
            result["negative_match"] = {
                "is_match": False,
                "matched_tags": [],
                "explanation": "AI未评估反向标签匹配"
            }
            missing_top_level.remove("negative_match") # Remove from missing list

        if missing_top_level: # If other fields are still missing
            raise AiException(f"AI响应缺少必要的顶级评估字段: {missing_top_level}")

        # Validate nested structures
        required_match_fields = ["is_match", "matched_tags", "explanation"]
        required_rating_fields = ["rating", "explanation"]

        # Check interest_match
        interest_match = result.get("interest_match", {})
        missing_interest = [k for k in required_match_fields if k not in interest_match]
        if missing_interest:
            raise AiException(f"AI响应 'interest_match' 字段结构错误，缺少: {missing_interest}")
        if not isinstance(interest_match.get("is_match"), bool):
            raise AiException(f"AI响应 'interest_match.is_match' 字段必须是布尔值 (true/false)，但收到类型: {type(interest_match.get('is_match'))} 值: {interest_match.get('is_match')}")
        if not isinstance(interest_match.get("matched_tags"), list):
             raise AiException(f"AI响应 'interest_match.matched_tags' 字段必须是列表")

        # Check negative_match
        negative_match = result.get("negative_match", {})
        missing_negative = [k for k in required_match_fields if k not in negative_match]
        # Allow for the default added case where explanation might be missing
        if missing_negative and not (negative_match.get("explanation") == "AI未评估反向标签匹配" and 'explanation' in missing_negative and len(missing_negative) == 1):
             raise AiException(f"AI响应 'negative_match' 字段结构错误，缺少: {missing_negative}")
        # Check type only if is_match exists
        if "is_match" in negative_match and not isinstance(negative_match.get("is_match"), bool):
             raise AiException(f"AI响应 'negative_match.is_match' 字段必须是布尔值 (true/false)，但收到类型: {type(negative_match.get('is_match'))} 值: {negative_match.get('is_match')}")
        if "matched_tags" in negative_match and not isinstance(negative_match.get("matched_tags"), list):
             raise AiException(f"AI响应 'negative_match.matched_tags' 字段必须是列表")

        # Check importance, timeliness, interest_level
        valid_ratings = [r.value for r in RatingLevel if r != RatingLevel.UNKNOWN]
        for field_name in ["importance", "timeliness", "interest_level"]:
            rating_field = result.get(field_name, {})
            missing_rating = [k for k in required_rating_fields if k not in rating_field]
            if missing_rating:
                raise AiException(f"AI响应 '{field_name}' 字段结构错误，缺少: {missing_rating}")
            # Validate rating value against RatingLevel enum values
            rating_value = rating_field.get("rating")
            if rating_value not in valid_ratings:
                 raise AiException(f"AI响应 '{field_name}.rating' 字段值 '{rating_value}' 无效。有效值: {valid_ratings}")

        # --- End Structure Validation ---

        # Log parsed results (only if validation passed)
        logger.info(f"\n============ AI评估结果 (结构验证通过) ============")
        # 记录解析结果
        is_match = result["interest_match"]["is_match"]
        matched_tags = result["interest_match"]["matched_tags"]
        negative_match = result["negative_match"]["is_match"]
        negative_matched_tags = result["negative_match"].get("matched_tags", [])
        importance = result["importance"]["rating"]
        timeliness = result["timeliness"]["rating"]
        interest_level = result["interest_level"]["rating"]
        
        logger.info(f"兴趣匹配: {is_match}")
        logger.info(f"匹配标签: {matched_tags}")
        logger.info(f"匹配解释: {result['interest_match']['explanation']}")
        logger.info(f"反向标签匹配: {negative_match}")
        logger.info(f"匹配的反向标签: {negative_matched_tags}")
        logger.info(f"反向匹配解释: {result['negative_match'].get('explanation', '无解释')}")
        logger.info(f"重要性: {importance}")
        logger.info(f"重要性解释: {result['importance']['explanation']}")
        logger.info(f"时效性: {timeliness}")
        logger.info(f"时效性解释: {result['timeliness']['explanation']}")
        logger.info(f"趣味性: {interest_level}")
        logger.info(f"趣味性解释: {result['interest_level']['explanation']}")
            
        return result
    
    def _should_keep_content(self, evaluation: Dict[str, Any]) -> bool:
        """根据评估结果决定是否保留内容"""
        # Handle potential error during evaluation (added by evaluate_content on failure)
        if "error" in evaluation:
            logger.warning(f"内容评估包含错误，将丢弃: {evaluation['error']}")
            return False

        # 提取评估信息
        is_interest_match = evaluation["interest_match"]["is_match"]
        matched_tags = evaluation["interest_match"]["matched_tags"]
        
        # 检查反向标签匹配
        is_negative_match = evaluation["negative_match"]["is_match"]
        negative_matched_tags = evaluation["negative_match"].get("matched_tags", [])
        
        # Convert rating strings to Enum members for comparison
        try:
            importance = RatingLevel(evaluation["importance"]["rating"])
            timeliness = RatingLevel(evaluation["timeliness"]["rating"])
            interest_level = RatingLevel(evaluation["interest_level"]["rating"])
        except ValueError as e:
             # This should not happen due to validation in _parse_evaluation
             logger.error(f"内部错误：无效的评级值 '{e}' 绕过了验证。将丢弃内容。")
             return False
        
        # 记录详细的筛选逻辑
        logger.info(f"\n============ 过滤决策过程 ============")
        logger.info(f"兴趣匹配: {is_interest_match} (标签: {matched_tags})")
        logger.info(f"反向标签匹配: {is_negative_match} (匹配标签: {negative_matched_tags})")
        logger.info(f"重要性: {importance.value}") # Use .value for logging string
        logger.info(f"时效性: {timeliness.value}")
        logger.info(f"趣味性: {interest_level.value}")
        
        # 首先检查反向标签 - 如果匹配任何反向标签，立即丢弃
        if is_negative_match and negative_matched_tags:
            logger.info("条件检查0: 内容匹配反向标签")
            logger.info(f"丢弃原因：匹配反向标签 {negative_matched_tags}")
            return False
        
        # 筛选逻辑检查，记录每个检查的结果
        # 1. 如果不是用户兴趣且重要性不是极高且不是极有意思，丢弃
        if not is_interest_match:
            logger.info("条件检查1: 内容不匹配用户兴趣")
            if importance != RatingLevel.VERY_HIGH:
                logger.info(f"条件检查1.1: 重要性 ({importance.value}) 不是极高")
                if interest_level != RatingLevel.VERY_HIGH:
                    logger.info(f"条件检查1.2: 趣味性 ({interest_level.value}) 不是极高")
                    logger.info("丢弃原因：不是用户兴趣且重要性不是极高且趣味性不是极高")
                    return False
                else:
                    logger.info("保留原因：虽然不匹配用户兴趣且重要性不是极高，但趣味性极高")
            else:
                logger.info("保留原因：虽然不匹配用户兴趣，但重要性极高")
        
        # 2. 如果是用户兴趣但重要性低或极低且趣味性低或极低，丢弃
        if is_interest_match:
            logger.info("条件检查2: 内容匹配用户兴趣")
            if importance in [RatingLevel.LOW, RatingLevel.VERY_LOW]:
                logger.info(f"条件检查2.1: 重要性 {importance.value}（低或极低）")
                if interest_level in [RatingLevel.LOW, RatingLevel.VERY_LOW]:
                    logger.info(f"条件检查2.2: 趣味性 {interest_level.value}（低或极低）")
                    logger.info("丢弃原因：是用户兴趣但重要性低/极低且趣味性低/极低")
                    return False
                else:
                     logger.info(f"保留原因：虽然重要性低/极低，但趣味性 ({interest_level.value}) 不低")
            else:
                 logger.info(f"保留原因：重要性 ({importance.value}) 不低")
        
        # 3. 如果时效性极低，丢弃
        if timeliness == RatingLevel.VERY_LOW:
            logger.info("条件检查3: 时效性极低")
            logger.info("丢弃原因：时效性极低")
            return False
        
        # 4. 如果重要性和趣味性都是极低，丢弃
        if importance == RatingLevel.VERY_LOW and interest_level == RatingLevel.VERY_LOW:
            logger.info("条件检查4: 重要性和趣味性都是极低")
            logger.info("丢弃原因：重要性和趣味性都是极低")
            return False
        
        # 通过所有筛选条件，保留内容
        logger.info("最终决定: 保留 - 通过所有筛选条件")
        return True
        
    def filter_content_batch(self, contents: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """批量评估和过滤新闻内容
        
        Args:
            contents: 新闻内容列表，每个内容包括feed_labels表示该RSS源特有的标签
            
        Returns:
            保留的内容列表和丢弃的内容列表
            
        Raises:
            AiException: 当批量处理中出现致命错误时
        """
        kept_contents = []
        discarded_contents = []
        
        # 检查是否有内容需要处理
        if not contents:
            logger.warning("无内容需要过滤")
            return kept_contents, discarded_contents
            
        logger.info(f"开始过滤 {len(contents)} 条内容，使用各个内容所属的源标签")
        
        for index, content in enumerate(contents):
            # No try-except block needed here for evaluate_content itself,
            # as it now handles its own errors and returns a result regardless.
            title = content.get("title", "无标题")
            feed_labels = content.get("feed_labels", [])
            
            # 增强逻辑，确保我们有负向标签
            negative_labels = content.get("negative_labels", [])
            feed_url = content.get("feed_url")
            task = content.get("task")
            
            # 如果没有负向标签但有任务对象和feed URL，则从任务配置中获取
            if not negative_labels and task and feed_url and hasattr(task, 'get_feed_negative_labels'):
                try:
                    negative_labels = task.get_feed_negative_labels(feed_url)
                    content["negative_labels"] = negative_labels
                except Exception as e:
                    logger.error(f"尝试从任务获取负向标签时出错: {str(e)}")
            
            label_info = f"标签: {feed_labels}"
            if negative_labels:
                label_info += f", 反向标签: {negative_labels}"
            
            logger.info(f"过滤进度: {index+1}/{len(contents)} - {title[:30]}{'...' if len(title) > 30 else ''} ({label_info})")
            
            # 评估每个内容 (now handles retries internally and returns error state if failed)
            evaluated_content = self.evaluate_content(content) # Pass content directly
            
            # 根据评估结果分类 (evaluate_content adds 'keep' and 'evaluation' with potential 'error')
            if evaluated_content.get("keep", False):
                logger.info(f"决定: 保留内容 #{index+1}")
                kept_contents.append(evaluated_content)
            else:
                # Check if discard was due to an evaluation error recorded by evaluate_content
                eval_data = evaluated_content.get("evaluation", {})
                if isinstance(eval_data, dict) and "error" in eval_data:
                     logger.warning(f"决定: 丢弃内容 #{index+1} (原因: {eval_data['error']})")
                else:
                     logger.info(f"决定: 丢弃内容 #{index+1} (原因: 过滤器规则)")
                discarded_contents.append(evaluated_content)
        
        logger.info(f"过滤完成: 共 {len(contents)} 条内容, 保留 {len(kept_contents)} 条, 丢弃 {len(discarded_contents)} 条")
        
        # 在完成过滤后添加更多统计信息
        if kept_contents or discarded_contents:
            logger.info(f"\n============ 过滤统计 ============")
            total_processed = len(contents)
            logger.info(f"总内容数: {total_processed}")
            logger.info(f"保留内容数: {len(kept_contents)} ({len(kept_contents)/total_processed*100:.1f}%)")
            logger.info(f"丢弃内容数: {len(discarded_contents)} ({len(discarded_contents)/total_processed*100:.1f}%)")
            
            error_count = sum(1 for c in discarded_contents if isinstance(c.get("evaluation"), dict) and "error" in c["evaluation"])
            if error_count > 0:
                logger.info(f"因评估错误丢弃数: {error_count}")
            
            # 记录丢弃内容的标题
            if discarded_contents:
                logger.info(f"\n============ 被丢弃的内容 ============")
                for i, content in enumerate(discarded_contents):
                    title = content.get("title", "无标题")
                    reason = "未知原因"
                    eval_data = content.get("evaluation", {})
                    if isinstance(eval_data, dict):
                        if "error" in eval_data:
                            reason = f"评估错误: {eval_data['error']}"
                        else:
                            # Attempt to reconstruct reason from valid evaluation data if available
                            try:
                                is_match = eval_data.get("interest_match", {}).get("is_match", "未知")
                                negative_match = eval_data.get("negative_match", {}).get("is_match", "未知")
                                negative_tags = eval_data.get("negative_match", {}).get("matched_tags", [])
                                importance = eval_data.get("importance", {}).get("rating", "未知")
                                timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                                interest_level = eval_data.get("interest_level", {}).get("rating", "未知")

                                # Use Enum for comparison if possible
                                try: importance_enum = RatingLevel(importance)
                                except: importance_enum = RatingLevel.UNKNOWN
                                try: timeliness_enum = RatingLevel(timeliness)
                                except: timeliness_enum = RatingLevel.UNKNOWN
                                try: interest_level_enum = RatingLevel(interest_level)
                                except: interest_level_enum = RatingLevel.UNKNOWN

                                if negative_match is True:
                                    reason = f"匹配反向标签: {negative_tags}"
                                elif is_match is False and importance_enum != RatingLevel.VERY_HIGH and interest_level_enum != RatingLevel.VERY_HIGH:
                                     reason = f"非兴趣({is_match}), 重要性({importance})非极高, 趣味性({interest_level})非极高"
                                elif is_match is True and importance_enum in [RatingLevel.LOW, RatingLevel.VERY_LOW] and interest_level_enum in [RatingLevel.LOW, RatingLevel.VERY_LOW]:
                                     reason = f"兴趣({is_match}), 但重要性({importance})低/极低 且 趣味性({interest_level})低/极低"
                                elif timeliness_enum == RatingLevel.VERY_LOW:
                                     reason = f"时效性({timeliness})极低"
                                elif importance_enum == RatingLevel.VERY_LOW and interest_level_enum == RatingLevel.VERY_LOW:
                                     reason = f"重要性({importance})极低 且 趣味性({interest_level})极低"
                                else:
                                     reason = f"通过规则过滤 (兴趣:{is_match}, 重要:{importance}, 时效:{timeliness}, 趣味:{interest_level}, 反向:{negative_match})"
                            except Exception as ex:
                                reason = f"记录丢弃原因时出错: {ex}"
                    logger.info(f"丢弃 #{i+1}: {title[:60]}{'...' if len(title)>60 else ''} - {reason}")
            
            # 记录保留内容的标题
            if kept_contents:
                logger.info(f"\n============ 保留的内容 ============")
                for i, content in enumerate(kept_contents):
                    title = content.get("title", "无标题")
                    reason = "未记录原因"
                    eval_data = content.get("evaluation", {})
                    if isinstance(eval_data, dict) and "error" not in eval_data:
                        try:
                            is_match = eval_data.get("interest_match", {}).get("is_match", "未知")
                            negative_match = eval_data.get("negative_match", {}).get("is_match", "未知")
                            importance = eval_data.get("importance", {}).get("rating", "未知")
                            timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                            interest_level = eval_data.get("interest_level", {}).get("rating", "未知")
                            reason = f"兴趣:{is_match}, 反向:{negative_match}, 重要:{importance}, 时效:{timeliness}, 趣味:{interest_level}"
                        except Exception as ex:
                            reason = f"记录保留原因时出错: {ex}"
                    else:
                        reason = "评估数据无效或包含错误" # Should not happen for kept items
                    logger.info(f"保留 #{i+1}: {title[:60]}{'...' if len(title)>60 else ''} - {reason}")
                    
        return kept_contents, discarded_contents
