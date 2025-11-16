"""
AI提供商统一接口适配器
支持多种AI服务：Claude、OpenAI、Kimi、GLM、OpenRouter等
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from enum import Enum

from src.core.scanner import FileInfo

logger = logging.getLogger(__name__)

class AIProvider(Enum):
    """AI提供商枚举"""
    CLAUDE = "claude"
    OPENAI = "openai"
    KIMI = "kimi"
    GLM = "glm"
    OPENROUTER = "openrouter"

class BaseAIAdapter(ABC):
    """AI适配器基类"""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model or self.get_default_model()
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def get_default_model(self) -> str:
        """获取默认模型"""
        pass
    
    @abstractmethod
    def _initialize_client(self):
        """初始化客户端"""
        pass
    
    @abstractmethod
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> Dict[str, Any]:
        """生成文件整理方案"""
        pass
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词（通用）"""
        return """你是 FreeU 文件整理助手，负责根据用户指令生成文件整理方案。

【角色定义】
- 只处理本地文件整理任务
- 输出必须是严格的 JSON 格式
- 只允许执行移动操作（move），不支持删除操作
- 目标路径必须在用户指定的目录下

【输出格式】
{
  "actions": [
    {
      "action_type": "move",
      "source": "相对路径",
      "destination": "目标相对路径", 
      "reason": "简短说明"
    }
  ]
}

【操作规则】
1. 只移动文件，不移动目录
2. 目标路径使用相对路径，相对于用户指定的基础目录
3. 自动创建必要的子目录
4. 不要移动隐藏文件（以.开头）
5. 不要移动系统文件

【分类建议】
- 图片文件：jpg, jpeg, png, gif, bmp, svg, webp → Pictures/
- 文档文件：pdf, doc, docx, txt, rtf → Documents/
- 视频文件：mp4, avi, mov, mkv, wmv → Videos/
- 音频文件：mp3, wav, flac, aac, m4a → Music/
- 压缩文件：zip, rar, 7z, tar, gz → Archives/
- 表格文件：xls, xlsx, csv → Spreadsheets/
- 演示文件：ppt, pptx → Presentations/

【示例】
用户指令："把所有图片放到 Pictures 文件夹"
文件列表：["photo.jpg", "document.pdf", "screenshot.png"]
输出：
{
  "actions": [
    {"action_type": "move", "source": "photo.jpg", "destination": "Pictures/photo.jpg", "reason": "图片文件"},
    {"action_type": "move", "source": "screenshot.png", "destination": "Pictures/screenshot.png", "reason": "图片文件"}
  ]
}"""

    def _build_user_prompt(self, user_instruction: str, files: List[FileInfo]) -> str:
        """构建用户提示词"""
        # 构建文件列表字符串
        file_list = []
        for file in files:
            file_info = f"- {file.name} (大小: {self._format_file_size(file.size)}, 修改时间: {file.modified_time.strftime('%Y-%m-%d %H:%M:%S')})"
            file_list.append(file_info)
        
        files_str = "\n".join(file_list)
        
        return f"""用户指令：{user_instruction}

当前目录下的文件：
{files_str}

请根据用户指令生成文件整理方案。只返回 JSON 格式，不要包含其他解释。"""
    
    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

class ClaudeAdapter(BaseAIAdapter):
    """Claude AI适配器"""
    
    def get_default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"
    
    def _initialize_client(self):
        """初始化Claude客户端"""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ValueError("请安装anthropic库: pip install anthropic")
    
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> Dict[str, Any]:
        """生成Claude整理方案"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_instruction, files)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            content = response.content[0].text
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            raise

class OpenAIAdapter(BaseAIAdapter):
    """OpenAI适配器"""
    
    def get_default_model(self) -> str:
        return "gpt-4-turbo-preview"
    
    def _initialize_client(self):
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ValueError("请安装openai库: pip install openai")
    
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> Dict[str, Any]:
        """生成OpenAI整理方案"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_instruction, files)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise

class KimiAdapter(BaseAIAdapter):
    """Kimi (Moonshot) 适配器"""
    
    def get_default_model(self) -> str:
        return "moonshot-v1-8k"
    
    def _initialize_client(self):
        """初始化Kimi客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.moonshot.cn/v1"
            )
        except ImportError:
            raise ValueError("请安装openai库: pip install openai")
    
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> Dict[str, Any]:
        """生成Kimi整理方案"""
        # Kimi使用与OpenAI兼容的API格式
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_instruction, files)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Kimi API调用失败: {e}")
            raise

class GLMAdapter(BaseAIAdapter):
    """GLM (智谱) 适配器"""
    
    def get_default_model(self) -> str:
        return "glm-4"
    
    def _initialize_client(self):
        """初始化GLM客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4"
            )
        except ImportError:
            raise ValueError("请安装openai库: pip install openai")
    
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> Dict[str, Any]:
        """生成GLM整理方案"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_instruction, files)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"GLM API调用失败: {e}")
            raise

class OpenRouterAdapter(BaseAIAdapter):
    """OpenRouter适配器"""
    
    def get_default_model(self) -> str:
        return "anthropic/claude-3.5-sonnet"
    
    def _initialize_client(self):
        """初始化OpenRouter客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        except ImportError:
            raise ValueError("请安装openai库: pip install openai")
    
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> Dict[str, Any]:
        """生成OpenRouter整理方案"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_instruction, files)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"OpenRouter API调用失败: {e}")
            raise

class AIAdapterFactory:
    """AI适配器工厂"""
    
    _adapters = {
        AIProvider.CLAUDE: ClaudeAdapter,
        AIProvider.OPENAI: OpenAIAdapter,
        AIProvider.KIMI: KimiAdapter,
        AIProvider.GLM: GLMAdapter,
        AIProvider.OPENROUTER: OpenRouterAdapter,
    }
    
    @classmethod
    def create_adapter(cls, provider: AIProvider, api_key: str, model: str = None) -> BaseAIAdapter:
        """创建AI适配器"""
        adapter_class = cls._adapters.get(provider)
        if not adapter_class:
            raise ValueError(f"不支持的AI提供商: {provider}")
        
        return adapter_class(api_key, model)
    
    @classmethod
    def get_available_providers(cls) -> List[Dict[str, str]]:
        """获取可用的AI提供商列表"""
        return [
            {"value": AIProvider.CLAUDE.value, "label": "Claude (Anthropic)", "description": "强大的AI助手，适合复杂任务"},
            {"value": AIProvider.OPENAI.value, "label": "OpenAI GPT", "description": "知名的GPT模型系列"},
            {"value": AIProvider.KIMI.value, "label": "Kimi (Moonshot)", "description": "国产大模型，中文理解好"},
            {"value": AIProvider.GLM.value, "label": "GLM (智谱)", "description": "清华系大模型，技术领先"},
            {"value": AIProvider.OPENROUTER.value, "label": "OpenRouter", "description": "聚合多个AI模型，灵活选择"},
        ]
    
    @classmethod
    def get_provider_config_examples(cls) -> Dict[str, Dict[str, str]]:
        """获取提供商配置示例"""
        return {
            "claude": {
                "api_key_example": "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "model_example": "claude-3-5-sonnet-20241022",
                "doc_url": "https://console.anthropic.com/"
            },
            "openai": {
                "api_key_example": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "model_example": "gpt-4-turbo-preview",
                "doc_url": "https://platform.openai.com/"
            },
            "kimi": {
                "api_key_example": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "model_example": "moonshot-v1-8k",
                "doc_url": "https://platform.moonshot.cn/"
            },
            "glm": {
                "api_key_example": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx",
                "model_example": "glm-4",
                "doc_url": "https://open.bigmodel.cn/"
            },
            "openrouter": {
                "api_key_example": "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "model_example": "anthropic/claude-3.5-sonnet",
                "doc_url": "https://openrouter.ai/"
            }
        }