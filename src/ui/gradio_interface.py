import gradio as gr
import logging
from pathlib import Path
from typing import List, Dict, Optional
from src.core.scanner import DirectoryScanner, FileInfo
from src.core.ai_engine import ClaudeAI, FileAction
from src.core.file_executor import FileExecutor
from src.utils.config import config
from src.utils.logger import (
    setup_logging, log_operation_start, log_operation_complete, 
    log_operation_error, log_operation_warning, log_progress
)

# 初始化日志
logger = setup_logging()

class FreeUInterface:
    """FreeU Gradio界面类"""
    
    def __init__(self):
        self.scanner: Optional[DirectoryScanner] = None
        self.ai_engine: Optional[ClaudeAI] = None
        self.executor: Optional[FileExecutor] = None
        self.current_files: List[FileInfo] = []
        self.current_actions: List[FileAction] = []
        
        logger.info("FreeU界面初始化")
    
    def scan_directory(self, directory_path: str, recursive: bool = False) -> str:
        """扫描目录"""
        try:
            if not directory_path:
                return "❌ 请选择目录"
            
            directory = Path(directory_path)
            if not directory.exists():
                return f"❌ 目录不存在: {directory_path}"
            
            if not directory.is_dir():
                return f"❌ 路径不是目录: {directory_path}"
            
            log_operation_start("扫描目录", {"path": directory_path, "recursive": recursive})
            
            # 创建扫描器
            self.scanner = DirectoryScanner(directory)
            
            # 扫描文件
            self.current_files = self.scanner.scan_directory(recursive)
            
            # 获取统计信息
            summary = self.scanner.get_files_summary()
            
            log_operation_complete("扫描目录", f"找到 {summary['total_files']} 个文件")
            
            # 格式化输出
            result = f"✅ 扫描完成！\n"
            result += f"📁 目录: {directory_path}\n"
            result += f"📊 文件数量: {summary['total_files']}\n"
            result += f"💾 总大小: {self._format_file_size(summary['total_size'])}\n"
            
            if summary['extensions']:
                result += "📎 文件类型分布:\n"
                for ext, count in sorted(summary['extensions'].items(), key=lambda x: x[1], reverse=True)[:10]:
                    result += f"   {ext}: {count} 个\n"
            
            return result
            
        except Exception as e:
            log_operation_error("扫描目录", str(e))
            return f"❌ 扫描失败: {str(e)}"
    
    def generate_organization_plan(self, instruction: str) -> str:
        """生成整理方案"""
        try:
            if not self.current_files:
                return "❌ 请先扫描目录"
            
            if not instruction.strip():
                return "❌ 请输入整理指令"
            
            log_operation_start("生成整理方案", {"instruction": instruction, "file_count": len(self.current_files)})
            
            # 初始化AI引擎
            if not self.ai_engine:
                try:
                    self.ai_engine = ClaudeAI()
                except ValueError as e:
                    return f"❌ Claude API配置错误: {str(e)}\n\n请在设置中配置API Key"
            
            # 生成整理方案
            ai_response = self.ai_engine.generate_organization_plan(instruction, self.current_files)
            self.current_actions = ai_response.actions
            
            log_operation_complete("生成整理方案", f"生成 {len(self.current_actions)} 个操作")
            
            if not self.current_actions:
                return "ℹ️ 未找到需要整理的文件"
            
            # 验证操作
            validation_results = self.ai_engine.validate_actions(self.current_actions, self.current_files)
            
            # 统计验证结果
            valid_actions = [r for r in validation_results if r["valid"]]
            invalid_actions = [r for r in validation_results if not r["valid"]]
            
            result = f"✅ 整理方案生成完成！\n"
            result += f"📋 总操作数: {len(self.current_actions)}\n"
            result += f"✅ 有效操作: {len(valid_actions)}\n"
            
            if invalid_actions:
                result += f"⚠️  无效操作: {len(invalid_actions)}\n"
            
            return result
            
        except Exception as e:
            log_operation_error("生成整理方案", str(e))
            return f"❌ 方案生成失败: {str(e)}"
    
    def get_actions_preview(self) -> List[List]:
        """获取操作预览表格数据"""
        if not self.current_actions:
            return []
        
        # 验证操作
        if self.ai_engine:
            validation_results = self.ai_engine.validate_actions(self.current_actions, self.current_files)
        else:
            validation_results = [{"valid": True, "message": ""} for _ in self.current_actions]
        
        preview_data = []
        for i, (action, validation) in enumerate(zip(self.current_actions, validation_results)):
            status = "✅" if validation["valid"] else "❌"
            preview_data.append([
                status,
                action.source,
                action.destination,
                action.reason,
                action.action_type,
                validation.get("message", "")
            ])
        
        return preview_data
    
    def execute_organization_plan(self) -> str:
        """执行整理方案"""
        try:
            if not self.current_actions:
                return "❌ 没有可执行的操作"
            
            if not self.scanner:
                return "❌ 扫描器未初始化"
            
            log_operation_start("执行整理方案", {"action_count": len(self.current_actions)})
            
            # 初始化执行器
            if not self.executor:
                self.executor = FileExecutor(self.scanner.base_path)
            
            # 执行操作
            results = self.executor.execute_actions(self.current_actions, self.current_files)
            
            # 统计结果
            success_count = sum(1 for r in results if r["success"])
            error_count = sum(1 for r in results if not r["success"])
            
            log_operation_complete("执行整理方案", f"成功: {success_count}, 失败: {error_count}")
            
            # 生成结果报告
            result = f"✅ 执行完成！\n"
            result += f"📊 总操作: {len(results)}\n"
            result += f"✅ 成功: {success_count}\n"
            
            if error_count > 0:
                result += f"❌ 失败: {error_count}\n\n"
                result += "错误详情:\n"
                for r in results:
                    if not r["success"]:
                        result += f"  ❌ {r['source']} → {r['destination']}: {r['error']}\n"
            
            # 清空当前操作列表
            self.current_actions = []
            
            return result
            
        except Exception as e:
            log_operation_error("执行整理方案", str(e))
            return f"❌ 执行失败: {str(e)}"
    
    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def create_interface(self) -> gr.Blocks:
        """创建Gradio界面"""
        with gr.Blocks(title="FreeU - AI文件整理助手", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# 🎯 FreeU - AI文件整理助手")
            gr.Markdown("通过自然语言指令，让AI帮你整理本地文件")
            
            with gr.Row():
                with gr.Column(scale=1):
                    # 目录选择和扫描
                    gr.Markdown("### 📁 步骤1: 选择目录")
                    directory_input = gr.Textbox(
                        label="目标目录",
                        placeholder="例如: /Users/dave/Desktop",
                        lines=1
                    )
                    
                    with gr.Row():
                        scan_btn = gr.Button("🔍 扫描目录", variant="primary")
                        recursive_check = gr.Checkbox(label="递归扫描子目录", value=False)
                    
                    scan_output = gr.Textbox(
                        label="扫描结果",
                        lines=6,
                        interactive=False
                    )
                    
                    # 指令输入
                    gr.Markdown("### 💬 步骤2: 输入整理指令")
                    instruction_input = gr.Textbox(
                        label="整理指令",
                        placeholder="例如: 把图片放到 Pictures，文档放到 Docs",
                        lines=3
                    )
                    
                    generate_btn = gr.Button("🤖 生成整理方案", variant="primary")
                    plan_output = gr.Textbox(
                        label="方案生成结果",
                        lines=4,
                        interactive=False
                    )
                    
                    # 执行操作
                    gr.Markdown("### ⚡ 步骤3: 执行整理")
                    execute_btn = gr.Button("✅ 确认执行", variant="primary")
                    execute_output = gr.Textbox(
                        label="执行结果",
                        lines=8,
                        interactive=False
                    )
                
                with gr.Column(scale=1):
                    # 方案预览
                    gr.Markdown("### 📋 整理方案预览")
                    preview_table = gr.Dataframe(
                        headers=["状态", "源文件", "目标路径", "原因", "操作", "备注"],
                        label="操作预览",
                        interactive=False,
                        max_rows=20
                    )
                    
                    refresh_preview_btn = gr.Button("🔄 刷新预览")
            
            # 事件绑定
            scan_btn.click(
                fn=self.scan_directory,
                inputs=[directory_input, recursive_check],
                outputs=scan_output
            )
            
            generate_btn.click(
                fn=self.generate_organization_plan,
                inputs=instruction_input,
                outputs=plan_output
            )
            
            refresh_preview_btn.click(
                fn=self.get_actions_preview,
                outputs=preview_table
            )
            
            execute_btn.click(
                fn=self.execute_organization_plan,
                outputs=execute_output
            )
            
            # 自动刷新预览
            generate_btn.click(
                fn=self.get_actions_preview,
                outputs=preview_table
            )
            
            execute_btn.click(
                fn=self.get_actions_preview,
                outputs=preview_table
            )
            
            gr.Markdown("""
            ### 📖 使用说明
            1. **选择目录**: 输入要整理的目录路径，点击"扫描目录"
            2. **输入指令**: 用自然语言描述整理需求
            3. **生成方案**: AI分析文件并生成整理方案
            4. **预览确认**: 查看整理方案，确认无误后执行
            5. **执行操作**: 点击"确认执行"完成文件整理
            
            ### ⚠️ 注意事项
            - 只支持移动操作，不会删除文件
            - 自动跳过隐藏文件和系统文件
            - 首次使用需要配置Claude API Key
            - 建议先备份重要文件
            """)
        
        return interface

def create_app():
    """创建应用"""
    interface = FreeUInterface()
    return interface.create_interface()

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )