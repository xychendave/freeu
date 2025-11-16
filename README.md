# FreeU - AI文件整理助手

基于Claude AI的本地文件整理工具，让普通用户通过自然语言指令轻松整理文件。

## 功能特点

- 🎯 **自然语言交互**：用日常语言描述整理需求
- 🤖 **AI智能分析**：Claude AI理解用户意图并生成整理方案
- 👀 **预览确认**：先展示整理方案，用户确认后执行
- 🔒 **安全可靠**：只移动文件，不删除，支持撤销
- 💻 **桌面应用**：Electron打包，无需命令行操作

## 技术架构

- **前端**：Gradio Web UI
- **后端**：Python 3.9+
- **AI引擎**：Claude API
- **桌面打包**：Electron

## 快速开始

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python src/main.py
```

### 配置Claude API

首次使用时，应用会提示输入Claude API Key。你也可以手动创建配置文件：

```bash
mkdir -p ~/.freeu
echo '{"anthropic_api_key": "your-api-key"}' > ~/.freeu/config.json
```

## 使用示例

1. 选择要整理的目录（如桌面）
2. 输入自然语言指令："把图片放到Pictures，文档放到Docs"
3. 查看AI生成的整理方案
4. 确认无误后点击"执行"

## 安全说明

- 只操作用户指定的目录
- 不会删除任何文件
- 自动跳过系统文件和隐藏文件
- 所有操作都有详细日志记录

## 开发计划

- [x] 基础框架搭建
- [x] 文件扫描模块
- [x] Claude AI集成
- [x] Gradio UI界面
- [x] 文件操作执行
- [x] 错误处理和日志
- [ ] Electron桌面打包
- [ ] 多语言支持
- [ ] 高级规则引擎

## 许可证

MIT License