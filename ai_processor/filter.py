import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
from ai_processor.ai_utils import AiService, AiException
import json

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
    
    def evaluate_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """评估新闻内容，检查是否符合用户兴趣，并评价重要性、时效性、趣味性
        
        Args:
            content: 新闻内容
            
        Returns:
            评估后的内容，包含评估结果
            
        Raises:
            AiException: 当AI评估失败时
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
        logger.info(f"\n============ 开始评估内容 ============")
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
                pub_datetime = datetime.fromisoformat(published_date)
                age = datetime.now() - pub_datetime
                logger.info(f"内容年龄: {age.days} 天 {age.seconds//3600} 小时")
            except (ValueError, TypeError):
                logger.info("无法解析发布时间格式")
        
        # 构建提示词，要求AI评估内容
        prompt = self._build_evaluation_prompt(content)
        logger.info(f"向AI发送的提示词长度: {len(prompt)} 字符")
        logger.info(f"提示词前100字符: {prompt[:100]}...")
        
        # 调用AI服务，如果失败将抛出异常
        logger.info(f"使用{self.provider}评估内容, 模型: {self.ollama_model or self.openai_model}")
        evaluation = self.ai_service.call_ai(prompt)
        
        logger.info(f"AI响应长度: {len(evaluation)} 字符")
        # 解析评估结果，如果失败将抛出异常
        evaluation_result = self._parse_evaluation(evaluation)
        
        # 记录评估结果
        is_match = evaluation_result["interest_match"]["is_match"]
        matched_tags = evaluation_result["interest_match"]["matched_tags"]
        negative_match = evaluation_result["negative_match"]["is_match"]
        negative_matched_tags = evaluation_result["negative_match"]["matched_tags"]
        importance = evaluation_result["importance"]["rating"]
        timeliness = evaluation_result["timeliness"]["rating"]
        interest_level = evaluation_result["interest_level"]["rating"]
        
        logger.info(f"评估结果: 兴趣匹配={is_match} {matched_tags}, 反向标签匹配={negative_match} {negative_matched_tags}, 重要性={importance}, 时效性={timeliness}, 趣味性={interest_level}")
        
        # 更新并返回内容字典
        content.update({
            "evaluation": evaluation_result,
            "keep": self._should_keep_content(evaluation_result)
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
        
        return f"""请分析以下新闻内容，并根据给定标准进行评估：

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
1. 兴趣匹配：这条新闻是否符合该RSS源关注的标签？如果有，请指明具体匹配的标签；如果不符合任何标签，请说明。
2. 反向标签匹配：这条新闻是否符合任何反向标签？如果有，请指明具体匹配的反向标签；如果不符合任何反向标签，请说明。
3. 重要性：这条新闻的重要性如何？（极低、低、中、高、极高）
4. 时效性：考虑当前日期（{current_date_str}），该新闻的时效性如何？（极低、低、中、高、极高）
   - 极高：今日/昨日的突发新闻或重大事件
   - 高：本周内的重要发展或更新
   - 中：本月内的相关信息
   - 低：几个月前的旧闻或一般性信息
   - 极低：明显过时或与当前环境无关的内容
5. 趣味性：这条新闻的趣味性如何？（极低、低、中、高、极高）

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

请只返回JSON格式的评估结果，严格遵守要求中定义的JSON格式，不要有任何其他文本。
"""
    
    def _clean_thinking_process(self, text: str) -> str:
        """清除AI推理模型中的思考过程（被<think></think>包裹的内容）
        
        Args:
            text: AI响应文本
            
        Returns:
            清除思考过程后的文本
        """
        import re
        # 使用非贪婪匹配移除所有<think>...</think>标记之间的内容
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        return cleaned_text
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """解析AI评估结果
        
        Args:
            evaluation_text: AI响应文本
            
        Returns:
            解析后的评估结果
            
        Raises:
            AiException: 当评估结果解析失败时
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
            # 如果解析失败，尝试修复常见的JSON错误
            logger.warning(f"初次解析JSON失败: {str(e)}，尝试修复JSON...")
            
            try:
                # 尝试修复缺少结束大括号的问题
                fixed_json = cleaned_text.strip()
                # 统计左右大括号数量
                open_braces = fixed_json.count('{')
                close_braces = fixed_json.count('}')
                
                # 如果缺少右大括号，添加缺少的部分
                if open_braces > close_braces:
                    logger.info(f"检测到缺少 {open_braces - close_braces} 个右大括号，尝试修复")
                    fixed_json += "}" * (open_braces - close_braces)
                
                # 尝试再次解析
                result = json.loads(fixed_json)
                logger.info("JSON修复成功")
            except Exception as e2:
                # 如果仍然失败，尝试使用更严格的方式查找JSON部分
                logger.warning(f"修复JSON仍然失败: {str(e2)}，尝试提取JSON部分...")
                
                try:
                    # 尝试找到JSON的开始和结束位置
                    start_idx = cleaned_text.find('{')
                    if start_idx != -1:
                        # 从找到的第一个 { 开始尝试解析
                        potential_json = cleaned_text[start_idx:]
                        # 确保JSON对象完整
                        open_count = 0
                        for i, char in enumerate(potential_json):
                            if char == '{':
                                open_count += 1
                            elif char == '}':
                                open_count -= 1
                                if open_count == 0:
                                    # 找到完整的JSON对象
                                    complete_json = potential_json[:i+1]
                                    result = json.loads(complete_json)
                                    logger.info(f"成功提取并解析JSON部分: {complete_json[:50]}...")
                                    break
                    else:
                        raise AiException("无法在AI响应中找到JSON开始标记")
                except Exception as e3:
                    # 所有尝试都失败，抛出组合异常
                    raise AiException(f"无法解析AI响应的JSON格式: 原始错误: {str(e)}, 修复尝试错误: {str(e2)}, 提取尝试错误: {str(e3)}")
        
        # 验证结果结构
        required_fields = ["interest_match", "importance", "timeliness", "interest_level"]
        
        # 添加对反向标签的处理
        if "negative_match" not in result:
            # 如果AI没有返回negative_match字段，添加一个默认值
            logger.warning("AI响应中缺少negative_match字段，使用默认值")
            result["negative_match"] = {
                "is_match": False,
                "matched_tags": [],
                "explanation": "AI未评估反向标签匹配"
            }
        
        if not all(k in result for k in required_fields):
            raise AiException("AI响应缺少必要的评估字段，请检查AI响应格式")
        
        # 记录解析结果
        is_match = result["interest_match"]["is_match"]
        matched_tags = result["interest_match"]["matched_tags"]
        negative_match = result["negative_match"]["is_match"]
        negative_matched_tags = result["negative_match"].get("matched_tags", [])
        importance = result["importance"]["rating"]
        timeliness = result["timeliness"]["rating"]
        interest_level = result["interest_level"]["rating"]
        
        logger.info(f"\n============ AI评估结果 ============")
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
        # 提取评估信息
        is_interest_match = evaluation["interest_match"]["is_match"]
        matched_tags = evaluation["interest_match"]["matched_tags"]
        
        # 检查反向标签匹配
        is_negative_match = evaluation["negative_match"]["is_match"]
        negative_matched_tags = evaluation["negative_match"].get("matched_tags", [])
        
        importance = evaluation["importance"]["rating"]
        timeliness = evaluation["timeliness"]["rating"]
        interest_level = evaluation["interest_level"]["rating"]
        
        # 记录详细的筛选逻辑
        logger.info(f"\n============ 过滤决策过程 ============")
        logger.info(f"兴趣匹配: {is_interest_match} (标签: {matched_tags})")
        logger.info(f"反向标签匹配: {is_negative_match} (匹配标签: {negative_matched_tags})")
        logger.info(f"重要性: {importance}")
        logger.info(f"时效性: {timeliness}")
        logger.info(f"趣味性: {interest_level}")
        
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
                logger.info("条件检查1.1: 重要性不是极高")
                if interest_level != RatingLevel.VERY_HIGH:
                    logger.info("条件检查1.2: 趣味性不是极高")
                    logger.info("丢弃原因：不是用户兴趣且重要性不是极高且不是极有意思")
                    return False
                else:
                    logger.info("保留原因：虽然不匹配用户兴趣且重要性不是极高，但趣味性极高")
            else:
                logger.info("保留原因：虽然不匹配用户兴趣，但重要性极高")
        
        # 2. 如果是用户兴趣但重要性低或极低且没有意思，丢弃
        if is_interest_match:
            logger.info("条件检查2: 内容匹配用户兴趣")
            if importance in [RatingLevel.LOW, RatingLevel.VERY_LOW]:
                logger.info(f"条件检查2.1: 重要性{importance}（低或极低）")
                if interest_level in [RatingLevel.LOW, RatingLevel.VERY_LOW]:
                    logger.info(f"条件检查2.2: 趣味性{interest_level}（低或极低）")
                    logger.info("丢弃原因：是用户兴趣但重要性低或极低且没有意思")
                    return False
        
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
            try:
                # 每条内容都显示进度
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
                
                # 评估每个内容
                evaluated_content = self.evaluate_content(content)
                
                # 根据评估结果分类
                if evaluated_content.get("keep", False):
                    logger.info(f"决定: 保留内容 #{index+1}")
                    kept_contents.append(evaluated_content)
                else:
                    logger.info(f"决定: 丢弃内容 #{index+1}")
                    discarded_contents.append(evaluated_content)
            except Exception as e:
                logger.error(f"过滤内容 #{index+1} 时出错: {str(e)}")
                # 如果是连续的多个错误，可能是AI服务问题，应该中断流程
                if index > 0 and index % 3 == 0 and len(kept_contents) == 0:
                    raise AiException(f"连续多条内容评估失败，可能是AI服务存在问题: {str(e)}")
                # 出错时将内容标记为丢弃
                content["error"] = str(e)
                discarded_contents.append(content)
        
        logger.info(f"过滤完成: 共 {len(contents)} 条内容, 保留 {len(kept_contents)} 条, 丢弃 {len(discarded_contents)} 条")
        
        # 在完成过滤后添加更多统计信息
        if kept_contents or discarded_contents:
            logger.info(f"\n============ 过滤统计 ============")
            logger.info(f"总内容数: {len(contents)}")
            logger.info(f"保留内容数: {len(kept_contents)} ({len(kept_contents)/len(contents)*100:.1f}%)")
            logger.info(f"丢弃内容数: {len(discarded_contents)} ({len(discarded_contents)/len(contents)*100:.1f}%)")
            
            # 记录丢弃内容的标题
            if discarded_contents:
                logger.info(f"\n============ 被丢弃的内容 ============")
                for i, content in enumerate(discarded_contents):
                    title = content.get("title", "无标题")
                    reason = "未记录原因"
                    if "evaluation" in content:
                        eval_data = content["evaluation"]
                        is_match = eval_data.get("interest_match", {}).get("is_match", False)
                        negative_match = eval_data.get("negative_match", {}).get("is_match", False)
                        negative_tags = eval_data.get("negative_match", {}).get("matched_tags", [])
                        importance = eval_data.get("importance", {}).get("rating", "未知")
                        timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                        interest_level = eval_data.get("interest_level", {}).get("rating", "未知")
                        
                        if negative_match:
                            reason = f"匹配反向标签: {negative_tags}, 兴趣匹配: {is_match}, 重要性: {importance}, 时效性: {timeliness}, 趣味性: {interest_level}"
                        else:
                            reason = f"兴趣匹配: {is_match}, 重要性: {importance}, 时效性: {timeliness}, 趣味性: {interest_level}"
                    logger.info(f"丢弃内容 #{i+1}: {title} - {reason}")
            
            # 记录保留内容的标题
            if kept_contents:
                logger.info(f"\n============ 保留的内容 ============")
                for i, content in enumerate(kept_contents):
                    title = content.get("title", "无标题")
                    reason = "未记录原因"
                    if "evaluation" in content:
                        eval_data = content["evaluation"]
                        is_match = eval_data.get("interest_match", {}).get("is_match", False)
                        negative_match = eval_data.get("negative_match", {}).get("is_match", False)
                        importance = eval_data.get("importance", {}).get("rating", "未知")
                        timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                        interest_level = eval_data.get("interest_level", {}).get("rating", "未知")
                        reason = f"兴趣匹配: {is_match}, 未匹配反向标签: {not negative_match}, 重要性: {importance}, 时效性: {timeliness}, 趣味性: {interest_level}"
                    logger.info(f"保留内容 #{i+1}: {title} - {reason}")
                    
        return kept_contents, discarded_contents
