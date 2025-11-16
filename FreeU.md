# FreeU 项目规格说明

## 1. 项目概述

### 1.1 项目目标
FreeU 是一个基于 Claude AI 的本地文件整理助手，旨在让普通用户（非程序员）通过自然语言指令轻松整理本地文件系统。

### 1.2 用户问题与痛点
- **目标用户**：非技术用户，不熟悉命令行操作
- **核心痛点**：
  - 桌面/下载文件夹杂乱无章，手动整理耗时费力
  - 不知道如何按规则批量分类文件
  - 担心误操作删除重要文件
  - 现有工具要么过于复杂，要么自动化程度不够

### 1.3 解决方案
提供一个本地桌面应用，用户输入自然语言指令（如"把图片放到 Pictures，文档放到 Docs"），AI 生成整理方案供预览，用户确认后执行。

---

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────────────────────────────┐
│     Electron 桌面应用（外壳）            │
│  ┌───────────────────────────────────┐  │
│  │   Gradio Web UI (localhost:7860)  │  │
│  └───────────────┬───────────────────┘  │
│                  │ HTTP                  │
│  ┌───────────────▼───────────────────┐  │
│  │   Python 后端 (Flask/FastAPI)     │  │
│  │   - 文件扫描 (pathlib)            │  │
│  │   - Claude SDK 调用               │  │
│  │   - 文件操作执行                  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 2.2 技术栈
- **前端**：Gradio（快速构建 Web UI）
- **后端**：Python 3.9+
  - `anthropic`（Claude SDK）
  - `pathlib`（文件系统操作）
  - `pydantic`（数据验证）
- **桌面打包**：Electron
- **日志**：Python `logging` 模块

### 2.3 运行模式
- 本地单机应用，无需联网（除了调用 Claude API）
- 所有文件操作限定在本机文件系统
- 数据不上传云端

---

## 3. 核心流程（感知 → 规划 → 执行）

### 3.1 感知阶段（Computer Use - 环境读取）
**输入**：
- 用户自然语言指令（文本框输入）
- 目标目录路径（路径输入框 + 浏览按钮）

**处理**：
- 使用 `pathlib.Path().iterdir()` 扫描目录
- 收集文件元信息：
  - 文件名
  - 扩展名
  - 文件大小
  - 修改时间
  - 相对路径

**输出**：
- 结构化文件列表（JSON 格式）

### 3.2 规划阶段（Agentic AI - 行动计划生成）
**输入**：
- 用户指令
- 文件列表
- 历史上下文（可选，前几轮交互）

**处理**：
- 构造 Claude API 请求：
  ```json
  {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "system": "<system_prompt>",
    "messages": [
      {
        "role": "user",
        "content": "<instruction + files>"
      }
    ]
  }
  ```

- System Prompt 包含：
  - 角色定义：本地文件整理助手
  - 输出格式：严格的 JSON schema
  - 允许的操作类型（MVP：move）
  - Few-shot 示例（3-5 个典型场景）

**输出格式**（严格 JSON）：
```json
{
  "actions": [
    {
      "action_type": "move",
      "source": "file1.jpg",
      "destination": "Pictures/file1.jpg",
      "reason": "图片文件移动到 Pictures 文件夹"
    }
  ]
}
```

**错误处理**：
- JSON 解析失败 → 提示用户，记录日志
- Schema 验证失败 → 重试或人工干预
- 模型输出为空 → 提示"未找到可整理的文件"

### 3.3 执行阶段（Computer Use - 工具调用）
**预览机制**：
- 在 Gradio 表格组件展示 actions 列表
- 显示：源文件 | 目标路径 | 操作类型 | 原因
- 默认不执行，等待用户确认

**执行逻辑**：
- 用户点击「确认执行」按钮
- 后端逐条执行 actions：
  ```python
  for action in actions:
      source_path = base_dir / action["source"]
      dest_path = base_dir / action["destination"]
      dest_path.parent.mkdir(parents=True, exist_ok=True)
      source_path.rename(dest_path)
  ```

**结果反馈**：
- 成功列表：已移动的文件
- 失败列表：失败原因（文件不存在、权限不足等）
- 日志输出到前端日志区域

---

## 4. Context Engineering 设计

### 4.1 System Prompt 结构
```
你是 FreeU 文件整理助手，负责根据用户指令生成文件整理方案。

【角色定义】
- 只处理本地文件整理任务
- 输出必须是严格的 JSON 格式
- 不执行删除操作（MVP 阶段）

【输出格式】
{
  "actions": [
    {
      "action_type": "move",
      "source": "相对路径",
      "destination": "目标相对路径",
      "reason": "简短说明"
    }
  ]
}

【Few-shot 示例】
示例 1：
用户指令："把所有图片放到 Pictures 文件夹"
文件列表：["photo.jpg", "document.pdf", "screenshot.png"]
输出：
{
  "actions": [
    {"action_type": "move", "source": "photo.jpg", "destination": "Pictures/photo.jpg", "reason": "图片文件"},
    {"action_type": "move", "source": "screenshot.png", "destination": "Pictures/screenshot.png", "reason": "图片文件"}
  ]
}

[更多示例...]

【注意事项】
- 不要移动隐藏文件（以 . 开头）
- 不要移动系统文件
- 目标路径必须在指定目录下
```

### 4.2 Few-shot 示例场景
1. 按文件类型分类（图片、文档、视频）
2. 按日期整理（年/月文件夹）
3. 按文件名模式分类（工作、个人等）
4. 清理重复文件（TODO：未来功能）

### 4.3 上下文管理
- 保留最近 3 轮交互历史
- 格式：`[指令 → 计划 → 执行结果]`
- 用于支持多轮对话式整理

---

## 5. 前端交互设计（Gradio）

### 5.1 界面布局
```
┌────────────────────────────────────────┐
│          FreeU 文件整理助手             │
├────────────────────────────────────────┤
│ 目标目录：[/Users/dave/Desktop  ] [📁] │
│                                        │
│ 整理指令：                              │
│ ┌────────────────────────────────────┐ │
│ │ 把图片放到 Pictures，文档放到 Docs  │ │
│ └────────────────────────────────────┘ │
│                                        │
│         [生成整理方案] [清除历史]       │
├────────────────────────────────────────┤
│ 整理方案预览：                          │
│ ┌────────────────────────────────────┐ │
│ │ 源文件      | 目标路径    | 原因   │ │
│ │ photo.jpg  | Pictures/.. | 图片   │ │
│ │ doc.pdf    | Docs/..     | 文档   │ │
│ └────────────────────────────────────┘ │
│                                        │
│              [确认执行] [取消]          │
├────────────────────────────────────────┤
│ 执行日志：                              │
│ ┌────────────────────────────────────┐ │
│ │ ✓ photo.jpg → Pictures/photo.jpg  │ │
│ │ ✓ doc.pdf → Docs/doc.pdf          │ │
│ │ ✗ file.txt 不存在                  │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### 5.2 组件说明
- **目标目录输入**：`gr.Textbox()` + `gr.Button("📁")` 触发文件夹选择器
- **整理指令**：`gr.Textbox(lines=3, placeholder="例如：把图片放到 Pictures")`
- **方案预览**：`gr.Dataframe()` 展示 actions
- **执行日志**：`gr.Textbox(lines=10, interactive=False)` 实时输出

### 5.3 交互流程
1. 用户选择目录 + 输入指令 → 点击「生成整理方案」
2. 后端扫描 + 调用 Claude → 返回 actions
3. 前端展示预览表格
4. 用户检查方案 → 点击「确认执行」
5. 后端执行 → 实时更新日志区域

---

## 6. 安全与限制

### 6.1 路径安全
- **白名单机制**：只允许操作用户明确指定的目录及其子目录
- **黑名单机制**：禁止操作以下路径：
  - 系统目录：`/System`, `/Library`, `/usr`, `/bin`, `/etc`
  - 用户关键目录：`~/.ssh`, `~/.config`
  - 应用程序目录：`/Applications`

### 6.2 文件操作限制
- MVP 阶段只支持 `move` 操作
- 不支持删除（`delete`）
- 不支持重命名跨目录的文件
- 自动跳过隐藏文件（以 `.` 开头）

### 6.3 权限检查
- 执行前检查源文件是否存在
- 检查目标目录是否有写权限
- 检查是否会覆盖现有文件（如有冲突，自动重命名或提示）

### 6.4 错误处理
- 文件不存在 → 跳过，记录日志
- 权限不足 → 跳过，提示用户
- JSON 解析失败 → 重试 1 次，失败则提示
- Claude API 调用失败 → 显示错误信息，不执行任何操作

---

## 7. 日志设计

### 7.1 日志规范
- 使用 Python `logging` 模块
- 日志文件路径：`./logs/freeu.log`
- 日志格式：
  ```
  [时间] [级别] [函数名] 消息内容
  ```

### 7.2 日志级别
- `INFO`：正常操作（扫描文件、生成方案、执行成功）
- `WARNING`：跳过的文件、权限问题
- `ERROR`：API 调用失败、JSON 解析失败
- `DEBUG`：详细的中间数据（开发模式）

### 7.3 关键日志点
- `scan_directory()` 开始/完成
- `call_claude_api()` 请求/响应
- `execute_actions()` 每个文件操作的结果

### 7.4 进度显示
对于批量操作，日志添加进度标记：
```
- [开始] 扫描目录 /Users/dave/Desktop
+ [完成] 扫描到 50 个文件

- [开始] 执行文件移动 (1/50)
+ [完成] photo.jpg → Pictures/photo.jpg
! [异常] file.txt 权限不足，跳过
```

---

## 8. 桌面应用打包（Electron）

### 8.1 Electron 结构
```
freeu-app/
├── main.js           # Electron 主进程
├── preload.js        # 预加载脚本
├── renderer/         # 渲染进程（可选，Gradio 自带 UI）
├── python_backend/   # Python 后端（打包）
│   ├── app.py
│   ├── requirements.txt
│   └── ...
└── package.json
```

### 8.2 启动流程
1. Electron 主进程启动
2. 检查 Python 环境（内置 Python 或调用系统 Python）
3. 启动 Python 后端（Gradio 服务，监听 localhost:7860）
4. Electron 窗口加载 `http://localhost:7860`
5. 用户交互通过 Gradio UI

### 8.3 打包方案
- **开发模式**：用户需要安装 Python + 依赖
- **生产模式**：
  - 使用 PyInstaller 将 Python 后端打包成可执行文件
  - Electron 调用打包后的可执行文件
  - 最终产物：`.app`（macOS）/ `.exe`（Windows）

### 8.4 配置文件
- Claude API Key 存储在本地配置文件：`~/.freeu/config.json`
- 首次启动时提示用户输入 API Key

---

## 9. 成功标准

### 9.1 MVP 阶段（第一版）
- [ ] 用户可以通过桌面应用启动 FreeU（无需命令行）
- [ ] 可以选择目录并输入自然语言指令
- [ ] AI 生成整理方案并展示预览
- [ ] 用户确认后正确执行文件移动
- [ ] 日志清晰展示执行结果
- [ ] 支持 macOS 打包（.app）

### 9.2 用户体验指标
- 从启动到生成方案：< 5 秒（假设网络正常）
- 方案准确率：> 90%（符合用户意图）
- 零学习成本：非技术用户 5 分钟内上手

### 9.3 技术指标
- 支持目录文件数：< 1000（超过则提示分批处理）
- Claude API 调用超时：10 秒
- 文件操作失败率：< 5%（正常情况下）

---

## 10. 超出范围（暂不实现）

### 10.1 MVP 阶段不包含
- ❌ 删除文件功能
- ❌ 批量重命名
- ❌ 重复文件检测与清理
- ❌ 文件内容分析（OCR、文本提取）
- ❌ 云端同步
- ❌ 多用户/权限管理
- ❌ 插件系统

### 10.2 后续迭代可考虑
- 定时自动整理
- 整理规则保存与复用
- 撤销（Undo）功能
- 文件预览（图片、文档）
- Windows/Linux 支持

---

## 11. 待澄清问题

### 11.1 用户场景
- [ ] 用户的典型使用场景是什么？（桌面整理、下载文件夹、项目文件？）
- [ ] 预期每次整理的文件数量级？（几十、几百、上千？）
- [ ] 是否需要支持递归扫描子文件夹？

### 11.2 Claude API
- [ ] 用户是否已有 Claude API Key？
- [ ] 是否可以使用 OpenAI API 作为备选？
- [ ] API 调用成本是否有预算限制？

### 11.3 功能优先级
- [ ] 是否需要支持多轮对话式整理？（例如："再把 PDF 放到 Documents/Work"）
- [ ] 是否需要支持自定义整理规则模板？
- [ ] 是否需要查看操作历史记录？

### 11.4 安全与隐私
- [ ] 是否需要在调用 Claude 前对文件名进行脱敏？（防止泄露敏感信息）
- [ ] 是否需要支持离线模式？（使用本地小模型）

### 11.5 用户体验
- [ ] 是否需要中英文双语支持？
- [ ] 是否需要暗色主题？
- [ ] 是否需要文件操作动画/进度条？

### 11.6 技术细节
- [ ] Python 版本要求？（3.9+? 3.10+?）
- [ ] 是否需要支持 Windows/Linux？（还是只需 macOS？）
- [ ] Electron 打包后的应用大小是否有限制？

---

## 12. 项目里程碑

### Phase 1：基础框架（1-2 天）
- 搭建项目结构
- 实现文件扫描模块
- 集成 Claude SDK
- 基础 Gradio UI

### Phase 2：核心功能（2-3 天）
- Context Engineering（System Prompt + Few-shot）
- 方案生成与预览
- 文件移动执行
- 错误处理与日志

### Phase 3：桌面打包（2-3 天）
- Electron 集成
- Python 后端打包（PyInstaller）
- macOS .app 构建
- 启动流程优化

### Phase 4：测试与优化（1-2 天）
- 功能测试
- 用户体验优化
- 文档编写（用户手册）

**总计：6-10 天**

---

## 13. 附录

### 13.1 参考资料
- [Claude Agent SDK 官方文档](https://docs.claude.com/zh-CN/api/agent-sdk/overview)
- [Gradio 官方文档](https://www.gradio.app/docs/)
- [Electron 官方文档](https://www.electronjs.org/docs/latest/)

### 13.2 相关技术
- Python `pathlib`：文件系统操作
- Python `logging`：日志管理
- `pydantic`：数据验证
- `anthropic` SDK：Claude API 调用

---

**文档版本**：v1.0  
**创建日期**：2025-11-16  
**作者**：AI Assistant  
**状态**：草稿 - 待审核

