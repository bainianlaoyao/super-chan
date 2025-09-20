# SuperChan

SuperChan 是一个基于终端的用户界面应用程序，提供丰富的交互体验。

## 功能特性

- **终端用户界面**: 基于 Textual 框架的现代化终端 UI
- **消息显示**: 支持历史消息显示和滚动
- **多行输入**: 支持多行文本输入和命令补全
- **命令系统**: 以 `/` 开头的命令支持自动补全
- **表单交互**: 支持动态表单生成和数据收集
- **键盘导航**: 完整的键盘快捷键支持

## 安装

确保你有 Python 3.13+ 和 uv 包管理器：

```bash
# 安装依赖
uv sync
```

## 运行

### 方法 1: 使用启动脚本

```bash
uv run python scripts/run_terminal_ui.py
```

### 方法 2: 直接运行模块

```bash
uv run python superchan/ui/terminal/terminal_ui.py
```

### 方法 3: 作为 Python 模块

```bash
uv run python -c "import asyncio; from superchan.ui.terminal.terminal_ui import main; asyncio.run(main())"
```

## 使用说明

### 基本操作

- **输入消息**: 在底部输入框中输入文本，按 **Ctrl+Enter** 发送
- **多行输入**: 使用 **Enter** 在输入框内换行
- **退出程序**: 按 Ctrl+D 或 Ctrl+C 退出

### 命令系统

- **命令前缀**: 以 `/` 开头输入命令
- **自动补全**: 输入 `/` 后会显示可用的命令列表
- **键盘导航**: 使用上下箭头键选择命令，Enter 确认

### 可用命令

- `/help` - 显示帮助信息
- `/example` - 示例命令
- `/quit` - 退出程序

## 架构说明

### 核心组件

- **TerminalUI**: 主应用程序类，基于 Textual App
- **IoRouter**: IO 路由器，负责请求发送和响应分发
- **BaseUI**: 基础 UI 接口，提供统一的回调机制
- **DisplayPane**: 消息显示面板
- **InputPane**: 输入面板，支持多行输入和命令补全

### 数据流

1. 用户在 InputPane 中输入文本
2. InputPane 将输入构造为 InputPayload
3. 通过 IoRouter 发送到后端处理
4. 后端返回 OutputPayload
5. IoRouter 分发到所有注册的回调
6. TerminalUI 接收并在 DisplayPane 中显示

## 实现变更记录

### 键盘绑定调整（2025-09-20）

**变更说明**：
- **Ctrl+Enter**: 发送消息/提交请求
- **Enter**: 在输入框内换行（支持多行输入）
- **Ctrl+D / Ctrl+C**: 退出应用程序

**变更原因**：
原始设计中 Enter 用于发送消息，但实际使用中发现这种设计不够直观。经过用户反馈，将键盘绑定调整为更常见的交互模式，提高了多行输入的便利性。

### 兼容性改进（2025-09-20）

**模块导入修复**：
修复了在不同 Python 环境中运行时的模块导入问题，现在支持：
- 直接运行 `python scripts/run_terminal_ui.py`
- 通过 uv 运行 `uv run python scripts/run_terminal_ui.py`
- VS Code 调试器运行
- 其他 Python 环境

**退出功能完善**：
确保 Ctrl+D 和 Ctrl+C 能正确退出程序，包括优雅的资源清理和异常情况下的强制退出。

## 开发

### 项目结构

```
superchan/
├── ui/
│   ├── terminal/
│   │   └── terminal_ui.py    # 终端 UI 实现
│   ├── io_router.py          # IO 路由器
│   ├── io_payload.py         # 数据载荷定义
│   └── base_ui.py           # 基础 UI 接口
├── config/
│   └── panels/              # 表单配置
└── scripts/
    └── run_terminal_ui.py   # 启动脚本
```

### 代码规范

项目遵循以下规范：

- **Python 版本**: 3.13+
- **类型提示**: 强制使用类型注解
- **错误处理**: 禁止静默失败，必须记录异常
- **日志**: 使用标准 logging 模块
- **格式化**: 使用 black 代码格式化

## 许可证

[请添加许可证信息]
