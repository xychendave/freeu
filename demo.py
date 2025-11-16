#!/usr/bin/env python3
"""
FreeU演示脚本 - 展示核心功能
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

def demo_ai_engine(files):
    """演示AI引擎功能"""
    print(f"\n🤖 演示AI引擎功能")
    print("-" * 40)
    
    try:
        from src.core.ai_engine import ClaudeAI
        
        # 检查API Key
        from src.utils.config import config
        if not config.anthropic_api_key:
            print("⚠️  未配置Claude API Key，跳过AI演示")
            print("  如需演示AI功能，请配置API Key")
            return None
        
        ai = ClaudeAI()
        
        # 测试指令
        instructions = [
            "把图片文件整理到Pictures文件夹",
            "把文档文件整理到Documents文件夹",
            "按文件类型分类整理"
        ]
        
        for instruction in instructions:
            print(f"\n📝 测试指令: {instruction}")
            try:
                response = ai.generate_organization_plan(instruction, files)
                actions = response.actions
                print(f"  ✅ 生成 {len(actions)} 个操作")
                
                for action in actions[:3]:  # 只显示前3个操作
                    print(f"    📋 {action.source} → {action.destination}")
                    print(f"       原因: {action.reason}")
                
                if len(actions) > 3:
                    print(f"    ... 还有 {len(actions) - 3} 个操作")
                    
            except Exception as e:
                print(f"  ❌ AI调用失败: {e}")
                
        return actions if 'actions' in locals() else None
        
    except Exception as e:
        print(f"❌ AI引擎初始化失败: {e}")
        return None

def demo_file_operations(demo_dir, actions=None):
    """演示文件操作功能"""
    print(f"\n⚙️  演示文件操作功能")
    print("-" * 40)
    
    from src.core.file_executor import FileExecutor
    
    executor = FileExecutor(demo_dir)
    
    # 创建一些测试操作
    test_actions = []
    
    if actions and len(actions) > 0:
        # 使用AI生成的操作
        test_actions = actions[:2]  # 只测试前2个操作
        print(f"📋 使用AI生成的操作进行测试")
    else:
        # 创建简单的测试操作
        from src.core.ai_engine import FileAction
        
        # 创建目标目录
        target_dir = demo_dir / "TestTarget"
        target_dir.mkdir(exist_ok=True)
        
        test_actions = [
            FileAction(
                action_type="move",
                source="README.md",
                destination="TestTarget/README_moved.md",
                reason="演示移动操作"
            )
        ]
        print(f"📋 使用预设操作进行测试")
    
    print(f"🎯 测试操作数量: {len(test_actions)}")
    
    # 模拟可用文件列表
    from src.core.scanner import DirectoryScanner
    scanner = DirectoryScanner(demo_dir)
    available_files = scanner.scan_directory(recursive=False)
    
    # 执行操作
    results = executor.execute_actions(test_actions, available_files)
    
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

def main():
    """主演示函数"""
    print("🎯 FreeU核心功能演示")
    print("=" * 50)
    
    try:
        # 创建演示文件
        demo_dir = create_demo_files()
        
        # 演示文件扫描
        files = demo_scanner(demo_dir)
        
        # 演示AI引擎
        actions = demo_ai_engine(files)
        
        # 演示文件操作
        results = demo_file_operations(demo_dir, actions)
        
        print(f"\n🎉 演示完成！")
        print(f"📁 演示目录: {demo_dir}")
        print(f"💡 可以手动检查该目录查看文件整理结果")
        
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