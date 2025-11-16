import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.freeu'
        self.config_file = self.config_dir / 'config.json'
        self._config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                    logger.info(f"配置文件加载成功: {self.config_file}")
            else:
                logger.info("配置文件不存在，使用默认配置")
                self._config = self.get_default_config()
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            self._config = self.get_default_config()
    
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置文件保存成功: {self.config_file}")
        except Exception as e:
            logger.error(f"配置文件保存失败: {e}")
            raise
    
    def get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            'ai_provider': 'claude',  # 默认AI提供商
            'ai_providers': {
                'claude': {
                    'api_key': '',
                    'model': 'claude-3-5-sonnet-20241022',
                    'enabled': True
                },
                'openai': {
                    'api_key': '',
                    'model': 'gpt-4-turbo-preview',
                    'enabled': False
                },
                'kimi': {
                    'api_key': '',
                    'model': 'moonshot-v1-8k',
                    'enabled': False
                },
                'glm': {
                    'api_key': '',
                    'model': 'glm-4',
                    'enabled': False
                },
                'openrouter': {
                    'api_key': '',
                    'model': 'anthropic/claude-3.5-sonnet',
                    'enabled': False
                }
            },
            'log_level': 'INFO',
            'max_files': 10000,  # 增加文件数量限制到10000
            'scan_all_files': False,  # 是否扫描所有文件（无限制）
            'allowed_operations': ['move'],
            'excluded_paths': [
                '/System',
                '/Library', 
                '/usr',
                '/bin',
                '/etc',
                '~/.ssh',
                '~/.config',
                '/Applications'
            ]
        }
    
    @property
    def ai_provider(self) -> str:
        """获取当前AI提供商"""
        return self._config.get('ai_provider', 'claude')
    
    @ai_provider.setter
    def ai_provider(self, value: str) -> None:
        """设置当前AI提供商"""
        self._config['ai_provider'] = value
        self.save_config()
    
    def get_ai_provider_config(self, provider: str = None) -> dict:
        """获取AI提供商配置"""
        provider = provider or self.ai_provider
        providers = self._config.get('ai_providers', {})
        return providers.get(provider, {})
    
    def set_ai_provider_config(self, provider: str, api_key: str, model: str = None, enabled: bool = True) -> None:
        """设置AI提供商配置"""
        if 'ai_providers' not in self._config:
            self._config['ai_providers'] = {}
        
        self._config['ai_providers'][provider] = {
            'api_key': api_key,
            'model': model or self._get_default_model_for_provider(provider),
            'enabled': enabled
        }
        self.save_config()
    
    def _get_default_model_for_provider(self, provider: str) -> str:
        """获取提供商的默认模型"""
        defaults = {
            'claude': 'claude-3-5-sonnet-20241022',
            'openai': 'gpt-4-turbo-preview',
            'kimi': 'moonshot-v1-8k',
            'glm': 'glm-4',
            'openrouter': 'anthropic/claude-3.5-sonnet'
        }
        return defaults.get(provider, '')
    
    def get_active_ai_provider(self) -> Optional[str]:
        """获取当前启用的AI提供商"""
        providers = self._config.get('ai_providers', {})
        current_provider = self.ai_provider
        
        # 检查当前提供商是否启用且有API Key
        if current_provider in providers:
            config = providers[current_provider]
            if config.get('enabled', False) and config.get('api_key'):
                return current_provider
        
        # 查找第一个启用的提供商
        for provider, config in providers.items():
            if config.get('enabled', False) and config.get('api_key'):
                return provider
        
        return None
    
    def get_active_ai_config(self) -> Optional[dict]:
        """获取当前启用的AI配置"""
        provider = self.get_active_ai_provider()
        if provider:
            return self.get_ai_provider_config(provider)
        return None
    
    # 向后兼容的旧API
    @property
    def anthropic_api_key(self) -> Optional[str]:
        """获取Claude API Key（向后兼容）"""
        claude_config = self.get_ai_provider_config('claude')
        return claude_config.get('api_key') if claude_config else None
    
    @anthropic_api_key.setter
    def anthropic_api_key(self, value: str) -> None:
        """设置Claude API Key（向后兼容）"""
        self.set_ai_provider_config('claude', value)
    
    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self._config.get('log_level', 'INFO')
    
    @property
    def max_files(self) -> int:
        """获取最大文件数量限制"""
        return self._config.get('max_files', 1000)
    
    @property
    def allowed_operations(self) -> list:
        """获取允许的操作类型"""
        return self._config.get('allowed_operations', ['move'])
    
    @property
    def excluded_paths(self) -> list:
        """获取排除路径列表"""
        return self._config.get('excluded_paths', [])

# 全局配置实例
config = Config()