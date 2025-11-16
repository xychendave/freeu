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
            'anthropic_api_key': '',
            'log_level': 'INFO',
            'max_files': 1000,
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
    def anthropic_api_key(self) -> Optional[str]:
        """获取Claude API Key"""
        api_key = self._config.get('anthropic_api_key', '')
        if not api_key:
            # 尝试从环境变量获取
            api_key = os.getenv('ANTHROPIC_API_KEY', '')
        return api_key if api_key else None
    
    @anthropic_api_key.setter
    def anthropic_api_key(self, value: str) -> None:
        """设置Claude API Key"""
        self._config['anthropic_api_key'] = value
        self.save_config()
    
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