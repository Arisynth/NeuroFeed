import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
from ai_processor.ai_utils import AiService

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
        """
        self.config = config or {}
        # 使用共享的AI服务
        self.ai_service = AiService(config)
        
        # 获取AI服务的可用状态和提供商
        self.ai_available = self.ai_service.ai_available
        self.provider = self.ai_service.provider
        self.ollama_model = getattr(self.ai_service, 'ollama_model', '')
        self.openai_model = getattr(self.ai_service, 'openai_model', '')
    
    def evaluate_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """评估新闻内容，检查是否符合用户兴趣，并评价重要性、时效性、趣味性"""
        title = content.get("title", "无标题")
        summary = content.get("summary", "")
        feed_labels = content.get("feed_labels", [])
        published_date = content.get("published", "未知")
        
        # 更详细地记录内容
        logger.info(f"\n============ 开始评估内容 ============")
        logger.info(f"标题: {title}")
        logger.info(f"链接: {content.get('link', '无链接')}")
        logger.info(f"来源: {content.get('source', '未知来源')}")
        logger.info(f"RSS源标签: {feed_labels}")
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
        
        # 如果AI不可用，使用基于规则的方法
        if not self.ai_available:
            logger.info(f"AI评估不可用: AI可用={self.ai_available}")
            logger.info(f"将使用基于规则的评估方法")
            return self._evaluate_content_rule_based(content)
        
        # 构建提示词，要求AI评估内容
        prompt = self._build_evaluation_prompt(content)
        logger.info(f"向AI发送的提示词长度: {len(prompt)} 字符")
        logger.info(f"提示词前100字符: {prompt[:100]}...")
        
        try:
            # 调用AI服务
            logger.info(f"使用{self.provider}评估内容, 模型: {self.ollama_model or self.openai_model}")
            evaluation = self.ai_service.call_ai(prompt)
            
            # 如果评估成功
            if evaluation:
                logger.info(f"AI响应长度: {len(evaluation)} 字符")
                # 解析评估结果
                evaluation_result = self._parse_evaluation(evaluation)
                
                # 记录评估结果
                is_match = evaluation_result["interest_match"]["is_match"]
                matched_tags = evaluation_result["interest_match"]["matched_tags"]
                importance = evaluation_result["importance"]["rating"]
                timeliness = evaluation_result["timeliness"]["rating"]
                interest_level = evaluation_result["interest_level"]["rating"]
                
                logger.info(f"评估结果: 兴趣匹配={is_match} {matched_tags}, 重要性={importance}, 时效性={timeliness}, 趣味性={interest_level}")
                
                # 更新并返回内容字典
                content.update({
                    "evaluation": evaluation_result,
                    "keep": self._should_keep_content(evaluation_result)
                })
            else:
                # 评估失败，使用规则方法
                logger.warning(f"AI评估失败，回退到规则方法")
                return self._evaluate_content_rule_based(content)
        except Exception as e:
            # 出现异常，使用规则方法
            logger.error(f"评估内容时出错: {str(e)}，回退到规则方法")
            return self._evaluate_content_rule_based(content)
        
        return content
    
    def _evaluate_content_rule_based(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """使用基于规则的方法评估内容
        
        Args:
            content: 新闻内容，包括feed_labels表示该RSS源特有的标签
            
        Returns:
            带有评估结果的内容字典
        """
        title = content.get("title", "").lower()
        summary = content.get("summary", "").lower()
        # 获取当前条目所属RSS源配置的特定标签
        feed_labels = content.get("feed_labels", [])
        
        logger.info(f"规则评估 - 标题: {title[:50]}{'...' if len(title) > 50 else ''}")
        logger.info(f"规则评估 - 源标签: {feed_labels}")
        
        # 检查标题和摘要中是否包含RSS源特定的标签
        interest_match = False
        matched_tags = []
        
        # 内容直接继承了feed的标签，我们认为它们是匹配的
        if feed_labels:
            interest_match = True
            matched_tags = feed_labels.copy()
            logger.info(f"内容匹配源标签: {matched_tags}")
        
        # 构建评估结果
        evaluation_result = {
            "interest_match": {
                "is_match": interest_match,
                "matched_tags": matched_tags,
                "explanation": "内容来自标记了这些标签的RSS源" if interest_match else "RSS源没有配置兴趣标签"
            },
            "importance": {
                "rating": RatingLevel.MEDIUM,  # 默认重要性为中等
                "explanation": "使用规则方法无法准确评估重要性"
            },
            "timeliness": {
                "rating": RatingLevel.HIGH,  # 默认假设RSS feed内容时效性高
                "explanation": "RSS feed通常包含最新内容"
            },
            "interest_level": {
                "rating": RatingLevel.MEDIUM,  # 默认趣味性为中等
                "explanation": "使用规则方法无法准确评估趣味性"
            }
        }
        
        # 如果匹配兴趣标签，提高重要性和趣味性评级
        if interest_match:
            evaluation_result["importance"]["rating"] = RatingLevel.HIGH
            evaluation_result["interest_level"]["rating"] = RatingLevel.HIGH
        
        # 更新内容字典
        keep_decision = self._should_keep_content(evaluation_result)
        logger.info(f"规则过滤决定: {'保留' if keep_decision else '丢弃'}")
        
        content.update({
            "evaluation": evaluation_result,
            "keep": keep_decision
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

## 评估要求
1. 兴趣匹配：这条新闻是否符合该RSS源关注的标签？如果有，请指明具体匹配的标签；如果不符合任何标签，请说明。
2. 重要性：这条新闻的重要性如何？（极低、低、中、高、极高）
3. 时效性：考虑当前日期（{current_date_str}），该新闻的时效性如何？（极低、低、中、高、极高）
   - 极高：今日/昨日的突发新闻或重大事件
   - 高：本周内的重要发展或更新
   - 中：本月内的相关信息
   - 低：几个月前的旧闻或一般性信息
   - 极低：明显过时或与当前环境无关的内容
4. 趣味性：这条新闻的趣味性如何？（极低、低、中、高、极高）

请按以下JSON格式返回评估结果：
{{ "interest_match": {{ "is_match": true/false, "matched_tags": ["标签1", "标签2"], "explanation": "解释为什么匹配或不匹配" }}, "importance": {{ "rating": "极低/低/中/高/极高", "explanation": "解释为什么给出这个评级" }}, "timeliness": {{ "rating": "极低/低/中/高/极高", "explanation": "解释为什么给出这个评级" }}, "interest_level": {{ "rating": "极低/低/中/高/极高", "explanation": "解释为什么给出这个评级" }} }}

请只返回JSON格式的评估结果，不要有任何其他文本。
"""
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """解析AI评估结果"""
        # 记录AI的完整响应
        logger.info(f"\n============ AI响应内容 ============")
        logger.info(f"AI响应原文 ({len(evaluation_text)} 字符):\n{evaluation_text}\n")
        
        # 使用共享的AI服务解析JSON
        result = self.ai_service.parse_json_response(evaluation_text)
        
        # 如果解析失败，返回默认结果
        if not result or not all(k in result for k in ["interest_match", "importance", "timeliness", "interest_level"]):
            logger.warning("AI响应缺少必要的评估字段或解析失败")
            # 创建默认结果
            default_result = {
                "interest_match": {
                    "is_match": False,
                    "matched_tags": [],
                    "explanation": "无法解析AI评估结果"
                },
                "importance": {
                    "rating": RatingLevel.UNKNOWN,
                    "explanation": "无法解析AI评估结果"
                },
                "timeliness": {
                    "rating": RatingLevel.UNKNOWN,
                    "explanation": "无法解析AI评估结果"
                },
                "interest_level": {
                    "rating": RatingLevel.UNKNOWN,
                    "explanation": "无法解析AI评估结果"
                }
            }
            return default_result
        
        # 记录解析结果
        is_match = result["interest_match"]["is_match"]
        matched_tags = result["interest_match"]["matched_tags"]
        importance = result["importance"]["rating"]
        timeliness = result["timeliness"]["rating"]
        interest_level = result["interest_level"]["rating"]
        
        logger.info(f"\n============ AI评估结果 ============")
        logger.info(f"兴趣匹配: {is_match}")
        logger.info(f"匹配标签: {matched_tags}")
        logger.info(f"匹配解释: {result['interest_match']['explanation']}")
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
        importance = evaluation["importance"]["rating"]
        timeliness = evaluation["timeliness"]["rating"]
        interest_level = evaluation["interest_level"]["rating"]
        
        # 记录详细的筛选逻辑
        logger.info(f"\n============ 过滤决策过程 ============")
        logger.info(f"兴趣匹配: {is_interest_match} (标签: {matched_tags})")
        logger.info(f"重要性: {importance}")
        logger.info(f"时效性: {timeliness}")
        logger.info(f"趣味性: {interest_level}")
        
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
                logger.info(f"过滤进度: {index+1}/{len(contents)} - {title[:30]}{'...' if len(title) > 30 else ''} (标签: {feed_labels})")
                
                # 评估每个内容 - 不再传入全局兴趣标签，而是使用内容自带的feed_labels
                evaluated_content = self.evaluate_content(content)
                
                # 根据评估结果分类
                if evaluated_content.get("keep", False):
                    logger.info(f"决定: 保留内容 #{index+1}")
                    kept_contents.append(evaluated_content)
                else:
                    logger.info(f"决定: 丢弃内容 #{index+1}")
                    discarded_contents.append(evaluated_content)
            except Exception as e:
                import traceback
                logger.error(f"过滤内容 #{index+1} 时出错: {str(e)}")
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                # 出错时默认丢弃内容
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
                        importance = eval_data.get("importance", {}).get("rating", "未知")
                        timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                        interest_level = eval_data.get("interest_level", {}).get("rating", "未知")
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
                        importance = eval_data.get("importance", {}).get("rating", "未知")
                        timeliness = eval_data.get("timeliness", {}).get("rating", "未知")
                        interest_level = eval_data.get("interest_level", {}).get("rating", "未知")
                        reason = f"兴趣匹配: {is_match}, 重要性: {importance}, 时效性: {timeliness}, 趣味性: {interest_level}"
                    logger.info(f"保留内容 #{i+1}: {title} - {reason}")
                    
        return kept_contents, discarded_contents
