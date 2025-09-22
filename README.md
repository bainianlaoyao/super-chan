# Super Chan

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Super Chan 是一个基于Python的异步AI助手平台，采用分层架构设计，提供现代化的终端用户界面体验。支持邮件处理、动漫风格化等功能，并具备强大的插件扩展能力。

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [安装](#安装)
- [快速开始](#快速开始)
- [用法](#用法)
- [架构](#架构)
- [当前进度](#当前进度)
- [贡献](#贡献)
- [许可证](#许可证)

## 功能特性

- **终端用户界面**: 基于 Textual 框架的现代化终端 UI，支持历史消息显示和滚动
- **多行输入与命令补全**: 支持多行文本输入、以 `/` 开头的命令自动补全
- **表单交互**: 动态表单生成和数据收集，支持键盘导航和快捷键
- **邮件处理**: 集成 Outlook 获取器和 LLM 总结器，支持邮件获取和内容总结
- **动漫风格化**: LLM 驱动的文本转二次元风格转换
- **推送通知**: 支持 ServerChan 等推送服务
- **插件系统**: 可扩展的插件架构，支持自定义功能模块
- **异步架构**: 基于 asyncio 的高性能异步处理

## 技术栈

- **Python 3.13+**: 核心编程语言
- **uv**: 快速的 Python 包安装器和虚拟环境管理器
- **Textual**: 现代终端用户界面框架
- **Pydantic**: 数据验证和设置管理
- **其他依赖**:
  - Outlook 库 (邮件处理)
  - ServerChan SDK (推送通知)
  - ZAI SDK (AI服务集成)

## 安装

### 系统要求

- Python 3.13 或更高版本
- uv 包管理器

### 安装 uv

```bash
# 使用官方安装脚本（适用于多种操作系统）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或者使用 pip 安装
pip install uv
```

### 安装项目

```bash
# 克隆项目
git clone https://github.com/your-username/superchan.git
cd superchan

# 安装依赖
uv sync
```

## 快速开始

1. **配置环境**: 编辑 `config/user.toml` 文件配置你的设置
2. **启动应用**: 运行终端界面

```bash
uv run python scripts/run_terminal_ui.py
```

3. **开始使用**: 在终端中输入命令或消息开始交互

## 用法

### 基本操作

- **发送消息**: 在输入框中输入文本，按 `Ctrl+Enter` 发送
- **多行输入**: 按 `Enter` 在输入框内换行
- **退出程序**: 按 `Ctrl+D` 或 `Ctrl+C`
- **命令面板**: 按 `ctrl+p`唤起命令面板, 调用命令

### 高级功能

- **邮件处理**: 使用内置程序处理邮件总结
- **动漫风格化**: 将文本转换为二次元风格
- **推送通知**: 配置推送服务接收通知

## 架构

项目采用分层架构设计，主要分为四个层次：

### 核心层 (Core)

- **引擎 (Engine)**: 业务逻辑调度和执行
- **传输 (Transport)**: 数据传输机制
- **执行器 (Executors)**: 任务执行管理

### UI层 (UI)

- **终端UI**: Textual 框架实现的终端界面
- **推送UI**: ServerChan 等推送服务集成
- **IO路由器**: 消息路由和回调管理
- **数据载荷**: InputPayload 和 OutputPayload 规范

### 超级程序层 (Super Program)

- **邮件模块**: Outlook 邮件获取、LLM 内容总结
- **动漫模块**: 文本风格化转换

### 工具层 (Utils)

- **配置管理**: TOML 配置文件处理
- **LLM提供者**: AI 服务接口封装
- **过程注册**: 动态过程注册机制

## 当前进度

### ✅ 已完成功能

- **核心架构**: 引擎、传输、执行器等核心组件稳定运行
- **邮件模块**: 邮件获取、内容总结功能完整
- **动漫模块**: LLM 风格化功能实现
- **UI系统**: 终端UI 和推送UI 支持多种交互模式

### 🚧 进行中

- **数据库集成**: 完善数据持久化机制
- **插件系统**: 扩展更多插件类型和配置

### 📋 未来计划

- **插件扩展**: 天气查询、新闻推送、任务管理等插件
- **UI优化**: 提升交互体验和视觉效果
- **性能优化**: 算法优化和资源利用率提升

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发设置

```bash
# 安装开发依赖
uv sync --dev

# 运行测试
uv run pytest

# 代码格式化
uv run black .
```

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
