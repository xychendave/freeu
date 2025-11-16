#!/usr/bin/env python3
"""
FreeU - AI文件整理助手
基于Claude AI的本地文件整理工具
"""

import sys
import os
from pathlib import Path

# 将src目录添加到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

def main():
    """主函数"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 9):
            print("❌ 错误: FreeU需要Python 3.9或更高版本")
            print(f"当前版本: Python {sys.version}")
            sys.exit(1)
        
        # 检查依赖
        try:
            import gradio
            import anthropic
            import pydantic
        except ImportError as e:
            print("❌ 错误: 缺少必要的依赖包")
            print(f"请运行: pip install -r requirements.txt")
            print(f"具体错误: {e}")
            sys.exit(1)
        
        # 启动应用
        print("🚀 启动 FreeU - AI文件整理助手")
        print("正在初始化界面...")
        
        from src.ui.gradio_interface import create_app
        
        app = create_app()
        
        print("✅ 应用启动成功！")
        print("📱 请打开浏览器访问: http://127.0.0.1:7860")
        print("⏹️  按 Ctrl+C 停止应用")
        
        # 启动Gradio应用
        app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False
        )
        
    except KeyboardInterrupt:
        print("\n⏹️  应用被用户停止")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()