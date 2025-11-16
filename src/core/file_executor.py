import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict
from src.core.ai_engine import FileAction
from src.core.scanner import FileInfo
from src.utils.config import config

logger = logging.getLogger(__name__)

class FileExecutionResult(BaseModel):
    """文件操作执行结果"""
    success: bool = Field(..., description="是否成功")
    source: str = Field(..., description="源文件路径")
    destination: str = Field(..., description="目标文件路径")
    action_type: str = Field(..., description="操作类型")
    error: Optional[str] = Field(None, description="错误信息")
    warning: Optional[str] = Field(None, description="警告信息")

class FileExecutor:
    """文件操作执行器"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path.resolve()
        logger.info(f"初始化文件执行器，基础路径: {self.base_path}")
    
    def execute_actions(self, actions: List[FileAction], available_files: List[FileInfo]) -> List[Dict]:
        """执行文件操作"""
        logger.info(f"开始执行文件操作，操作数量: {len(actions)}")
        
        results = []
        success_count = 0
        
        for i, action in enumerate(actions):
            logger.info(f"执行操作 {i+1}/{len(actions)}: {action.source} → {action.destination}")
            
            try:
                result = self._execute_single_action(action, available_files)
                results.append(result)
                
                if result["success"]:
                    success_count += 1
                    logger.info(f"操作成功: {action.source} → {action.destination}")
                else:
                    logger.warning(f"操作失败: {action.source} - {result['error']}")
                
                # 记录进度
                log_progress(i + 1, len(actions), f"文件操作进度")
                
            except Exception as e:
                logger.error(f"执行操作异常: {action.source} - {e}")
                results.append({
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": f"执行异常: {str(e)}"
                })
        
        logger.info(f"文件操作执行完成，成功: {success_count}/{len(actions)}")
        return results
    
    def _execute_single_action(self, action: FileAction, available_files: List[FileInfo]) -> Dict:
        """执行单个文件操作"""
        try:
            # 验证操作类型
            if action.action_type != "move":
                return {
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": f"不支持的操作类型: {action.action_type}"
                }
            
            # 构建完整路径
            source_path = self.base_path / action.source
            destination_path = self.base_path / action.destination
            
            # 验证源文件存在
            if not source_path.exists():
                return {
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": "源文件不存在"
                }
            
            if not source_path.is_file():
                return {
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": "源路径不是文件"
                }
            
            # 检查目标路径安全性
            if not self._is_path_safe(destination_path):
                return {
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": "目标路径不安全"
                }
            
            # 创建目标目录
            destination_dir = destination_path.parent
            try:
                destination_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": f"创建目标目录失败: {str(e)}"
                }
            
            # 检查目标文件是否已存在
            if destination_path.exists():
                # 生成新的文件名
                destination_path = self._generate_unique_filename(destination_path)
                warning = f"目标文件已存在，重命名为: {destination_path.name}"
                logger.warning(warning)
            
            # 执行移动操作
            try:
                shutil.move(str(source_path), str(destination_path))
                
                return {
                    "success": True,
                    "source": action.source,
                    "destination": str(destination_path.relative_to(self.base_path)),
                    "action_type": action.action_type,
                    "error": None,
                    "warning": warning if destination_path.name != Path(action.destination).name else None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "source": action.source,
                    "destination": action.destination,
                    "action_type": action.action_type,
                    "error": f"移动文件失败: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"执行操作异常: {action.source} - {e}")
            return {
                "success": False,
                "source": action.source,
                "destination": action.destination,
                "action_type": action.action_type,
                "error": f"操作异常: {str(e)}"
            }
    
    def _is_path_safe(self, path: Path) -> bool:
        """检查路径是否安全"""
        try:
            # 解析路径
            resolved_path = path.resolve()
            
            # 检查是否在基础路径下
            if not str(resolved_path).startswith(str(self.base_path)):
                logger.warning(f"路径不在基础目录下: {path}")
                return False
            
            # 检查是否在排除路径列表中
            for excluded_path in config.excluded_paths:
                excluded = Path(excluded_path).expanduser().resolve()
                if str(resolved_path).startswith(str(excluded)):
                    logger.warning(f"路径在排除列表中: {path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"路径安全检查失败: {path} - {e}")
            return False
    
    def _generate_unique_filename(self, path: Path) -> Path:
        """生成唯一的文件名"""
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            
            if not new_path.exists():
                return new_path
            
            counter += 1
            
            # 防止无限循环
            if counter > 999:
                logger.error(f"无法生成唯一文件名: {path}")
                raise ValueError(f"无法生成唯一文件名: {path}")
    
    def undo_last_operation(self) -> bool:
        """撤销最后一次操作（TODO: 未来实现）"""
        logger.warning("撤销功能暂未实现")
        return False
    
    def get_operation_history(self) -> List[Dict]:
        """获取操作历史（TODO: 未来实现）"""
        logger.warning("操作历史功能暂未实现")
        return []