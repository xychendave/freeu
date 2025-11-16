#!/usr/bin/env python3
"""
FreeU简化演示 - 不依赖AI功能
"""

import sys
import tempfile
import shutil
from pathlib import Path

# 将src目录添加到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

def create_demo_files():
    """创建演示文件"""
    demo_dir = Path(tempfile.mkdtemp(prefix="freeu_demo_"))
    print(f"📁 创建演示目录: {demo_dir}")
    
    # 创建不同类型的文件
    files = [
        ("vacation_photo.jpg", "Beautiful sunset photo"),
        ("family_dinner.png", "Family gathering picture"),
        ("report_2024.pdf", "Annual work report"),
        ("meeting_notes.txt", "Team meeting minutes"),
        ("presentation.pptx", "Project presentation"),
        ("budget.xlsx", "Monthly budget spreadsheet"),
        ("song1.mp3", "Favorite music track"),
        ("movie_clip.mp4", "Home video recording"),
        ("archive.zip", "Compressed backup files"),
        ("README.md", "Project documentation")
    ]
    
    for filename, content in files:
        file_path = demo_dir / filename
        file_path.write_text(content)
        print(f"  📄 创建文件: {filename}")
    
    return demo_dir

def demo_scanner(demo_dir):
    """演示文件扫描功能"""
    print(f"\n🔍 演示文件扫描功能")
    print("-" * 40)
    
    from src.core.scanner import DirectoryScanner
    
    scanner = DirectoryScanner(demo_dir)
    files = scanner.scan_directory(recursive=False)
    
    print(f"📊 扫描结果:")
    print(f"  找到 {len(files)} 个文件")
    
    summary = scanner.get_files_summary()
    print(f"  总大小: {summary['total_size']} 字节")
    print(f"  文件类型:")
    
    for ext, count in sorted(summary['extensions'].items(), key=lambda x: x[1], reverse=True):
        print(f"    {ext}: {count} 个")
    
    return files

def demo_file_operations(demo_dir, files):
    """演示文件操作功能"""
    print(f"\n⚙️  演示文件操作功能")
    print("-" * 40)
    
    from src.core.file_executor import FileExecutor, FileAction
    
    executor = FileExecutor(demo_dir)
    
    # 创建一些简单的测试操作
    # 创建目标目录
    pictures_dir = demo_dir / "Pictures"
    documents_dir = demo_dir / "Documents"
    pictures_dir.mkdir(exist_ok=True)
    documents_dir.mkdir(exist_ok=True)
    
    # 创建测试操作
    test_actions = [
        FileAction(
            action_type="move",
            source="vacation_photo.jpg",
            destination="Pictures/vacation_photo.jpg",
            reason="移动图片到Pictures文件夹"
        ),
        FileAction(
            action_type="move",
            source="report_2024.pdf",
            destination="Documents/report_2024.pdf",
            reason="移动文档到Documents文件夹"
        ),
        FileAction(
            action_type="move",
            source="README.md",
            destination="Documents/README_moved.md",
            reason="演示移动操作"
        )
    ]
    
    print(f"🎯 测试操作数量: {len(test_actions)}")
    
    # 执行操作
    results = executor.execute_actions(test_actions, files)
    
    print(f"📊 执行结果:")
    success_count = sum(1 for r in results if r["success"])
    error_count = len(results) - success_count
    
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失败: {error_count}")
    
    # 显示详细结果
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {result['source']} → {result['destination']}")
        if not result["success"] and result.get("error"):
            print(f"     错误: {result['error']}")
    
    return results

def demo_path_safety(demo_dir):
    """演示路径安全检查"""
    print(f"\n🔒 演示路径安全检查")
    print("-" * 40)
    
    from src.core.file_executor import FileExecutor
    
    executor = FileExecutor(demo_dir)
    
    # 测试安全路径
    safe_path = demo_dir / "safe_file.txt"
    print(f"✅ 安全路径: {safe_path}")
    print(f"   检查结果: {executor._is_path_safe(safe_path)}")
    
    # 测试不安全路径
    unsafe_path = demo_dir / ".." / "unsafe.txt"
    print(f"❌ 不安全路径: {unsafe_path}")
    print(f"   检查结果: {executor._is_path_safe(unsafe_path)}")

def demo_unique_filename(demo_dir):
    """演示唯一文件名生成"""
    print(f"\n📝 演示唯一文件名生成")
    print("-" * 40)
    
    from src.core.file_executor import FileExecutor
    
    executor = FileExecutor(demo_dir)
    
    # 创建已存在的文件
    existing_file = demo_dir / "existing.txt"
    existing_file.write_text("content")
    
    print(f"📄 已存在文件: {existing_file}")
    
    # 生成唯一文件名
    new_path = executor._generate_unique_filename(existing_file)
    print(f"🆕 生成的唯一文件名: {new_path.name}")
    
    # 验证文件不存在
    print(f"✅ 文件不存在: {not new_path.exists()}")

def main():
    """主演示函数"""
    print("🎯 FreeU核心功能演示（无AI版本）")
    print("=" * 50)
    
    try:
        # 创建演示文件
        demo_dir = create_demo_files()
        
        # 演示文件扫描
        files = demo_scanner(demo_dir)
        
        # 演示文件操作
        results = demo_file_operations(demo_dir, files)
        
        # 演示路径安全检查
        demo_path_safety(demo_dir)
        
        # 演示唯一文件名生成
        demo_unique_filename(demo_dir)
        
        print(f"\n🎉 演示完成！")
        print(f"📁 演示目录: {demo_dir}")
        print(f"💡 可以手动检查该目录查看文件整理结果")
        
        # 显示目录结构
        print(f"\n📂 最终目录结构:")
        for item in sorted(demo_dir.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(demo_dir)
                print(f"  📄 {rel_path}")
            elif item.is_dir() and item != demo_dir:
                rel_path = item.relative_to(demo_dir)
                print(f"  📁 {rel_path}/")
        
        # 询问是否清理演示文件
        print(f"\n🧹 演示文件位于: {demo_dir}")
        print("可以选择手动删除或保留用于进一步测试")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)