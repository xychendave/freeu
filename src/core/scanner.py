import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from src.utils.config import config

logger = logging.getLogger(__name__)

class FileInfo(BaseModel):
    """文件信息模型"""
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="相对路径")
    extension: str = Field(..., description="文件扩展名")
    size: int = Field(..., description="文件大小（字节）")
    modified_time: datetime = Field(..., description="修改时间")
    is_directory: bool = Field(False, description="是否为目录")

class DirectoryScanner:
    """目录扫描器"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path.resolve()
        self.files: List[FileInfo] = []
        logger.info(f"初始化目录扫描器: {self.base_path}")
    
    def is_path_safe(self, path: Path) -> bool:
        """检查路径是否安全（不在排除列表中）"""
        try:
            # 解析路径
            resolved_path = path.resolve()
            
            # 检查是否在用户指定的基础路径下
            if not str(resolved_path).startswith(str(self.base_path)):
                logger.warning(f"路径不在基础目录下: {path}")
                return False
            
            # 检查是否在排除路径列表中
            for excluded_path in config.excluded_paths:
                excluded = Path(excluded_path).expanduser().resolve()
                if str(resolved_path).startswith(str(excluded)):
                    logger.warning(f"路径在排除列表中: {path}")
                    return False
            
            # 检查是否是隐藏文件（以.开头）
            if path.name.startswith('.'):
                logger.info(f"跳过隐藏文件: {path.name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"路径安全检查失败: {path} - {e}")
            return False
    
    def scan_directory(self, recursive: bool = False) -> List[FileInfo]:
        """扫描目录"""
        logger.info(f"开始扫描目录: {self.base_path} (recursive={recursive})")
        
        if not self.base_path.exists():
            raise FileNotFoundError(f"目录不存在: {self.base_path}")
        
        if not self.base_path.is_dir():
            raise ValueError(f"路径不是目录: {self.base_path}")
        
        self.files = []
        file_count = 0
        
        try:
            if recursive:
                # 递归扫描
                for root, dirs, files in os.walk(self.base_path):
                    root_path = Path(root)
                    
                    # 检查目录是否安全
                    if not self.is_path_safe(root_path):
                        dirs[:] = []  # 跳过此目录
                        continue
                    
                    # 处理文件
                    for filename in files:
                        file_path = root_path / filename
                        
                        if self.is_path_safe(file_path):
                            try:
                                file_info = self._create_file_info(file_path)
                                self.files.append(file_info)
                                file_count += 1
                                
                                # 检查文件数量限制
                                if file_count >= config.max_files:
                                    logger.warning(f"达到文件数量限制: {config.max_files}")
                                    break
                                    
                            except Exception as e:
                                logger.error(f"处理文件失败: {file_path} - {e}")
                        
                        if file_count >= config.max_files:
                            break
                    
                    if file_count >= config.max_files:
                        break
            else:
                # 只扫描当前目录
                for item in self.base_path.iterdir():
                    if self.is_path_safe(item) and item.is_file():
                        try:
                            file_info = self._create_file_info(item)
                            self.files.append(file_info)
                            file_count += 1
                            
                            # 检查文件数量限制
                            if file_count >= config.max_files:
                                logger.warning(f"达到文件数量限制: {config.max_files}")
                                break
                                
                        except Exception as e:
                            logger.error(f"处理文件失败: {item} - {e}")
        
        except Exception as e:
            logger.error(f"扫描目录失败: {self.base_path} - {e}")
            raise
        
        logger.info(f"扫描完成，找到 {len(self.files)} 个文件")
        return self.files
    
    def _create_file_info(self, file_path: Path) -> FileInfo:
        """创建文件信息对象"""
        stat = file_path.stat()
        
        # 计算相对路径
        try:
            relative_path = file_path.relative_to(self.base_path)
        except ValueError:
            relative_path = file_path.name
        
        return FileInfo(
            name=file_path.name,
            path=str(relative_path),
            extension=file_path.suffix.lower(),
            size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            is_directory=file_path.is_dir()
        )
    
    def get_files_summary(self) -> Dict:
        """获取文件统计摘要"""
        if not self.files:
            return {"total_files": 0, "total_size": 0, "extensions": {}}
        
        total_size = sum(file.size for file in self.files)
        extensions = {}
        
        for file in self.files:
            ext = file.extension or "无扩展名"
            extensions[ext] = extensions.get(ext, 0) + 1
        
        return {
            "total_files": len(self.files),
            "total_size": total_size,
            "extensions": extensions,
            "scan_path": str(self.base_path)
        }
    
    def filter_files(self, extensions: Optional[List[str]] = None, 
                    min_size: Optional[int] = None,
                    max_size: Optional[int] = None) -> List[FileInfo]:
        """过滤文件"""
        filtered_files = self.files.copy()
        
        if extensions:
            filtered_files = [f for f in filtered_files if f.extension.lower() in [ext.lower() for ext in extensions]]
        
        if min_size is not None:
            filtered_files = [f for f in filtered_files if f.size >= min_size]
        
        if max_size is not None:
            filtered_files = [f for f in filtered_files if f.size <= max_size]
        
        logger.info(f"文件过滤完成: {len(self.files)} -> {len(filtered_files)}")
        return filtered_files