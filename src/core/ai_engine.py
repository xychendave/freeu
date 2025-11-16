import json
import logging
from typing import List, Dict, Optional
try:
    from pydantic import BaseModel, Field
except ImportError:
    from pydantic.v1 import BaseModel, Field
from src.utils.config import config
from src.core.scanner import FileInfo
from src.core.ai_adapter import (
    AIProvider, AIAdapterFactory
)

logger = logging.getLogger(__name__)

class FileAction(BaseModel):
    """文件操作模型"""
    action_type: str = Field(..., description="操作类型 (move)")
    source: str = Field(..., description="源文件相对路径")
    destination: str = Field(..., description="目标文件相对路径")
    reason: str = Field(..., description="操作原因说明")

class AIResponse(BaseModel):
    """AI响应模型"""
    actions: List[FileAction] = Field(default_factory=list, description="文件操作列表")
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "actions": [
                {
                    "action_type": action.action_type,
                    "source": action.source,
                    "destination": action.destination,
                    "reason": action.reason
                }
                for action in self.actions
            ]
        }

class MultiAIEngine:
    """多AI提供商统一引擎"""
    
    def __init__(self, provider: str = None):
        self.provider = provider or config.ai_provider
        self.adapter = None
        self._initialize_adapter()
    
    def _initialize_adapter(self) -> None:
        """初始化AI适配器"""
        # 获取当前启用的AI配置
        ai_config = config.get_active_ai_config()
        if not ai_config:
            available_providers = self.get_available_providers()
            if available_providers:
                raise ValueError(f"请先配置AI提供商的API Key。可用的提供商：{', '.join(available_providers)}")
            else:
                raise ValueError("没有可用的AI提供商，请在设置中配置API Key")
        
        api_key = ai_config.get('api_key')
        model = ai_config.get('model')
        
        try:
            # 创建适配器
            ai_provider = AIProvider(self.provider)
            self.adapter = AIAdapterFactory.create_adapter(ai_provider, api_key, model)
            logger.info(f"AI适配器初始化成功: {self.provider}")
            
        except Exception as e:
            logger.error(f"AI适配器初始化失败: {e}")
            raise
    
    def get_available_providers(self) -> List[str]:
        """获取可用的AI提供商列表"""
        available = []
        providers = config._config.get('ai_providers', {})
        
        for provider, config_data in providers.items():
            if config_data.get('enabled', False) and config_data.get('api_key'):
                available.append(provider)
        
        return available
    
    def switch_provider(self, provider: str) -> bool:
        """切换AI提供商"""
        try:
            # 检查提供商是否可用
            provider_config = config.get_ai_provider_config(provider)
            if not provider_config.get('api_key'):
                logger.error(f"提供商 {provider} 未配置API Key")
                return False
            
            # 切换提供商
            self.provider = provider
            config.ai_provider = provider
            self._initialize_adapter()
            
            logger.info(f"成功切换到AI提供商: {provider}")
            return True
            
        except Exception as e:
            logger.error(f"切换AI提供商失败: {e}")
            return False
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
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
    
    def generate_organization_plan(self, user_instruction: str, files: List[FileInfo]) -> AIResponse:
        """生成文件整理方案"""
        logger.info(f"开始生成整理方案，用户指令: {user_instruction}, 文件数量: {len(files)}, 提供商: {self.provider}")
        
        if not self.adapter:
            raise ValueError("AI适配器未初始化")
        
        if not files:
            logger.warning("文件列表为空")
            return AIResponse(actions=[])
        
        try:
            # 使用适配器生成方案
            result_data = self.adapter.generate_organization_plan(user_instruction, files)
            
            # 解析操作列表
            actions = []
            for action_data in result_data.get("actions", []):
                try:
                    action = FileAction(**action_data)
                    # 验证操作类型
                    if action.action_type not in config.allowed_operations:
                        logger.warning(f"跳过不允许的操作类型: {action.action_type}")
                        continue
                    actions.append(action)
                except Exception as e:
                    logger.error(f"解析操作失败: {action_data} - {e}")
                    continue
            
            result = AIResponse(actions=actions)
            logger.info(f"生成整理方案完成，操作数量: {len(actions)}")
            return result
            
        except Exception as e:
            logger.error(f"生成整理方案失败: {e}")
            raise
    
    def validate_actions(self, actions: List[FileAction], available_files: List[FileInfo]) -> List[Dict]:
        """验证操作的有效性"""
        logger.info(f"开始验证操作，操作数量: {len(actions)}")
        
        available_file_names = {file.name: file for file in available_files}
        validation_results = []
        
        for i, action in enumerate(actions):
            result = {
                "index": i,
                "action": action,
                "valid": True,
                "message": "",
                "warnings": []
            }
            
            # 检查源文件是否存在
            source_filename = Path(action.source).name
            if source_filename not in available_file_names:
                result["valid"] = False
                result["message"] = f"源文件不存在: {action.source}"
                logger.warning(f"操作验证失败 - 源文件不存在: {action.source}")
            
            # 检查路径安全性
            if ".." in action.destination:
                result["valid"] = False
                result["message"] = f"目标路径不安全: {action.destination}"
                logger.warning(f"操作验证失败 - 路径不安全: {action.destination}")
            
            # 检查操作类型
            if action.action_type not in config.allowed_operations:
                result["valid"] = False
                result["message"] = f"不允许的操作类型: {action.action_type}"
                logger.warning(f"操作验证失败 - 不允许的操作: {action.action_type}")
            
            if result["valid"] and not result["message"]:
                result["message"] = "操作有效"
            
            validation_results.append(result)
        
        valid_count = sum(1 for r in validation_results if r["valid"])
        logger.info(f"操作验证完成，有效操作: {valid_count}/{len(actions)}")
        
        return validation_results