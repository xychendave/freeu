#!/usr/bin/env python3
"""
FreeU简单测试 - 验证基础功能
"""

import sys
import os
from pathlib import Path

# 将src目录添加到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

def test_basic_imports():
    """测试基础导入"""
    print("🧪 测试基础导入...")
    
    try:
        from src.utils.config import Config
        print("✅ 配置模块导入成功")
        
        from src.utils.logger import setup_logging
        print("✅ 日志模块导入成功")
        
        from src.core.scanner import DirectoryScanner, FileInfo
        print("✅ 扫描器模块导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_config():
    """测试配置"""
    print("⚙️  测试配置模块...")
    
    try:
        from src.utils.config import config
        print(f"✅ 配置初始化成功")
        print(f"   日志级别: {config.log_level}")
        print(f"   最大文件数: {config.max_files}")
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_logging():
    """测试日志"""
    print("📝 测试日志模块...")
    
    try:
        from src.utils.logger import setup_logging, log_operation_start, log_operation_complete
        
        logger = setup_logging()
        print("✅ 日志系统初始化成功")
        
        log_operation_start("测试操作")
        log_operation_complete("测试操作", "成功")
        print("✅ 日志记录功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 日志测试失败: {e}")
        return False

def test_scanner():
    """测试扫描器"""
    print("🔍 测试文件扫描器...")
    
    try:
        from src.core.scanner import DirectoryScanner
        
        # 创建临时测试目录
        test_dir = Path(__file__).parent / "test_temp"
        test_dir.mkdir(exist_ok=True)
        
        # 创建测试文件
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        
        # 测试扫描
        scanner = DirectoryScanner(test_dir)
        files = scanner.scan_directory(recursive=False)
        
        print(f"✅ 扫描完成，找到 {len(files)} 个文件")
        
        if files:
            file_info = files[0]
            print(f"   文件名: {file_info.name}")
            print(f"   大小: {file_info.size} 字节")
        
        # 清理
        import shutil
        shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ 扫描器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 FreeU基础功能测试")
    print("=" * 40)
    
    tests = [
        test_basic_imports,
        test_config,
        test_logging,
        test_scanner
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            print()
    
    print("=" * 40)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！基础功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)