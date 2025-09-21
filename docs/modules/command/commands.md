# 命令系统模块

## 命令元数据与表单 Schema 设计

简短定位：本文件为 Terminal UI（server-chan）中的命令元数据（command metadata）与表单型命令（form commands）输入数据的规范设计。它用于指导开发者实现或生成 machine-readable 的 JSON Schema，并说明自动补全（autocomplete）在存在 ASCII art 窗口时的交互行为与降级方案。与内部 UI 类型/签名的对齐请参考 [`docs/ui_internals.md`](docs/ui_internals.md:1)（备注：若本文与内部文档有差异，以内部文档为准，且在差异处标注"依据内部文档"）。

## 一. 概要与范围

- 适用范围：描述面板级别的 command 元数据（用于注册、显示、触发）与 form 类型命令的 InputPayload 子集 schema。
- 目的：便于生成 JSON Schema、前端表单渲染、校验、以及自动补全子系统实现。

## 二. Command metadata JSON Schema（概念性定义）

说明：下面给出命令元数据的 JSON Schema（示意）。该 schema 必须严格说明字段、类型、必填项与含义，便于直接转换为 machine-readable JSON Schema。

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CommandMetadata",
  "type": "object",
  "required": ["id", "type", "title"],
  "properties": {
    "id": { "type": "string", "description": "命令唯一标识，建议使用短蛇形（slug）" },
    "type": { "type": "string", "enum": ["action", "form", "query"], "description": "命令类别；form 表示表单型命令" },
    "title": { "type": "string", "description": "命令显示名称" },
    "description": { "type": "string", "description": "可选的长描述，供 UI tooltip/详情使用" },
    "icon": { "type": "string", "description": "可选，图标标识（可为 emoji 或 class 名称）" },
    "category": { "type": "string", "description": "可选，命令分类（用于分组展示）" },
    "priority": { "type": "integer", "minimum": 0, "description": "可选，命令排序优先级，越小越靠前" },
    "formSchema": { "type": ["object","null"], "description": "当 type==='form' 时，表示表单字段定义（参见下文 Form data schema）" },
    "autocomplete": {
      "type": ["object","boolean"],
      "description": "自动补全配置；true 使用默认策略，object 为详细配置"
    },
    "hidden": { "type": "boolean", "description": "是否隐藏于通用命令列表（默认 false）" },
    "meta": { "type": "object", "additionalProperties": true, "description": "扩展字段，供插件或后端使用" }
  },
  "additionalProperties": false
}
```

说明要点：
- id、type、title 为必须字段。
- formSchema 在非 form 类型下可为 null 或缺省。
- autocomplete 支持布尔或对象；对象形态允许覆盖数据源与缓存策略等。

## 三. 表单型命令的数据 Schema（form data schema / InputPayload 子集）

目标：指定表单字段集合的精确结构，用于前端渲染、校验与提交。以下为概念性 JSON Schema（示意）与字段说明。

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CommandFormSchema",
  "type": "object",
  "required": ["fields"],
  "properties": {
    "fields": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "type", "label"],
        "properties": {
          "name": { "type": "string", "description": "字段键，提交时的属性名" },
          "type": { "type": "string", "enum": ["text","number","select","boolean"], "description": "字段类型" },
          "label": { "type": "string", "description": "表单标签" },
          "placeholder": { "type": ["string","null"], "description": "占位文本" },
          "required": { "type": "boolean", "description": "是否必填" },
          "default": { "description": "默认值，类型依赖于 type" },
          "options": {
            "type": ["array","null"],
            "items": { "type": "object", "required": ["value","label"], "properties": { "value": {}, "label": { "type": "string" } } },
            "description": "当 type==='select' 时使用的选项数组"
          },
          "validation": {
            "type": "object",
            "description": "可选的校验规则（例如 min/max/regex 等）",
            "additionalProperties": true
          },
          "ui": {
            "type": "object",
            "description": "UI 渲染提示（如宽度、行数、multiline 等），非必需",
            "additionalProperties": true
          }
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}
```

字段含义与校验建议：
- name：仅允许字母数字、下划线与短横，作为后端接收键（建议正则 ^[a-zA-Z0-9_-]+$）。
- type：目前支持 text、number、select、boolean。扩展类型需同时更新前端渲染器。
- placeholder：仅用于提示，不作为校验值。
- required：若为 true，前端应在提交前阻止空值，后端必须再次校验。
- default：当用户未修改时作为提交值；对 number 类型建议显式为数值。
- options：select 必须提供至少一个选项；每个 option 的 value 应与最终提交值类型一致。
- validation：建议定义常用规则，例如 number 的 min/max，text 的 regex 与 maxLength。

与 `docs/ui_internals.md` 的对齐：
- 本节的字段签名与渲染约定应参考并以 [`docs/ui_internals.md`](docs/ui_internals.md:1) 为准（依据内部文档）。若内部文档中对某些 ui.ui-field 的命名或类型有不同，优先遵循内部文档并在此处注明具体差异。

## 四. 自动补全（Autocomplete）行为设计

目标：定义自动补全触发条件、数据源优先级、本地缓存策略、候选交互与排序规则，以及降级行为。

1) 触发条件
- 基础触发：用户在命令输入区域中输入至少 1 个字符后开始触发（可配置 threshold）。
- 特殊触发：按键触发（如 Ctrl+Space 或 Tab）应强制显示补全。
- 表单字段内触发：在表单的文本字段或可补全 select 中，应按字段类型启用独立补全逻辑。

2) 数据源与优先级（从高到低）
- 当前 panel 的本地静态 options（表单配置中的 options 字段）。
- 本地缓存（最近使用/历史输入，TTL 参见下文）。
- 本地索引/内置词表（应用内固定词库）。
- 后端/远程 API（实时查询）。

优先级说明：优先使用本地可得数据以降低延迟并保护隐私；仅在本地无匹配时或按需（如用户显式请求更多）才查询远端。

3) 本地缓存策略
- 缓存项结构：{ key, value, source, timestamp }。
- TTL 建议：默认 5 分钟（300 秒），对隐私敏感的条目可将 TTL 设为 0（不缓存）。
- 容量限制：默认最近 200 条，采用 LRU 策略回收。
- 隐私控制：允许命令声明 "cache": false 或 "cacheTTL": 0。

4) 候选交互与 snippet-like 参数占位
- 候选项可包含显示 label、value、description 与 snippet 字段。
- snippet 支持参数占位（如 ${1:arg}、${2:opt} 风格），用于在选中后快速填写到输入框或表单字段。
- 对于表单中的多个字段，选中一个候选可以触发填充其它相关字段（通过返回一组字段映射）。

5) 排序规则
- 相关性评分：基础为前缀匹配得高分，包含匹配次之，fuzzy 匹配为最低分。
- 使用频率加权：近期使用或常用选项应提升权重（结合本地历史）。
- 命令/字段优先级权重：metadata.priority 可作为最终排名的加权因子。

6) 降级策略
- 当无法访问远端 API 或 terminal/环境受限时，退回到本地缓存、本地静态 options 或内置词表。
- 在极端受限（无法打开额外 UI 空间）时，使用行内候选或状态栏提示（见下文 ASCII art 交互段落）。

## 五. Autocomplete 与 ASCII art 窗口交互

目标：在存在 ASCII art free panel（如 server-chan 的 ASCII art 窗口）时，自动补全 UI 不覆盖该面板，而是扩展或分配额外顶层空间；同时提供在受限终端下的降级方案。

1) UI 行为原则（必须遵守）
- 补全窗口绝对不覆盖已有的 ASCII art 面板像素。展示时应"扩展/分配窗口空间"：
  - 若终端/布局支持多列或浮层，则在 ASCII art 所在面板的右侧分配一个补全列（suggestion column），固定宽度或按候选最长宽度自适应。
  - 若无法右侧扩展，则在 ASCII art 上方或下方在顶层创建一条行内 suggestion 区（top-layer inline suggestions），通过占用额外行数扩展整体面板高度，使 ASCII art 原内容保持完整且相对位置不变。
- 展示行为示例：当补全激活，UI 分配 10 行 suggestion 区在 ASCII art 下方显示；ASCII art 面板继续完整渲染并保持可见，仅整体视窗高度变化。

2) 焦点与键位管理
- 补全列表激活时，键盘焦点默认落在补全列表（上下键选择，Enter 确认，Esc 取消）。
- Tab 键用于在输入框与补全列表之间切换焦点（Shift+Tab 反向）。
- 当补全列表关闭或取消时，焦点回到原输入控件，ASCII art 面板继续接收鼠标/滚动事件。
- 建议实现：使用明确的 focus stack，记录 focus 来源控件，以便恢复。

3) 降级方案（受限终端）
- 若终端或环境无法为补全分配额外行或列（例如固定行高限制或不可变布局），采用以下降级方式按优先级执行：
  1. 行内候选：在当前输入行内以最小干扰的文本片段展示首个候选（不遮挡 ASCII art），用户可按 Tab 接受。
  2. 状态栏提示：在最底部状态栏显示"补全可用（按 Ctrl+Space 查看）"并在用户触发时以 paged 模式显示候选。
  3. 被动提示：仅在输入历史或选项无交互时不显示补全。

4) 可视化与无障碍
- 补全列表应支持键盘导航与屏幕阅读器友好文本描述（label + description）。
- 在 ASCII art 旁展开时，确保补全区域使用可读的对比度与固定宽度字体以匹配 ASCII art 风格。

## 六. 与 `docs/ui_internals.md` 的签名/类型一致性

- 本文档中使用的类型名与字段签名应与内部签名保持一致，详细参见 [`docs/ui_internals.md`](docs/ui_internals.md:1)（依据内部文档）。
- 在实现时注意点：
  - 若内部文档对 InputPayload 的字段名或嵌套结构有不同，应以内部文档为准，并在转换层（adapter）中进行字段映射。
  - 前端渲染器需支持本 schema 的 fields 数组格式，并在读取时对缺省字段进行内聚（例如 absent -> null / 默认值填充）。

## 七. 实现注意事项与性能/隐私建议

- 缓存 TTL 建议：默认 300s，可通过命令元数据中的 cacheTTL 覆盖；对隐私敏感条目建议 cacheTTL=0。
- 频率限制：远端补全请求默认节流为 200ms（可配置），并在失败后采用指数回退。
- 网络降级：避免在主渲染路径阻塞远端请求；采用异步加载与渐进增强（先展示本地候选，远端返回后合并）。
- 数据最小化：补全请求应仅发送必要上下文（字段名、已输入文本、panel id），避免发送敏感历史。
- 日志与审计：对补全查询的记录应可配置，敏感查询默认不记录或做脱敏处理。

## 八. 示例片段（示意）

- 示例 1：命令元数据（YAML）

```yaml
id: "send_email"
type: "form"
title: "发送邮件"
description: "通过表单填写邮件信息并发送"
autocomplete: true
formSchema:
  fields:
    - name: "to"
      type: "text"
      label: "收件人"
      placeholder: "example@domain.com"
      required: true
    - name: "subject"
      type: "text"
      label: "主题"
      placeholder: "邮件主题"
      required: false
    - name: "priority"
      type: "select"
      label: "优先级"
      options:
        - value: "low"
          label: "低"
        - value: "normal"
          label: "普通"
        - value: "high"
          label: "高"
```

- 示例 2：表单数据（JSON 提交示意）

```json
{
  "to": "alice@example.com",
  "subject": "部署通知",
  "priority": "high"
}
```

- 示例 3：补全伪代码（Python 风格示意）

```python
def fetch_suggestions(input_text, field_name, panel_id):
    # 优先：本地选项 -> 本地缓存 -> 内置词表 -> 远端 API
    candidates = local_options(field_name, panel_id)
    if not candidates:
        candidates = cache.get_recent(field_name, input_text)
    if not candidates:
        candidates = builtin_dictionary.search(input_text)
    if not candidates:
        candidates = remote_api.query(field_name, input_text, panel_id)
    return rank_candidates(candidates, input_text)
```

## 九. 下一步建议

- 将上文 schema 转为机器可读的 JSON Schema 文件并加入仓库（例如 schema/command_metadata.json）。
- 在 CI 中对所有 config/panels/*.yaml 做 schema 校验，防止手工编辑引入不一致。
- 在 UI 端实现 adapter 层以兼容 [`docs/ui_internals.md`](docs/ui_internals.md:1) 的签名（依据内部文档）。
- 针对补全实现添加可配置的 telemetry 与隐私策略开关（cache TTL、记录策略）。