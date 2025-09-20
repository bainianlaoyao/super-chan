# 终端 UI（Terminal）说明

## 概述

本文档聚焦终端层面的呈现与用户交互职责：渲染会话历史（display pane）、接受并构造输入（input pane），以及将构造好的请求交付给上层路由/执行（通过 IoRouter）。实现细节与数据结构定义请参见 [`docs/ui_internals.md`](docs/ui_internals.md:1)。

## 核心职责（简要）

* terminal ui是一个独立运行的程序, 通过router接口与外部交互
* 集成textual的app来实现程序
* 提供一个start脚本启动程序

- 呈现历史消息与系统输出，支持滚动与长文本处理。
- 提供单一多行输入区以收集用户输入/命令，并按约定构造 InputPayload。
- 支持命令补全、表单式交互（顶层 modal）与非阻塞的自由面板（free panel）。

## 实现变更记录

### 键盘绑定调整（2025-09-20）

**变更背景**：
原始设计中 Enter 键用于发送消息，Ctrl+Enter 用于换行。但在实际使用中，用户发现这种设计不够直观，希望采用更常见的交互模式。

**变更内容**：
- **Enter 键**：在输入框内换行（支持多行输入）
- **Ctrl+Enter**：发送消息/提交请求
- **Ctrl+D / Ctrl+C**：退出应用程序

**实现细节**：
```python
# InputPane.on_key 方法中的键盘处理逻辑
async def on_key(self, event: Any) -> None:
    # Ctrl+Enter 发送消息
    if event.key == "ctrl+enter":
        text = self.input_area.text.strip()
        if text:
            await self.terminal_ui.send_request(InputPayload(...))
            self.input_area.clear()
            event.prevent_default()
    # 普通 Enter 在输入框内换行
    elif event.key == "enter":
        # 让 TextArea 处理换行
        pass  # 不阻止默认行为
```

**影响范围**：
- 更新了用户交互习惯
- 保持了与其他终端应用的兼容性
- 提高了多行输入的便利性

### 模块导入问题修复（2025-09-20）

**问题描述**：
在使用 VS Code 调试器或直接运行 Python 时，出现 "No module named 'superchan'" 错误。

**解决方案**：
在启动脚本中添加项目根目录到 Python 路径：

```python
# scripts/run_terminal_ui.py
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

**支持的运行方式**：
- `python scripts/run_terminal_ui.py` （直接运行）
- `uv run python scripts/run_terminal_ui.py` （通过 uv）
- VS Code 调试器运行
- 其他 Python 环境

### 退出功能完善（2025-09-20）

**问题描述**：
Ctrl+D 退出功能在某些情况下无法正常工作。

**解决方案**：
在 TerminalUI 类中添加明确的键盘绑定：

```python
BINDINGS = [
    Binding("ctrl+d", "quit", "退出"),
    Binding("ctrl+c", "quit", "退出"),
]

async def action_quit(self) -> None:
    """退出应用程序"""
    try:
        self.base.shutdown()
        self.exit()
    except Exception as e:
        logger.exception("退出应用程序失败: %s", e)
        self.exit()
```

**功能验证**：
- ✅ Ctrl+D 正确退出
- ✅ Ctrl+C 正确退出
- ✅ 优雅的资源清理
- ✅ 异常情况下的强制退出

### 错误处理增强（2025-09-20）

**改进内容**：
- 添加了全面的异常捕获和日志记录
- 改进了异步操作的错误处理
- 增加了用户友好的错误提示

**关键改进**：
```python
# 统一的日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 异常处理示例
try:
    # 核心操作
    pass
except Exception as e:
    logger.exception("操作失败: %s", e)
    # 提供用户友好的错误信息
```

## 设计原则

- 命令/协议与载荷签名以 [`docs/ui_internals.md`](docs/ui_internals.md:1) 为准；Terminal UI 不改变底层约定，仅负责呈现与交互。
- 将呈现/交互逻辑与 transport/路由实现解耦；实现细节见内部文档。

## 页面结构与布局（精确定义）

Terminal UI 采用两层结构：

- Base layer（基础层）：display pane（上框）与 input pane（下框），负责主流程的呈现与输入。
- Top layer（顶层）：overlay、modal、free panel 等浮动/顶置组件，负责增强交互，不常驻于基础流程。

职责与交互边界：

- display pane：仅用于渲染历史输出与消息；不直接处理输入事件（由 input pane 接收并发送）。
- input pane：负责收集用户文本、识别命令行并触发补全或命令分支流程。
- top layer：用于临时或富交互（如表单、动画、自由面板）；应明确定义焦点切换与是否阻塞基础层。

布局建议（视觉比例与可配置参数示例）：

- display pane 建议占比：75–85%（示例配置：config.terminal.display_ratio）。
- input pane 建议占比：15–25%（示例配置：config.terminal.input_max_height 或 config.terminal.input_ratio）。
  注：以上为建议比例，实际值应通过可配置参数调整以适配不同终端高度。

## display pane（上框）——渲染与滚动

要点：

- 时间顺序：消息按时间纵向排列，最旧在上、最新在下（最新在下）。
- 支持回溯滚动：用户滚动时暂停自动跟随；用户回到底部或执行“回到底部”操作后恢复自动跟随。
- 消息最小字段：sender、timestamp、content（更详细字段请参见 [`docs/ui_internals.md`](docs/ui_internals.md:1)）。
- 对齐与样式：用户消息右对齐，系统/Agent 输出左对齐；使用差异化样式（颜色/边框/背景）区分。
- 长文本处理：按容器宽度换行；对超长段落提供折叠/展开机制（默认显示前 N 行）。
- 代码块渲染：使用等宽字体、支持横向滚动或折行；若渲染库支持，可启用语法高亮。提供复制提示（视终端能力）。
- 性能：渲染长历史时采用分页或虚拟化（实现细节见内部文档）。

实现/接口细节见 [`docs/ui_internals.md`](docs/ui_internals.md:1)。

## input pane（下框）——输入行为与键位

基本行为：

- 唯一输入组件为多行 textarea（textarea-only）。
- 自动伸缩（auto-resize），在达到最大高度后在内部出现滚动（不延展整个页面）。
- 无提交按钮（纯键盘交互）。

键位与提交规则（明确优先级）：

- **Ctrl+Enter**：提交当前 textarea 内容作为一次 request。提交仅在以下条件满足时发生：补全面板未激活或补全未高亮项，且内容不为空。
- **Enter**：在 textarea 内插入换行，不触发提交（支持多行输入）。
- 以 '/' 行首识别命令（命令检测仅在行首生效）；否则为普通 request。
- 补全交互优先级：补全菜单活跃且项被高亮时，Enter 接受补全（而非直接提交）；在接受补全后按命令元数据分支处理（参见下文）。

**变更说明**：
- 原始设计中 Enter 用于提交，Ctrl+Enter 用于换行
- 实际实现中调整为 Ctrl+Enter 提交，Enter 换行，以提高用户体验
- 这种设计更符合常见的多行文本编辑习惯

InputPayload 构造示例（伪代码，依据内部文档签名）：

```python
# 伪示例：从 input pane 构造 InputPayload（示意，非执行性实现）
from superchan.ui.io_router import InputPayload
import datetime

raw_text = "请列出最近7天活跃用户"
payload = InputPayload(
    type="nl",
    input=raw_text,
    timestamp=datetime.datetime.now(datetime.timezone.utc),
)
# 发送由 UI 层调用：await ui.send_request(payload)
```

实现/接口细节见 [`docs/ui_internals.md`](docs/ui_internals.md:1)。

## 命令元数据 schema（示例字段与含义）

命令元数据用于补全后判定后续流程，以下为建议 schema（示意）：

```python
{
    "name": "string",                     # 命令标识
    "type": "form" | "builtin" | "lightweight",  # 执行分支
    "form_config_path": "optional str",   # 指向 panel 配置（form 类型）
    "config_path": "optional str",        # 兼容别名
    "handler": "optional str",            # 内置/扩展处理器标识
    "ui_hint": {"shape": str, "autoplay": bool, "fps": int, "focus_request": bool},
    "metadata": {}                        # 额外元数据
}
```

说明：字段及语义以 [`docs/ui_internals.md`](docs/ui_internals.md:1) 为准；此处仅供 UI 分支判断与降级参考。

## 命令分支行为（精确流程）

- type == "form"：补全→加载表单配置→在 top layer 打开 modal 表单→用户填写并即时校验→构造 InputPayload 并 await ui.send_request(payload)。
- type == "builtin"：补全→加载元数据→调用本地 handler（例如打开 free panel、播放动画或触发回调）；默认非阻塞底层输入，必要时 handler 可请求以 modal 形式阻塞。
- type == "lightweight"：补全→直接构造并发送轻量级 InputPayload（无需表单）。

示例伪代码：form 流程（示意）：

```python
# 伪代码：form 流程（加载 panel 配置 -> 打开 modal -> 构建 InputPayload 并发送）
panel = load_yaml("config/panels/example_command.yaml")  # 伪函数，详见内部文档
form_values = await ui.open_modal_form(panel)           # 顶层 modal，返回 dict
payload = InputPayload(type="precedure", input=form_values, timestamp=now_utc())
await ui.send_request(payload)
```

示例伪代码：builtin 流程（非阻塞 free panel）：

```python
# 伪代码：builtin handler 打开 free panel 并播放动画（不阻塞 input）
cmd_meta = {"name": "show_mascot", "type": "builtin", "handler": "open_free_panel"}
await ui.invoke_builtin_handler(cmd_meta, context={"trigger": "completion"})
# handler 在顶层创建 free panel 并以异步任务驱动动画，input pane 保持可用
```

键位伪步骤示例（命令补全至表单）：/ex -> 补全弹出 -> ArrowDown -> Enter 接受 -> 打开表单 -> Tab 填写 -> **Ctrl+Enter** 提交。

以上分支与示例均需保持与 [`docs/ui_internals.md`](docs/ui_internals.md:1) 中的类型与签名一致；若发生冲突，以内部文档为准（文中已标注）。

## 表单（modal）规范

- 表单作为顶层 overlay（modal）展示，字段映射由 panel 配置决定（type→控件映射示例：text/number/select/boolean）。
- 字段属性：label、placeholder、required、即时校验规则（基本类型与必填校验）。
- 键盘导航：Tab / Shift+Tab 切换字段，Arrow 键在可选项内导航，**Ctrl+Enter** 在表单未被多行字段占用时可触发提交，Esc 取消并关闭 modal。
- 提交失败行为：展示字段或全局错误信息并返回编辑状态，保留已输入数据以便修正。
- 降级策略：若终端不支持顶层 modal，则降级为在 input pane 提示键值模板或按行内模板填充，并引导用户按提示手动提交（详见“降级与兼容性”）。

实现细节与 panel schema 参见 [`docs/ui_internals.md`](docs/ui_internals.md:1)。

## free panel（自由框）规格

目的与默认行为：

- 用于展示非阻塞的富交互内容（ASCII 动画、状态面板、mascot 等），默认为浮动/非阻塞。
- 支持可拖动、可缩放、最小化/停靠；当需要阻塞交互时应改为 modal 形式。

控制与键位建议：

- 建议快捷键示例：Ctrl+Alt+F 打开/关闭主 free panel；Ctrl+Alt+箭头 移动；Ctrl+Alt+= / Ctrl+Alt+- 调整大小；Tab 在 panel 与 input 之间切换焦点。

数据来源优先级与回退：

- 优先：本地资源（local） > 缓存（cache） > 后端推送（network）。网络失败时回退本地资源或展示占位并异步重试。

动画渲染建议：

- 在独立异步任务中渲染帧，限制帧率（例如 10–15 FPS 默认），避免阻塞主事件循环；采用差分渲染以降低重绘成本。

可访问性与降级：

- 无鼠标环境提供键盘控制；无法渲染时回退为在 display pane 插入状态说明或行内模板提示。

## autocomplete（补全）规范（精炼）

本节定义终端 UI 中补全（autocomplete / completion）行为的规范、优先级、渲染与交互流程，目的是保证在不同终端尺寸、网络/离线场景及存在 ASCII art 窗口（例如 mascot / 艺术字）时，补全行为一致且可预测。请同时参见实现细节文档：[`docs/ui_internals.md`](docs/ui_internals.md:1)。若本节与实现细节冲突，以 [`docs/ui_internals.md`](docs/ui_internals.md:1) 为准。

### 目标

- 快速响应、最小打断：在最少用户等待的前提下展示高质量候选。
- 可预测优先级：一致的源优先级与排序策略。
- 兼容性与降级：在无网络、小屏或 ASCII art 场景下提供合理回退。
- 隐私与限频：保护用户数据并对远端请求做节流与缓存。

---

### 触发（Triggers）

- 自动触发：
  - 默认：字符输入事件后，满足 minChars（默认 2）且 debounce（默认 150–250ms）后触发。
  - 特殊触发器：以特定前缀触发（如 "/"、":"、"@"），按命令 schema 区分。
- 手动触发：
  - 快捷键：Ctrl+Space / Ctrl+I / Meta+Space（可配置）。
  - 显式请求：API 调用 ui.open_completion(panel)。
- 取消触发：
  - 输入退回到低于 minChars、Esc、光标移动到远离触发点。

要点：

- debounce 值可按网络/本地源分别调整（本地即时、远端放宽）。
- 支持显式强制刷新（例如 Shift+Ctrl+R）以跳过缓存。

---

### 数据源与优先级（Data Sources & Priority）

候选项来自多个数据源，合并时遵循以下优先级（高 → 低）：

1. 已加载的本地命令元数据（已缓存的 full-command-meta）
2. 最近/频繁命令历史（local MRU / frequency）
3. builtin / 静态命令列表（本地包中）
4. 插件/扩展提供的本地候选（同步）
5. 远端建议（异步，网络）——加入后可调整排序
6. Lightweight snippets / 小提示

合并策略：

- 先合并本地同步源并立即渲染初始候选（确保极低延迟）。
- 异步源（远端）到达后按评分重新合并并平滑更新面板（避免强制重绘闪烁）。
- 对同一命令的重复候选以最新加载的元数据为准。

---

### 匹配与排序（Matching & Scoring）

匹配策略：

- Tokenize 用户输入（空格、斜杠、驼峰拆分），支持前缀匹配与模糊匹配（默认：prefix 高权重，fuzzy 低权重）。
- 优先考虑命令名称与显式别名，再参考描述与参数名。

评分（score）构成（示例权重）：

- 基础匹配得分（prefix > substring > fuzzy）
- recency_score（最近使用 + 权重）
- frequency_score（使用频率）
- meta_match_boost（命令 meta 明确匹配到参数或标志）
- source_priority_boost（本地缓存/内置 > 插件 > 远端）

合并后按综合得分降序排列。Tie-breaker：更短的 snippet / 更少参数优先。

---

### 候选渲染、键位交互与焦点逻辑（Rendering, Keymap & Focus）

渲染项模板：

- 左侧图标（type：form / builtin / lightweight / plugin）
- 主标题（命令或补全文本）
- 次要信息（短描述、参数摘要）
- 右侧提示（键位提示或状态，如 "needs meta"）

候选面板行为：

- 默认显示：最多 N 行（N 根据可用高度计算，见 ASCII art 节）。
- 支持虚拟滚动（大列表下保持性能）。
- 异步到达新候选采用淡入/微调动画，避免闪烁。

焦点与键位（简洁键位表）：

| 键                | 行为                                                    |
| ----------------- | ------------------------------------------------------- |
| Up / Down         | 上下移动焦点（循环可配置）                              |
| PageUp / PageDown | 翻页                                                    |
| Tab / Shift+Tab   | 接受当前补全并在可插入占位符间跳转（若为 snippet/form） |
| Enter             | 接受所选候选（若无焦点则接受首项）                      |
| Ctrl+Space        | 切换补全面板（打开/关闭）                               |
| Esc               | 关闭补全面板                                            |
| Ctrl+L / Alt+I    | 主动加载命令元数据（若候选标注 "needs meta"）           |
| Ctrl+R            | 强制刷新远端建议（节流）                                |

焦点逻辑要点：

- Keyboard navigation 保持 1:1 对应候选项索引；鼠标移动会改变焦点但不触发 accept。
- 当候选标注需要加载 meta（lazy meta）时，光标停留在该项超过 metaLoadDelay（默认 300ms）可触发异步加载并在加载完成前显示 loading 状态。
- 若使用 Tab 接受并展开 form，光标跳转到第一个可编辑字段。

---

### 接受补全后的流程（Accept Flow）——按 type 分支处理

接受补全步骤（简化）：

1. ui.accept_completion(candidate, ctx)
2. 如果 candidate.meta 未加载，则触发 ui.load_command_meta(candidate)（异步，返回 promise/async）
3. 根据 candidate.type 分支：
   - form：打开命令表单（ui.open_command_form(meta)），填充初始字段并聚焦第一个 field
   - builtin：直接调用执行器（executor.run_builtin(meta / candidate)）
   - lightweight：插入 snippet 文本并把焦点放回输入（支持占位符跳转）
4. 记录 telemetry（本地，不上传敏感输入）

Python 风格伪代码（示意，禁止假设可执行）：

```python
# python
# 伪代码：接受补全（示意）
def on_accept(candidate, input_ctx):
    ui.accept_completion(candidate)  # 视觉上关闭面板或高亮接受动画

    if not candidate.meta_loaded:
        # 异步加载命令元数据（可能来自缓存或网络）
        meta = ui.load_command_meta(candidate.id, timeout=1.5)
    else:
        meta = candidate.meta

    if not meta:
        # 降级：直接插入文本或触发 fallback
        insert_text(candidate.insert_text)
        return

    if meta.type == "form":
        ui.open_command_form(meta, prefill=input_ctx)
    elif meta.type == "builtin":
        executor.run_builtin(meta, context=input_ctx)
    elif meta.type == "lightweight":
        insert_snippet(meta.snippet)
    else:
        insert_text(candidate.insert_text)
```

注意：伪代码中的 API 名称与行为应与实现约定保持一致；如果与 [`docs/ui_internals.md`](docs/ui_internals.md:1) 中描述冲突，请以该内部文档为准。

---

### 降级与兼容性（Fallbacks & Compatibility）

- 离线或网络失败：仅使用本地/缓存候选并把远端请求标注为失败，向 UI 提示“离线模式”或“远端建议不可用”。
- 小屏终端 / 行高度受限：面板自动缩减显示项或改用内联候选（inline suggest）模式。
- 旧终端（无鼠标或无颜色）：降级为简单文本列表，键位仍然可用。
- 插件异常：捕获并隔离插件提供的候选，显示“来自插件的候选（已禁用时隐藏）”。

---

### 缓存、隐私与限频（Cache / Privacy / Rate-limits）

- 缓存层级：
  - session-cache（内存，短期）用于立即响应
  - persistent-cache（磁盘，可选）用于启动加速（敏感数据以用户选择为准）
- 隐私原则：
  - 不上传完整用户输入到远端，远端请求应仅发送 tokenized query（脱敏）或在用户同意下发送完整内容。
  - 本地缓存对敏感参数（如密码）执行模糊化或不缓存。
- 限频策略（远端建议）：
  - 同一查询短期内合并请求（debounce + coalescing）
  - 基于节流（例如每 5s 最多 2 次），并在出现 429/网络错误时指数退避
  - 并发限制：对同一候选的元数据加载并发为 1（队列后续请求）
- 用户控制：提供设置以完全禁用远端建议或持久缓存。

---

### serverchan 的 ASCII art 窗口展示补全（行为规则与实现要点）

当存在 ASCII art 窗口（例如 mascot、艺术字或 logo 占用若干行）时，补全弹窗必须避免覆盖 ASCII art，按下列策略显示补全列表。优先顺序（实现应按此顺序尝试）：

优先顺序：

1. 在 ASCII art 下方扩展窗口高度以插入补全列表（优先）
2. 如果右侧宽度允许，则在 ASCII art 右侧显示补全面板（并行布局）
3. 在 display pane 内行内降级候选（inline suggestions）——最末备选

实现要点：

- 测量 ASCII art 区域高度：
  - ASCII art 区域由 UI 布局组件标识（例如 display pane 中某个 window/region），直接读取该 region 的行数（如果实现层无法直接读取，则以 first_nonempty_line / block detection：自顶向下扫描 display pane 寻找连续非空字符行）。
  - height_art = region.end_row - region.start_row + 1
- 计算可用空间：
  - total_height = terminal.rows
  - above_art = region.start_row - top_region_row
  - below_art = total_height - region.end_row
  - available_right_width = terminal.cols - art_rightmost_col
- 策略判定：
  - 若 below_art >= min_panel_height（例如 5 行），优先在 ASCII art 下方扩展（策略 1）。
  - 否则若 available_right_width >= min_panel_width（例如 30 列），选择右侧显示（策略 2）。
  - 否则进入行内降级（策略 3），显示 1-2 个高优先候选作为 inline suggestions。
- 避免重绘闪烁：
  - 使用双缓冲或 diff 渲染：先计算面板将要绘制的区域与当前屏幕差异，仅重绘变更行/列。
  - 批量更新：合并多次异步候选更新为单次视觉更新（节流渲染，典型 50–100ms）。
  - 渲染事务：在完成布局计算后一次性提交渲染帧。
- 有限终端高度处理（滚动或分页）：
  - 如果在 ASCII art 下方可用高度有限，启用分页（显示页脚 "1/3"）或虚拟滚动（上下键滚动候选）。
  - 在右侧布局时，若右侧高度也不足则回退至内联降级。
- 额外兼容性：
  - 在宽度/高度临界值附近避免频繁切换布局；当窗口尺寸变化超过阈值（如 10%）时才重新评估布局。
  - 为避免与 ASCII art 的动画冲突，优先在 ASCII art 静止时插入面板或与 ASCII art 提供一致的刷新节拍同步。

---

### 典型交互示例（Step-by-step）

示例 1：行首输入 "/ex" -> 补全 -> 接受 -> 展开表单

1. 用户输入 "/ex"（触发器：前缀 "/" + minChars=2）
2. 本地同步源返回候选 ["example", "export"]，渲染初始面板
3. 用户向下选择 "example"（焦点变更）
4. 系统发现 candidate.meta 未加载，停留 300ms 后触发 ui.load_command_meta("example")
5. meta 返回并确定 type="form"，面板显示 "Open form" 状态
6. 用户按 Enter → ui.accept_completion(candidate)
7. ui.open_command_form(meta, prefill) 打开表单，光标聚焦第一字段

示例 2：远端建议到达（异步更新）

1. 初始面板显示本地候选
2. 远端建议到达后以较小动画更新面板（不做完整重绘）
3. 如果新候选得分更高，自动高亮新项（不会改变用户当前键入位置）

示例 3：ASCII art 场景（降级）

1. ASCII art 占用 8 行，下方可用行数为 3（小于 min_panel_height）
2. 右侧可用宽度充足 → 面板在右侧显示
3. 若右侧宽度不足 → 行内降级，仅显示最相关 2 个候选作为 inline suggestions

---

### 伪代码：状态机片段（简洁）

```python
# python
# 补全状态机（简化）
state = "idle"  # idle, querying, showing, loading_meta, accepted, error

def on_input(char):
    if should_trigger(char):
        debounce(trigger_query, 200)  # ms

def trigger_query():
    state = "querying"
    candidates = local_sources.query(input_text)
    ui.render_completion_panel(candidates)
    state = "showing"
    async_fetch(remote_suggestions, on_remote)

def on_remote(remote_candidates):
    merged = merge(candidates, remote_candidates)
    ui.render_completion_panel(merged)  # diff render
    state = "showing"

def on_focus_candidate(cand):
    if cand.needs_meta:
        state = "loading_meta"
        meta = ui.load_command_meta(cand.id, timeout=1500)  # ms
        if meta:
            cand.meta = meta
            ui.render_candidate(cand)
            state = "showing"
        else:
            state = "showing"

def on_accept(cand):
    state = "accepted"
    ui.accept_completion(cand)
    follow_accept_flow(cand)
```

---

### 监控与可配置项（Configurable knobs）

- minChars, debounce_ms, metaLoadDelay_ms, remote_rate_limit, max_panel_height, inline_threshold
- 开关：enable_remote_suggestions, enable_persistent_cache, ascii_art_strategy_preference

---

附：参考文件

- 当前被替换节位于 [`docs/terminal_ui.md`](docs/terminal_ui.md:1)
- 实现内部约定：[`docs/ui_internals.md`](docs/ui_internals.md:1)

## 降级、兼容性与隐私说明

降级路径（总结）：

- 受限终端（无 overlay/无鼠标）：overlay 降级为行内提示或 display pane 中的静态文本；表单降级为模板提示或按行交互；free panel 降级为状态说明或本地替代资源。
- 补全/元数据从后端拉取失败时：回退本地缓存→若无缓存则按 lightweight 路径发送文本请求。

隐私/频率建议：

- 建议对远端元数据采用缓存 TTL（例如 5–60 分钟，依数据敏感度调整）并限频请求；对敏感上下文避免在补全请求中发送完整输入。

实现/接口细节见 [`docs/ui_internals.md`](docs/ui_internals.md:1)。

## 已同步的函数与参数清单（概要）

下列签名与字段为关键契约概要；具体定义以 [`docs/ui_internals.md`](docs/ui_internals.md:1) 为准。

- send_request 签名（UI/IoRouter）：async def send_request(self, request: InputPayload) -> None
- register_callback / unregister_callback（IoRouter）：
  - def register_callback(self, callback: CallbackType) -> str
  - def unregister_callback(self, callback_id: str) -> None
- InputPayload（主要字段）：type: "precedure" | "nl"，input: str | dict，timestamp: datetime | None，metadata: dict
- OutputPayload（主要字段）：text: str，timestamp: datetime | None，metadata: dict
  注：字段字面值与行为细节请以 [`docs/ui_internals.md`](docs/ui_internals.md:1) 为准；若出现不一致，以内部文档为准。

## 改进建议（按优先级）

1. 建议（高优先级）：把命令元数据 schema 提取为独立的 JSON Schema 文件并放在仓库中，便于校验与自动生成表单。预期收益：减少 schema 不一致，支持自动化校验与工具集成。
2. 建议（中优先级）：为补全维护本地倒排索引并周期性与后端同步，降低补全延迟并提高离线可用性。预期收益：显著提升补全响应速度与用户体验。
3. 建议（中优先级）：将 free panel 的动画渲染抽象为独立渲染任务/服务（异步任务或子进程），以免阻塞 UI 主循环。预期收益：降低卡顿与 CPU 峰值，提升稳定性。
4. 建议（低优先级）：增加可配置化的主题与颜色变量（config.theme.*），以便在不同终端主题/可访问性需求下适配显示。预期收益：改善可用性与视觉一致性。

## 参考与备注

- 本文仅包含与终端呈现与交互直接相关的信息；实现细节、精确类型与序列化约定请参见并遵循 [`docs/ui_internals.md`](docs/ui_internals.md:1) 与源码：[`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)、[`superchan/ui/base_ui.py`](superchan/ui/base_ui.py:1)。
- 文中所有伪代码为示意，禁止将其作为可直接执行的实现。

[`docs/terminal_ui.md`](docs/terminal_ui.md:1)
