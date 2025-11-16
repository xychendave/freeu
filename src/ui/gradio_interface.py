import gradio as gr
import logging
from pathlib import Path
from typing import List, Dict, Optional
from src.core.scanner import DirectoryScanner, FileInfo
from src.core.ai_engine import MultiAIEngine, FileAction
from src.core.file_executor import FileExecutor
from src.utils.config import config
from src.utils.logger import (
    setup_logging, log_operation_start, log_operation_complete, 
    log_operation_error, log_operation_warning, log_progress
)
import json

# 初始化日志
logger = setup_logging()

class FreeUInterface:
    """FreeU Gradio界面类"""
    
    def __init__(self):
        self.scanner: Optional[DirectoryScanner] = None
        self.ai_engine: Optional[MultiAIEngine] = None
        self.executor: Optional[FileExecutor] = None
        self.current_files: List[FileInfo] = []
        self.current_actions: List[FileAction] = []
        
        logger.info("FreeU界面初始化")
    
    def scan_directory(self, directory_path: str, recursive: bool = False, scan_all_files: bool = False) -> str:
        """扫描目录"""
        try:
            if not directory_path:
                return "❌ 请选择目录"
            
            directory = Path(directory_path)
            if not directory.exists():
                return f"❌ 目录不存在: {directory_path}"
            
            if not directory.is_dir():
                return f"❌ 路径不是目录: {directory_path}"
            
            log_operation_start("扫描目录", {"path": directory_path, "recursive": recursive, "scan_all_files": scan_all_files})
            
            # 临时设置扫描所有文件选项
            if scan_all_files:
                original_scan_all = config._config.get('scan_all_files', False)
                config._config['scan_all_files'] = True
            
            # 创建扫描器
            self.scanner = DirectoryScanner(directory)
            
            # 扫描文件
            self.current_files = self.scanner.scan_directory(recursive)
            
            # 获取统计信息
            summary = self.scanner.get_files_summary()
            
            log_operation_complete("扫描目录", f"找到 {summary['total_files']} 个文件")
            
            # 恢复原始设置
            if scan_all_files:
                config._config['scan_all_files'] = original_scan_all
            
            # 格式化输出
            result = f"✅ 扫描完成！\n"
            result += f"📁 目录: {directory_path}\n"
            result += f"📊 文件数量: {summary['total_files']}\n"
            result += f"💾 总大小: {self._format_file_size(summary['total_size'])}\n"
            if scan_all_files:
                result += f"🔄 扫描模式: 无限制\n"
            else:
                result += f"⚠️  扫描模式: 有限制（最多{config.max_files}个文件）\n"
            
            if summary['extensions']:
                result += "📎 文件类型分布:\n"
                for ext, count in sorted(summary['extensions'].items(), key=lambda x: x[1], reverse=True)[:10]:
                    result += f"   {ext}: {count} 个\n"
            
            return result
            
        except Exception as e:
            log_operation_error("扫描目录", str(e))
            # 确保恢复原始设置
            if scan_all_files and 'original_scan_all' in locals():
                config._config['scan_all_files'] = original_scan_all
            return f"❌ 扫描失败: {str(e)}"
    
    def generate_organization_plan(self, instruction: str, ai_provider: str = None) -> str:
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
                    self.ai_engine = MultiAIEngine(ai_provider)
                except ValueError as e:
                    available_providers = self.ai_engine.get_available_providers() if hasattr(self.ai_engine, 'get_available_providers') else []
                    if available_providers:
                        return f"❌ AI配置错误: {str(e)}\n\n请在设置中配置API Key。可用的AI提供商: {', '.join(available_providers)}"
                    else:
                        return f"❌ AI配置错误: {str(e)}\n\n请在设置中配置API Key"
            
            # 如果指定了不同的AI提供商，切换
            if ai_provider and ai_provider != self.ai_engine.provider:
                success = self.ai_engine.switch_provider(ai_provider)
                if not success:
                    return f"❌ 切换到AI提供商 {ai_provider} 失败，请检查配置"
            
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
            result += f"🤖 AI提供商: {self.ai_engine.provider}\n"
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
    
    def get_available_ai_providers(self) -> List[str]:
        """获取可用的AI提供商列表"""
        try:
            if not self.ai_engine:
                # 临时创建AI引擎来获取可用提供商
                temp_engine = MultiAIEngine()
                providers = temp_engine.get_available_providers()
            else:
                providers = self.ai_engine.get_available_providers()
            
            return providers if providers else ["claude"]  # 默认返回claude
        except:
            return ["claude"]  # 出错时返回默认
    
    def get_ai_config_display(self) -> str:
        """获取AI配置显示信息"""
        try:
            providers_config = config._config.get('ai_providers', {})
            current_provider = config.ai_provider
            
            config_info = f"当前AI提供商: {current_provider}\n\n"
            config_info += "已配置的AI提供商:\n"
            
            for provider, provider_config in providers_config.items():
                api_key_status = "✅ 已配置" if provider_config.get('api_key') else "❌ 未配置"
                model = provider_config.get('model', '默认模型')
                enabled = "✅ 启用" if provider_config.get('enabled', False) else "❌ 禁用"
                
                config_info += f"\n{provider}:\n"
                config_info += f"  - API Key: {api_key_status}\n"
                config_info += f"  - 模型: {model}\n"
                config_info += f"  - 状态: {enabled}\n"
            
            return config_info
            
        except Exception as e:
            return f"获取配置信息失败: {str(e)}"
    
    def update_ai_provider_config(self, provider: str, api_key: str, model: str = None, enabled: bool = None) -> str:
        """更新AI提供商配置"""
        try:
            # 获取当前配置
            providers_config = config._config.get('ai_providers', {})
            
            if provider not in providers_config:
                return f"❌ 不支持的AI提供商: {provider}"
            
            # 更新配置
            provider_config = providers_config[provider]
            
            if api_key.strip():
                provider_config['api_key'] = api_key.strip()
            
            if model and model.strip():
                provider_config['model'] = model.strip()
            
            if enabled is not None:
                provider_config['enabled'] = enabled
            
            # 保存配置
            config._config['ai_providers'] = providers_config
            config.save_config()
            
            logger.info(f"AI提供商配置已更新: {provider}")
            return f"✅ AI提供商 {provider} 配置已更新！"
            
        except Exception as e:
            logger.error(f"更新AI提供商配置失败: {e}")
            return f"❌ 配置更新失败: {str(e)}"
    
    def switch_ai_provider(self, provider: str) -> str:
        """切换AI提供商"""
        try:
            if not self.ai_engine:
                return "❌ 请先初始化AI引擎"
            
            success = self.ai_engine.switch_provider(provider)
            if success:
                return f"✅ 已切换到AI提供商: {provider}"
            else:
                return f"❌ 切换到AI提供商 {provider} 失败"
                
        except Exception as e:
            return f"❌ 切换失败: {str(e)}"
    
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
            
            with gr.Tab("文件整理"):
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
                            scan_all_check = gr.Checkbox(label="扫描所有文件（无限制）", value=False)
                        
                        scan_output = gr.Textbox(
                            label="扫描结果",
                            lines=6,
                            interactive=False
                        )
                        
                        # AI提供商选择
                        gr.Markdown("### 🤖 步骤2: 选择AI提供商")
                        available_providers = self.get_available_ai_providers()
                        ai_provider_dropdown = gr.Dropdown(
                            choices=available_providers,
                            value=available_providers[0] if available_providers else "claude",
                            label="AI提供商",
                            info="选择要使用的AI服务提供商"
                        )
                        
                        # 指令输入
                        gr.Markdown("### 💬 步骤3: 输入整理指令")
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
                        gr.Markdown("### ⚡ 步骤4: 执行整理")
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
                            interactive=False
                        )
                        
                        refresh_preview_btn = gr.Button("🔄 刷新预览")
                
                # 事件绑定
                scan_btn.click(
                    fn=self.scan_directory,
                    inputs=[directory_input, recursive_check, scan_all_check],
                    outputs=scan_output
                )
                
                generate_btn.click(
                    fn=self.generate_organization_plan,
                    inputs=[instruction_input, ai_provider_dropdown],
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
                2. **选择AI**: 选择要使用的AI提供商（Claude、OpenAI、Kimi等）
                3. **输入指令**: 用自然语言描述整理需求
                4. **生成方案**: AI分析文件并生成整理方案
                5. **预览确认**: 查看整理方案，确认无误后执行
                6. **执行操作**: 点击"确认执行"完成文件整理
                
                ### ⚠️ 注意事项
                - 只支持移动操作，不会删除文件
                - 自动跳过隐藏文件和系统文件
                - 首次使用需要配置AI提供商的API Key
                - 建议先备份重要文件
                """)
            
            with gr.Tab("AI设置"):
                gr.Markdown("## 🔧 AI提供商配置")
                gr.Markdown("配置不同AI提供商的API Key，支持Claude、OpenAI、Kimi、GLM、OpenRouter等")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        # 当前配置显示
                        config_display = gr.Textbox(
                            label="当前配置状态",
                            value=self.get_ai_config_display(),
                            lines=10,
                            interactive=False
                        )
                        
                        refresh_config_btn = gr.Button("🔄 刷新配置状态")
                        
                        # 全局扫描设置
                        gr.Markdown("### ⚙️ 扫描设置")
                        scan_all_global_check = gr.Checkbox(
                            label="默认扫描所有文件（无限制）",
                            value=config._config.get('scan_all_files', False),
                            info="默认关闭文件数量限制"
                        )
                        
                        max_files_input = gr.Number(
                            label="最大文件数量",
                            value=config.max_files,
                            minimum=100,
                            maximum=100000,
                            step=100,
                            info="设置文件扫描数量上限"
                        )
                        
                        save_scan_settings_btn = gr.Button("💾 保存扫描设置")
                    
                    with gr.Column(scale=1):
                        # 配置表单
                        gr.Markdown("### 📝 配置AI提供商")
                        
                        provider_select = gr.Dropdown(
                            choices=["claude", "openai", "kimi", "glm", "openrouter"],
                            value="claude",
                            label="选择AI提供商"
                        )
                        
                        api_key_input = gr.Textbox(
                            label="API Key",
                            placeholder="输入您的API Key",
                            type="password",
                            lines=1
                        )
                        
                        model_input = gr.Textbox(
                            label="模型名称（可选）",
                            placeholder="留空使用默认模型",
                            lines=1
                        )
                        
                        enabled_check = gr.Checkbox(
                            label="启用此提供商",
                            value=True
                        )
                        
                        update_config_btn = gr.Button("💾 保存配置", variant="primary")
                        config_result = gr.Textbox(
                            label="配置结果",
                            lines=2,
                            interactive=False
                        )
                        
                        # 测试连接按钮
                        test_connection_btn = gr.Button("🔗 测试连接")
                        test_result = gr.Textbox(
                            label="测试结果",
                            lines=2,
                            interactive=False
                        )
                
                gr.Markdown("""
                ### 🔑 获取API Key
                - **Claude**: [Anthropic Console](https://console.anthropic.com/)
                - **OpenAI**: [OpenAI API Keys](https://platform.openai.com/api-keys)
                - **Kimi**: [Moonshot AI](https://platform.moonshot.cn/)
                - **GLM**: [Zhipu AI](https://open.bigmodel.cn/)
                - **OpenRouter**: [OpenRouter](https://openrouter.ai/keys)
                
                ### 💡 使用建议
                1. 建议配置多个AI提供商作为备用
                2. 不同提供商的模型能力各有特色
                3. 可以根据任务复杂度选择不同的提供商
                4. API Key请妥善保管，不要分享给他人
                """
                
                # AI设置页面的事件绑定
                refresh_config_btn.click(
                    fn=self.get_ai_config_display,
                    outputs=config_display
                )
                
                update_config_btn.click(
                    fn=self.update_ai_provider_config,
                    inputs=[provider_select, api_key_input, model_input, enabled_check],
                    outputs=config_result
                ).then(
                    fn=self.get_ai_config_display,
                    outputs=config_display
                )
                
                test_connection_btn.click(
                    fn=self._test_ai_connection,
                    inputs=[provider_select],
                    outputs=test_result
                )
                
                # 扫描设置事件绑定
                save_scan_settings_btn.click(
                    fn=self.save_scan_settings,
                    inputs=[scan_all_global_check, max_files_input],
                    outputs=config_result
                ).then(
                    fn=self.get_ai_config_display,
                    outputs=config_display
                )
            
        return interface
    
    def save_scan_settings(self, scan_all_files: bool, max_files: int) -> str:
        """保存扫描设置"""
        try:
            config._config['scan_all_files'] = scan_all_files
            config._config['max_files'] = max(max_files, 100)  # 最少100个文件
            config.save_config()
            
            logger.info(f"扫描设置已更新: scan_all_files={scan_all_files}, max_files={max_files}")
            return f"✅ 扫描设置已保存！\n- 扫描所有文件: {'是' if scan_all_files else '否'}\n- 最大文件数量: {max_files}"
            
        except Exception as e:
            logger.error(f"保存扫描设置失败: {e}")
            return f"❌ 保存扫描设置失败: {str(e)}"
    
    def _test_ai_connection(self, provider: str) -> str:
        """测试AI连接"""
        try:
            # 创建临时引擎测试连接
            test_engine = MultiAIEngine(provider)
            
            # 简单的测试请求
            test_files = [
                FileInfo(name="test.txt", path="/tmp/test.txt", size=100, 
                      modified_time="2024-01-01 00:00:00", is_directory=False)
            ]
            
            result = test_engine.generate_organization_plan("测试连接", test_files)
            return f"✅ AI提供商 {provider} 连接测试成功！"
            
        except Exception as e:
            return f"❌ AI提供商 {provider} 连接测试失败: {str(e)}"


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