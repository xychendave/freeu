import gradio as gr
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
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
    
    def scan_directory(self, directory_path: str) -> str:
        """扫描目录（自动递归扫描所有文件）"""
        try:
            if not directory_path:
                return "❌ 请选择目录"
            directory = Path(directory_path)
            if not directory.exists():
                return f"❌ 目录不存在: {directory_path}"
            if not directory.is_dir():
                return f"❌ 路径不是目录: {directory_path}"
            log_operation_start("扫描目录", {"path": directory_path, "recursive": True})
            # 创建扫描器
            self.scanner = DirectoryScanner(directory)
            # 自动递归扫描所有文件
            self.current_files = self.scanner.scan_directory(recursive=True)
            
            # 获取统计信息
            summary = self.scanner.get_files_summary()
            log_operation_complete("扫描目录", f"找到 {summary['total_files']} 个文件")
            # 格式化输出
            result = f"✅ 扫描完成！正在准备AI自动整理...\n\n"
            result += f"📁 目录: {directory_path}\n"
            result += f"📊 总项目: {summary.get('total_items', summary['total_files'])} 个\n"
            result += f"   - 📄 文件: {summary['total_files']} 个\n"
            result += f"   - 📂 文件夹: {summary.get('total_directories', 0)} 个\n"
            result += f"💾 文件总大小: {self._format_file_size(summary['total_size'])}\n"
            if summary['extensions']:
                result += "\n📎 文件类型分布（前10）:\n"
                for ext, count in sorted(summary['extensions'].items(), key=lambda x: x[1], reverse=True)[:10]:
                    result += f"   {ext}: {count} 个\n"
            result += f"\n✨ 点击'开始智能整理'按钮，AI将自动为您整理文件"
            return result
        except Exception as e:
            log_operation_error("扫描目录", str(e))
            return f"❌ 扫描失败: {str(e)}"
    
    def auto_organize(self) -> str:
        """AI自动整理（使用system prompt）"""
        try:
            if not self.current_files:
                return "❌ 请先扫描目录"
            # 获取system prompt
            system_prompt = config._config.get('organization_prompt', self._get_default_prompt())
            log_operation_start("AI自动整理", {"file_count": len(self.current_files), "prompt_length": len(system_prompt)})
            # 初始化AI引擎（使用配置中的默认提供商）
            if not self.ai_engine:
                try:
                    self.ai_engine = MultiAIEngine()
                except ValueError as e:
                    return f"❌ AI配置错误: {str(e)}\n\n请在'AI设置'标签页配置API Key"
            # 使用system prompt自动生成整理方案
            ai_response = self.ai_engine.generate_organization_plan(system_prompt, self.current_files)
            self.current_actions = ai_response.actions
            
            log_operation_complete("AI自动整理", f"生成 {len(self.current_actions)} 个操作")
            if not self.current_actions:
                return "ℹ️ AI分析后认为文件已经整理得很好，无需调整"
            # 验证操作
            validation_results = self.ai_engine.validate_actions(self.current_actions, self.current_files)
            # 统计验证结果
            valid_actions = [r for r in validation_results if r["valid"]]
            invalid_actions = [r for r in validation_results if not r["valid"]]
            result = f"✅ AI整理方案生成完成！\n\n"
            result += f"🤖 使用AI: {self.ai_engine.provider}\n"
            result += f"📋 计划操作: {len(self.current_actions)} 项\n"
            result += f"✅ 有效操作: {len(valid_actions)} 项\n"
            if invalid_actions:
                result += f"⚠️  无效操作: {len(invalid_actions)} 项\n"
            result += f"\n📊 点击下方'查看整理方案'查看详情\n"
            result += f"✅ 确认无误后点击'执行整理'开始整理文件"
            return result
        except Exception as e:
            log_operation_error("AI自动整理", str(e))
            return f"❌ 整理失败: {str(e)}"
    
    def _get_default_prompt(self) -> str:
        """获取默认整理提示词"""
        return """你是一个专业的文件整理助手。请根据文件的类型、内容和用途，智能地将文件归类整理到合适的文件夹中。

整理原则：
1. 按文件类型分类（图片、文档、视频、音频、代码等）
2. 按项目或主题归类（工作、学习、个人等）
3. 按时间归档（如需要）
4. 保持目录结构清晰，便于查找
5. 相似或相关的文件放在一起
6. 为每个文件夹取一个清晰易懂的名称

请分析提供的文件列表，生成合理的整理方案。"""
    
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
        """执行整理方案并生成报告"""
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
            # 生成整理报告
            report = self._generate_organization_report(results, success_count, error_count)
            # 清空当前操作列表
            self.current_actions = []
            return report
        except Exception as e:
            log_operation_error("执行整理方案", str(e))
            return f"❌ 执行失败: {str(e)}"
    
    def _generate_organization_report(self, results: list, success_count: int, error_count: int) -> str:
        """生成整理报告"""
        report = f"# 📊 文件整理报告\n\n"
        report += f"## 整理概况\n"
        report += f"✅ 成功整理: {success_count} 个文件/文件夹\n"
        if error_count > 0:
            report += f"❌ 整理失败: {error_count} 个\n"
        report += f"\n## 整理规则说明\n"
        # 分析整理逻辑
        folder_groups = {}
        for r in results:
            if r["success"]:
                dest_folder = str(Path(r["destination"]).parent)
                if dest_folder not in folder_groups:
                    folder_groups[dest_folder] = []
                folder_groups[dest_folder].append(r)
        report += f"\n文件已按以下规则整理到 {len(folder_groups)} 个文件夹：\n\n"
        for folder, items in sorted(folder_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            report += f"### 📁 {folder}\n"
            report += f"- 包含 {len(items)} 个文件\n"
            # 分析文件类型
            extensions = {}
            for item in items:
                ext = Path(item["source"]).suffix or "无扩展名"
                extensions[ext] = extensions.get(ext, 0) + 1
            if extensions:
                report += f"- 文件类型: {', '.join([f'{ext}({count})' for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:5]])}\n"
            report += f"\n"
        report += f"\n## 如何查找文件\n\n"
        report += f"1. **按文件类型查找**: 文件已按类型归类到相应文件夹\n"
        report += f"2. **按项目主题查找**: 相关文件已归类到同一文件夹\n"
        report += f"3. **使用系统搜索**: 在整理后的文件夹中搜索更高效\n"
        if error_count > 0:
            report += f"\n## ⚠️ 错误详情\n\n"
            for r in results:
                if not r["success"]:
                    report += f"- ❌ {r['source']}: {r.get('error', '未知错误')}\n"
        report += f"\n---\n"
        report += f"整理完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        return report
    
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
    
    def set_default_provider(self, provider: str) -> str:
        """设置默认AI提供商"""
        try:
            config.ai_provider = provider
            logger.info(f"默认AI提供商已设置为: {provider}")
            # 如果AI引擎已初始化，也切换一下
            if self.ai_engine:
                self.ai_engine.switch_provider(provider)
            return f"✅ 默认AI提供商已设置为: {provider}"
        except Exception as e:
            logger.error(f"设置默认AI提供商失败: {e}")
            return f"❌ 设置失败: {str(e)}"
    
    def save_organization_prompt(self, prompt: str) -> str:
        """保存整理规则prompt"""
        try:
            config._config['organization_prompt'] = prompt
            config.save_config()
            logger.info("整理规则已更新")
            return f"✅ 整理规则已保存！共{len(prompt)}字符"
        except Exception as e:
            logger.error(f"保存整理规则失败: {e}")
            return f"❌ 保存失败: {str(e)}"
    
    def reset_organization_prompt(self) -> tuple:
        """重置整理规则为默认值"""
        default_prompt = self._get_default_prompt()
        try:
            config._config['organization_prompt'] = default_prompt
            config.save_config()
            logger.info("整理规则已重置为默认")
            return default_prompt, "✅ 已恢复默认整理规则"
        except Exception as e:
            logger.error(f"重置整理规则失败: {e}")
            return default_prompt, f"❌ 重置失败: {str(e)}"
    
    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_common_directory(self, dir_name: str) -> str:
        """获取常用目录路径"""
        home = str(Path.home())
        common_dirs = {
            "desktop": Path.home() / "Desktop",
            "documents": Path.home() / "Documents",
            "downloads": Path.home() / "Downloads",
            "pictures": Path.home() / "Pictures",
            "home": Path.home()
        }
        dir_path = common_dirs.get(dir_name.lower(), Path.home())
        if dir_path.exists():
            return str(dir_path)
        return home
    
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
                        gr.Markdown("**快速选择常用文件夹：**")
                        with gr.Row():
                            desktop_btn = gr.Button("🖥️ 桌面", size="sm")
                            documents_btn = gr.Button("📄 文档", size="sm")
                            downloads_btn = gr.Button("⬇️ 下载", size="sm")
                            pictures_btn = gr.Button("🖼️ 图片", size="sm")
                            home_btn = gr.Button("🏠 主目录", size="sm")
                        directory_input = gr.Textbox(
                            label="目标目录",
                            placeholder="点击上方按钮选择常用文件夹，或手动输入路径",
                            lines=1
                        )
                        scan_btn = gr.Button("🔍 扫描目录", variant="primary", size="lg")
                        scan_output = gr.Textbox(
                            label="扫描结果",
                            lines=8,
                            interactive=False
                        )
                        # AI自动整理
                        gr.Markdown("### 🤖 步骤2: AI智能整理")
                        gr.Markdown("AI将根据预设规则自动为您整理文件（可在设置页面自定义整理规则）")
                        auto_organize_btn = gr.Button("✨ 开始智能整理", variant="primary", size="lg")
                        organize_output = gr.Textbox(
                            label="整理方案",
                            lines=6,
                            interactive=False
                        )
                        # 执行操作
                        gr.Markdown("### ⚡ 步骤3: 执行与报告")
                        with gr.Row():
                            execute_btn = gr.Button("✅ 执行整理", variant="primary", size="lg")
                            refresh_preview_btn = gr.Button("🔄 查看整理方案", size="lg")
                        report_output = gr.Textbox(
                            label="整理报告",
                            lines=15,
                            interactive=False
                        )
                    
                    with gr.Column(scale=1):
                        # 方案预览
                        gr.Markdown("### 📋 整理方案预览")
                        preview_table = gr.Dataframe(
                            headers=["状态", "源文件", "目标路径", "原因", "操作", "备注"],
                            label="操作预览",
                            interactive=False,
                            wrap=True
                        )
                
                # 事件绑定 - 快捷文件夹按钮
                desktop_btn.click(
                    fn=lambda: self.get_common_directory("desktop"),
                    outputs=directory_input
                )
                documents_btn.click(
                    fn=lambda: self.get_common_directory("documents"),
                    outputs=directory_input
                )
                downloads_btn.click(
                    fn=lambda: self.get_common_directory("downloads"),
                    outputs=directory_input
                )
                pictures_btn.click(
                    fn=lambda: self.get_common_directory("pictures"),
                    outputs=directory_input
                )
                home_btn.click(
                    fn=lambda: self.get_common_directory("home"),
                    outputs=directory_input
                )
                scan_btn.click(
                    fn=self.scan_directory,
                    inputs=[directory_input],
                    outputs=scan_output
                )
                auto_organize_btn.click(
                    fn=self.auto_organize,
                    outputs=organize_output
                ).then(
                    fn=self.get_actions_preview,
                    outputs=preview_table
                )
                refresh_preview_btn.click(
                    fn=self.get_actions_preview,
                    outputs=preview_table
                )
                execute_btn.click(
                    fn=self.execute_organization_plan,
                    outputs=report_output
                ).then(
                    fn=self.get_actions_preview,
                    outputs=preview_table
                )
                
                gr.Markdown("""
                ### 📖 使用说明
                1. **选择目录**: 点击快捷按钮或输入要整理的目录路径，点击"扫描目录"（自动递归扫描所有文件）
                2. **AI整理**: 点击"开始智能整理"，AI将根据预设规则自动生成整理方案
                3. **预览方案**: 在右侧预览表格中查看详细的整理操作
                4. **执行整理**: 确认无误后点击"执行整理"，完成后查看详细报告
                
                ### ⚠️ 注意事项
                - AI整理规则可在'AI设置'中自定义
                - 只执行移动操作，不会删除文件
                - 自动跳过隐藏文件和系统文件
                - 首次使用需要在'AI设置'中配置API Key
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
                        # 整理规则配置
                        gr.Markdown("### 📝 整理规则配置")
                        gr.Markdown("自定义AI整理文件的规则和原则")
                        organization_prompt = gr.Textbox(
                            label="System Prompt（整理规则）",
                            value=config._config.get('organization_prompt', FreeUInterface()._get_default_prompt()),
                            lines=12,
                            placeholder="输入AI整理文件的规则...",
                            info="AI将根据这些规则自动整理文件"
                        )
                        with gr.Row():
                            save_prompt_btn = gr.Button("💾 保存整理规则", variant="primary")
                            reset_prompt_btn = gr.Button("🔄 恢复默认", variant="secondary")
                        prompt_result = gr.Textbox(
                            label="保存结果",
                            lines=1,
                            interactive=False
                        )
                        # 默认AI提供商选择
                        gr.Markdown("### 🎯 默认AI提供商")
                        default_provider_dropdown = gr.Dropdown(
                            choices=["claude", "openai", "kimi", "glm", "openrouter"],
                            value=config.ai_provider,
                            label="默认AI提供商",
                            info="整理文件时使用的AI服务"
                        )
                        set_default_provider_btn = gr.Button("💾 设置为默认", variant="secondary")
                        default_provider_result = gr.Textbox(
                            label="设置结果",
                            lines=1,
                            interactive=False
                        )
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
                """)
                
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
                # 整理规则事件绑定
                save_prompt_btn.click(
                    fn=self.save_organization_prompt,
                    inputs=[organization_prompt],
                    outputs=prompt_result
                )
                reset_prompt_btn.click(
                    fn=self.reset_organization_prompt,
                    outputs=[organization_prompt, prompt_result]
                )
                # 默认AI提供商设置事件绑定
                set_default_provider_btn.click(
                    fn=self.set_default_provider,
                    inputs=[default_provider_dropdown],
                    outputs=default_provider_result
                ).then(
                    fn=self.get_ai_config_display,
                    outputs=config_display
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
        server_port=7861,
        share=False,
        show_error=True
    )