import logging
import json
import requests
import time
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

# 配置日志
logger = logging.getLogger("ai_utils")

class AiProvider(str, Enum):
    """AI提供商类型"""
    OLLAMA = "ollama"
    OPENAI = "openai"

class AiService:
    """AI服务抽象类，提供统一的接口调用AI模型"""
    
    def __init__(self, config=None):
        """初始化AI服务
        
        Args:
            config: 包含AI设置的配置字典
        """
        self.config = config or {}
        # 从配置加载AI设置
        self.ai_settings = self.config.get("global_settings", {}).get("ai_settings", {})
        self.provider = self.ai_settings.get("provider", "ollama")
        self.ai_available = True  # 用于跟踪AI服务可用性
        self.connection_errors = 0  # 连接错误计数
        self.ai_error_threshold = 3  # 超过此阈值时切换到本地处理模式
        
        if self.provider == AiProvider.OLLAMA:
            self.ollama_host = self.ai_settings.get("ollama_host", "http://localhost:11434")
            self.ollama_model = self.ai_settings.get("ollama_model", "llama2")
            
            # 检查Ollama是否可用
            if not self._check_ollama_availability():
                self.ai_available = False
                logger.warning(f"Ollama在{self.ollama_host}不可用，将使用本地处理")
        else:  # OpenAI
            self.openai_key = self.ai_settings.get("openai_key", "")
            self.openai_model = self.ai_settings.get("openai_model", "gpt-3.5-turbo")
            
            # 检查OpenAI是否可用
            if not self.openai_key:
                self.ai_available = False
                logger.warning("未提供OpenAI API密钥，将使用本地处理")
    
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
    
    def call_ai(self, prompt: str, max_retries=1) -> str:
        """调用AI模型获取响应
        
        Args:
            prompt: 提示词
            max_retries: 最大重试次数
            
        Returns:
            AI响应文本，如果失败则返回空字符串
        """
        if not self.ai_available:
            logger.warning("AI服务不可用")
            return ""
        
        for retry in range(max_retries + 1):
            try:
                if self.provider == AiProvider.OLLAMA:
                    return self._call_ollama(prompt)
                else:
                    return self._call_openai(prompt)
            except Exception as e:
                logger.error(f"调用AI失败 (尝试 {retry+1}/{max_retries+1}): {str(e)}")
                self.connection_errors += 1
                if self.connection_errors >= self.ai_error_threshold:
                    self.ai_available = False
                    logger.warning(f"连接错误过多，AI服务标记为不可用")
                    return ""
                if retry < max_retries:
                    time.sleep(2)  # 重试前等待2秒
        
        return ""
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama API获取响应
        
        Args:
            prompt: 提示词
            
        Returns:
            Ollama的响应文本
        """
        try:
            logger.info(f"调用Ollama (模型: {self.ollama_model})")
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60  # 60秒超时
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("response", "")
                logger.info(f"Ollama响应成功，长度: {len(result)} 字符")
                return result
            else:
                logger.error(f"Ollama API错误: {response.status_code}, {response.text}")
                return ""
        except Exception as e:
            logger.error(f"调用Ollama时出错: {str(e)}")
            raise  # 重新抛出异常，由上层处理重试
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API获取响应
        
        Args:
            prompt: 提示词
            
        Returns:
            OpenAI的响应文本
        """
        try:
            logger.info(f"调用OpenAI (模型: {self.openai_model})")
            
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的新闻分析和处理助手。"},
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
                result = response_data["choices"][0]["message"]["content"]
                logger.info(f"OpenAI响应成功，长度: {len(result)} 字符")
                return result
            else:
                logger.error(f"OpenAI API错误: {response.status_code}, {response.text}")
                return ""
        except Exception as e:
            logger.error(f"调用OpenAI时出错: {str(e)}")
            raise  # 重新抛出异常，由上层处理重试
    
    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """从AI响应中解析JSON
        
        Args:
            response_text: AI响应文本
            
        Returns:
            解析后的JSON字典，如果解析失败则返回空字典
        """
        if not response_text:
            return {}
            
        try:
            # 尝试提取JSON字符串
            # 查找第一个 { 和最后一个 } 之间的内容
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("从AI响应中找不到JSON")
                return {}
                
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON时出错: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"处理AI响应时出错: {str(e)}")
            return {}
