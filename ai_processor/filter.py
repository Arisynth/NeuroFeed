import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import requests
from enum import Enum
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        # 从配置加载AI设置
        self.ai_settings = self.config.get("global_settings", {}).get("ai_settings", {})
        self.provider = self.ai_settings.get("provider", "ollama")
        self.ai_available = True  # 用于跟踪AI服务可用性
        self.connection_errors = 0  # 连接错误计数
        self.ai_error_threshold = 3  # 超过此阈值时切换到无AI模式
        
        if self.provider == "ollama":
            self.ollama_host = self.ai_settings.get("ollama_host", "http://localhost:11434")
            self.ollama_model = self.ai_settings.get("ollama_model", "llama2")
            
            # 检查Ollama是否可用
            if not self._check_ollama_availability():
                self.ai_available = False
                logger.warning(f"Ollama在{self.ollama_host}不可用，将使用基于规则的过滤")
        else:  # OpenAI
            self.openai_key = self.ai_settings.get("openai_key", "")
            self.openai_model = self.ai_settings.get("openai_model", "gpt-3.5-turbo")
            
            # 检查OpenAI是否可用
            if not self.openai_key:
                self.ai_available = False
                logger.warning("未提供OpenAI API密钥，将使用基于规则的过滤")
    
    def _check_ollama_availability(self) -> bool:
        """检查Ollama服务是否可用
        
        Returns:
            布尔值表示是否可用
        """
        try:
            # 尝试ping Ollama，5秒超时
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"无法连接到Ollama: {str(e)}")
            return False
    
    def evaluate_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """评估新闻内容，检查是否符合用户兴趣，并评价重要性、时效性、趣味性
        
        Args:
            content: 包含新闻内容的字典，包括feed_labels表示该RSS源特有的标签
            
        Returns:
            带有评估结果的原始内容字典
        """
        title = content.get("title", "无标题")
        feed_labels = content.get("feed_labels", [])
        logger.info(f"评估内容: {title[:50]}{'...' if len(title) > 50 else ''}, 源标签: {feed_labels}")
        
        # 如果过多连接错误或AI不可用，使用基于规则的方法
        if not self.ai_available or self.connection_errors >= self.ai_error_threshold:
            logger.info(f"使用规则方法评估: AI可用={self.ai_available}, 连接错误={self.connection_errors}")
            return self._evaluate_content_rule_based(content)
        
        # 构建提示词，要求AI评估内容
        prompt = self._build_evaluation_prompt(content)
        
        try:
            # 根据提供者调用AI
            logger.info(f"使用{self.provider}评估内容")
            if self.provider == "ollama":
                logger.info(f"调用Ollama (模型: {self.ollama_model}, 主机: {self.ollama_host})")
                evaluation = self._call_ollama(prompt)
            else:
                logger.info(f"调用OpenAI (模型: {self.openai_model})")
                evaluation = self._call_openai(prompt)
            
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
                
                # 成功情况下重置连接错误计数
                self.connection_errors = 0
            else:
                # 评估失败，增加错误计数并使用规则方法
                self.connection_errors += 1
                logger.warning(f"AI评估失败 ({self.connection_errors}/{self.ai_error_threshold})，回退到规则方法")
                return self._evaluate_content_rule_based(content)
        except Exception as e:
            # 出现异常，增加错误计数并使用规则方法
            self.connection_errors += 1
            logger.error(f"评估内容时出错: {str(e)}，回退到规则方法 ({self.connection_errors}/{self.ai_error_threshold})")
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
        
        # 如果摘要或全文很长，进行截断
        if len(summary) > 1000:
            summary = summary[:1000] + "..."
        if len(full_content) > 3000:
            full_content = full_content[:3000] + "..."
        
        # 将兴趣标签格式化为字符串 - 使用RSS源特定的标签
        interests_str = ", ".join([f'"{tag}"' for tag in feed_labels])
        
        return f"""请分析以下新闻内容，并根据给定标准进行评估：

## 新闻内容
标题：{title}
摘要：{summary}
全文：{full_content}

## 该RSS源关注的标签
{interests_str}

## 评估要求
1. 兴趣匹配：这条新闻是否符合该RSS源关注的标签？如果有，请指明具体匹配的标签；如果不符合任何标签，请说明。
2. 重要性：这条新闻的重要性如何？（极低、低、中、高、极高）
3. 时效性：这条新闻的时效性如何？（极低、低、中、高、极高）
4. 趣味性：这条新闻的趣味性如何？（极低、低、中、高、极高）

请按以下JSON格式返回评估结果：
{{ "interest_match": {{ "is_match": true/false, "matched_tags": ["标签1", "标签2"], "explanation": "解释为什么匹配或不匹配" }}, "importance": {{ "rating": "极低/低/中/高/极高", "explanation": "解释为什么给出这个评级" }}, "timeliness": {{ "rating": "极低/低/中/高/极高", "explanation": "解释为什么给出这个评级" }}, "interest_level": {{ "rating": "极低/低/中/高/极高", "explanation": "解释为什么给出这个评级" }} }}

请只返回JSON格式的评估结果，不要有任何其他文本。
"""
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama API进行评估
        
        Args:
            prompt: 评估提示词
            
        Returns:
            Ollama的响应文本
        """
        try:
            # 增加超时时间，解决超时问题
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60  # 增加超时时间到60秒
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                logger.error(f"Ollama API错误: {response.status_code}, {response.text}")
                return ""
        except Exception as e:
            logger.error(f"调用Ollama时出错: {str(e)}")
            return ""
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API进行评估
        
        Args:
            prompt: 评估提示词
            
        Returns:
            OpenAI的响应文本
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的新闻分析和评估助手。"},
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenAI API错误: {response.status_code}, {response.text}")
                return ""
        except Exception as e:
            logger.error(f"调用OpenAI时出错: {str(e)}")
            return ""
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """解析AI评估结果
        
        Args:
            evaluation_text: AI返回的评估文本
            
        Returns:
            结构化的评估结果字典
        """
        # 默认结果
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
        
        try:
            # 尝试提取JSON字符串
            # 查找第一个 { 和最后一个 } 之间的内容
            start_idx = evaluation_text.find('{')
            end_idx = evaluation_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("从AI响应中找不到JSON")
                return default_result
                
            json_str = evaluation_text[start_idx:end_idx]
            result = json.loads(json_str)
            
            # 验证结果结构
            if not all(k in result for k in ["interest_match", "importance", "timeliness", "interest_level"]):
                logger.warning("AI响应缺少必要的评估字段")
                return default_result
                
            return result
        except json.JSONDecodeError as e:
            logger.error(f"解析AI评估结果时出错: {str(e)}, 原始文本: {evaluation_text}")
            return default_result
    
    def _should_keep_content(self, evaluation: Dict[str, Any]) -> bool:
        """根据评估结果决定是否保留内容
        
        Args:
            evaluation: 评估结果字典
            
        Returns:
            是否保留内容
        """
        # 提取评估信息
        is_interest_match = evaluation["interest_match"]["is_match"]
        importance = evaluation["importance"]["rating"]
        timeliness = evaluation["timeliness"]["rating"]
        interest_level = evaluation["interest_level"]["rating"]
        
        # 记录详细的筛选逻辑
        logger.info(f"过滤决策 - 兴趣匹配: {is_interest_match}, 重要性: {importance}, 时效性: {timeliness}, 趣味性: {interest_level}")
        
        # 筛选逻辑
        # 1. 如果不是用户兴趣且重要性不是极高且不是极有意思，丢弃
        if not is_interest_match and importance != RatingLevel.VERY_HIGH and interest_level != RatingLevel.VERY_HIGH:
            logger.info("丢弃原因：不是用户兴趣且重要性不是极高且不是极有意思")
            return False
            
        # 2. 如果是用户兴趣但重要性低或极低且没有意思，丢弃
        if is_interest_match and (importance in [RatingLevel.LOW, RatingLevel.VERY_LOW]) and (interest_level in [RatingLevel.LOW, RatingLevel.VERY_LOW]):
            logger.info("丢弃原因：是用户兴趣但重要性低或极低且没有意思")
            return False
            
        # 3. 如果时效性极低，丢弃
        if timeliness == RatingLevel.VERY_LOW:
            logger.info("丢弃原因：时效性极低")
            return False
            
        # 4. 如果重要性和趣味性都是极低，丢弃
        if importance == RatingLevel.VERY_LOW and interest_level == RatingLevel.VERY_LOW:
            logger.info("丢弃原因：重要性和趣味性都是极低")
            return False
        
        # 通过所有筛选条件，保留内容
        logger.info("保留原因：通过所有筛选条件")
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
        return kept_contents, discarded_contents
