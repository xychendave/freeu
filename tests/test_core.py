#!/usr/bin/env python3
"""
FreeU测试脚本
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from src.core.scanner import DirectoryScanner, FileInfo
from src.core.ai_engine import ClaudeAI, FileAction
from src.core.file_executor import FileExecutor
from src.utils.config import config

class TestDirectoryScanner(unittest.TestCase):
    """测试目录扫描器"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # 创建测试文件
        (self.test_dir / "test1.jpg").write_text("test image 1")
        (self.test_dir / "test2.pdf").write_text("test document")
        (self.test_dir / "test3.txt").write_text("test text file")
        
        # 创建子目录
        sub_dir = self.test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "test4.png").write_text("test image in subdir")
        
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_scan_directory(self):
        """测试目录扫描"""
        scanner = DirectoryScanner(self.test_dir)
        files = scanner.scan_directory(recursive=False)
        
        self.assertGreater(len(files), 0)
        
        # 检查文件信息
        for file_info in files:
            self.assertIsInstance(file_info, FileInfo)
            self.assertTrue(file_info.name)
            self.assertTrue(file_info.path)
            self.assertGreater(file_info.size, 0)
    
    def test_scan_recursive(self):
        """测试递归扫描"""
        scanner = DirectoryScanner(self.test_dir)
        files_recursive = scanner.scan_directory(recursive=True)
        files_non_recursive = scanner.scan_directory(recursive=False)
        
        # 递归扫描应该找到更多文件
        self.assertGreater(len(files_recursive), len(files_non_recursive))
    
    def test_file_summary(self):
        """测试文件摘要"""
        scanner = DirectoryScanner(self.test_dir)
        scanner.scan_directory(recursive=True)
        summary = scanner.get_files_summary()
        
        self.assertIn('total_files', summary)
        self.assertIn('total_size', summary)
        self.assertIn('extensions', summary)
        self.assertGreater(summary['total_files'], 0)

class TestAIEngine(unittest.TestCase):
    """测试AI引擎"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_files = [
            FileInfo(
                name="photo.jpg",
                path="photo.jpg",
                extension=".jpg",
                size=1024,
                modified_time="2024-01-01 10:00:00",
                is_directory=False
            ),
            FileInfo(
                name="document.pdf",
                path="document.pdf", 
                extension=".pdf",
                size=2048,
                modified_time="2024-01-01 11:00:00",
                is_directory=False
            ),
            FileInfo(
                name="screenshot.png",
                path="screenshot.png",
                extension=".png", 
                size=3072,
                modified_time="2024-01-01 12:00:00",
                is_directory=False
            )
        ]
    
    def test_build_system_prompt(self):
        """测试系统提示词构建"""
        try:
            ai = ClaudeAI()
            prompt = ai._build_system_prompt()
            self.assertIn("FreeU", prompt)
            self.assertIn("JSON", prompt)
        except ValueError:
            # 如果没有配置API Key，应该抛出ValueError
            pass
    
    def test_build_user_prompt(self):
        """测试用户提示词构建"""
        try:
            ai = ClaudeAI()
            instruction = "把所有图片放到Pictures文件夹"
            prompt = ai._build_user_prompt(instruction, self.test_files)
            
            self.assertIn(instruction, prompt)
            self.assertIn("photo.jpg", prompt)
            self.assertIn("screenshot.png", prompt)
        except ValueError:
            # 如果没有配置API Key，应该抛出ValueError
            pass

class TestFileExecutor(unittest.TestCase):
    """测试文件执行器"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # 创建测试文件
        self.source_file = self.test_dir / "test_file.txt"
        self.source_file.write_text("test content")
        
        # 创建执行器
        self.executor = FileExecutor(self.test_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_is_path_safe(self):
        """测试路径安全性检查"""
        # 安全路径
        safe_path = self.test_dir / "safe_file.txt"
        self.assertTrue(self.executor._is_path_safe(safe_path))
        
        # 不安全路径（包含..）
        unsafe_path = self.test_dir / ".." / "unsafe.txt"
        self.assertFalse(self.executor._is_path_safe(unsafe_path))
    
    def test_generate_unique_filename(self):
        """测试生成唯一文件名"""
        # 创建已存在的文件
        existing_file = self.test_dir / "existing.txt"
        existing_file.write_text("content")
        
        # 生成唯一文件名
        new_path = self.executor._generate_unique_filename(existing_file)
        self.assertNotEqual(new_path, existing_file)
        self.assertTrue(new_path.name.startswith("existing_"))
    
    def test_execute_single_action(self):
        """测试执行单个操作"""
        # 创建目标目录
        target_dir = self.test_dir / "target"
        target_dir.mkdir()
        
        # 创建操作
        action = FileAction(
            action_type="move",
            source="test_file.txt",
            destination="target/test_file.txt",
            reason="测试移动"
        )
        
        # 创建文件信息
        file_info = FileInfo(
            name="test_file.txt",
            path="test_file.txt",
            extension=".txt",
            size=12,
            modified_time="2024-01-01 10:00:00",
            is_directory=False
        )
        
        # 执行操作
        result = self.executor._execute_single_action(action, [file_info])
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertFalse(self.source_file.exists())
        self.assertTrue((self.test_dir / "target" / "test_file.txt").exists())

def run_tests():
    """运行所有测试"""
    print("🧪 运行FreeU测试...")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDirectoryScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestAIEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestFileExecutor))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)