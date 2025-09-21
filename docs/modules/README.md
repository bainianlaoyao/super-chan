# 文档模块组织

本目录包含Super-Chan项目的模块化文档，按功能领域组织，结构与源码目录保持一致：

## 模块列表

### 核心架构 (core/)
- [架构设计](core/architecture.md) - 项目目标、整体架构、核心理念、关键决策、系统特性、里程碑等

### UI系统 (ui/)
- [BaseUI抽象基类](ui/base_ui.md) - UI基础接口和生命周期管理
- [数据载荷设计](ui/io_payload.md) - InputPayload和OutputPayload规范
- [IoRouter消息路由](ui/io_router.md) - 消息路由和回调管理机制

#### 终端UI实现 (ui/terminal/)
- [TerminalUI实现](ui/terminal/terminal_ui.md) - 终端UI架构和组件设计
- [CommandProvider](ui/terminal/command_provider.md) - 命令提供者和表单系统

### 命令系统 (command/)
- [命令系统设计](command/commands.md) - 命令元数据、表单Schema、自动补全

### 扩展性设计 (extensibility/)
- [扩展性设计](extensibility/design.md) - 插件系统和工具箱设计

### 风格设计 (style/)
- [二次元风格](style/anime.md) - 二次元风格设计

## 文档重组说明

原始文档已按模块重新组织，每个模块都有更细粒度的介绍和设计，但未新增任何内容，只是进行了拆分重组以提高可读性和维护性。文档结构与源码目录结构保持一致，便于开发者快速定位相关文档。