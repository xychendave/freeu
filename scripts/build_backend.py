#!/usr/bin/env python3
"""
FreeU Python后端打包脚本
使用PyInstaller将Python后端打包成可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """运行命令"""
    print(f"运行命令: {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def install_dependencies():
    """安装依赖"""
    print("📦 安装Python依赖...")
    
    # 检查pip
    if not run_command("pip --version"):
        print("❌ pip未安装")
        return False
    
    # 安装依赖
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    if not requirements_file.exists():
        print(f"❌ 找不到requirements.txt: {requirements_file}")
        return False
    
    return run_command(f"pip install -r {requirements_file}")

def install_pyinstaller():
    """安装PyInstaller"""
    print("📦 安装PyInstaller...")
    return run_command("pip install pyinstaller")

def build_backend():
    """构建后端"""
    print("🔨 构建Python后端...")
    
    # 项目根目录
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    main_script = src_dir / "main.py"
    
    if not main_script.exists():
        print(f"❌ 找不到主脚本: {main_script}")
        return False
    
    # 构建命令
    build_cmd = [
        "pyinstaller",
        "--onefile",  # 打包成单个文件
        "--name", "freeu_backend",  # 可执行文件名
        "--distpath", "dist",  # 输出目录
        "--workpath", "build",  # 临时构建目录
        "--specpath", ".",  # spec文件目录
        "--clean",  # 清理临时文件
        "--noconfirm",  # 不确认覆盖
        # 包含数据文件
        "--add-data", f"{src_dir}/core:core",
        "--add-data", f"{src_dir}/ui:ui", 
        "--add-data", f"{src_dir}/utils:utils",
        # 隐藏导入
        "--hidden-import", "anthropic",
        "--hidden-import", "gradio",
        "--hidden-import", "pydantic",
        "--hidden-import", "pathlib",
        str(main_script)
    ]
    
    # 根据平台调整命令
    if sys.platform == "win32":
        # Windows平台使用分号分隔路径
        build_cmd = [cmd.replace(":", ";") if ":" in cmd and "add-data" in build_cmd[build_cmd.index(cmd)-1] else cmd for cmd in build_cmd]
    
    cmd_str = " ".join(build_cmd)
    
    print(f"构建命令: {cmd_str}")
    
    # 运行构建命令
    if not run_command(cmd_str, cwd=project_root):
        print("❌ PyInstaller构建失败")
        return False
    
    print("✅ 构建完成")
    return True

def copy_to_electron():
    """复制到Electron目录"""
    print("📁 复制构建结果到Electron目录...")
    
    project_root = Path(__file__).parent.parent
    dist_dir = project_root / "dist"
    electron_dir = project_root / "electron" / "python_backend"
    
    # 创建Electron目录
    electron_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制dist目录
    if dist_dir.exists():
        target_dist = electron_dir / "dist"
        if target_dist.exists():
            shutil.rmtree(target_dist)
        
        shutil.copytree(dist_dir, target_dist)
        print(f"✅ 已复制到: {target_dist}")
        return True
    else:
        print(f"❌ 找不到构建输出目录: {dist_dir}")
        return False

def main():
    """主函数"""
    print("🚀 FreeU Python后端打包工具")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 9):
        print("❌ 需要Python 3.9或更高版本")
        return False
    
    print(f"Python版本: {sys.version}")
    
    # 步骤1: 安装依赖
    if not install_dependencies():
        print("❌ 依赖安装失败")
        return False
    
    # 步骤2: 安装PyInstaller
    if not install_pyinstaller():
        print("❌ PyInstaller安装失败")
        return False
    
    # 步骤3: 构建后端
    if not build_backend():
        print("❌ 后端构建失败")
        return False
    
    # 步骤4: 复制到Electron目录
    if not copy_to_electron():
        print("❌ 复制失败")
        return False
    
    print("\n🎉 打包完成！")
    print("构建输出:")
    print(f"  - 可执行文件: dist/freeu_backend")
    print(f"  - Electron集成: electron/python_backend/dist/")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)