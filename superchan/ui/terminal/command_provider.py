"""superchan.ui.terminal.command_provider

Textual Command Provider & form Screen for procedure commands.

功能：
- 扫描 `config/procedure/*.toml` 以发现可用的 procedure 命令。
- 将每个 procedure 作为单独的命令出现在 Textual 命令面板中。
- 选择命令时，弹出顶层表格（含字段/类型/值）以收集输入；提交后回调到 App。

与 App 的集成契约：
- App 需实现 `open_procedure_form(spec: ProcedureSpec) -> None` 方法，
  该方法内部应调用 `self.push_screen(ProcedureFormScreen(spec), self._on_procedure_form_result)`
  或者任何等价方式，并在结果为 dict 时构造 InputPayload(type='precedure', input=values, metadata=spec.metadata | {"procedure": spec.name}) 发送。
- 为避免循环依赖，本模块不直接导入 TerminalUI，仅通过 duck-typing 调用 App 的方法。

注意：
- TOML 解析使用 Python 3.11+ 的标准库 `tomllib`。
- 输入类型支持 str/int/float/bool，提交时将尝试做类型转换，失败则保留为字符串并在表格中标红提示。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


import tomllib

from textual.command import Hit, Hits, Provider
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, VerticalScroll, Container
from textual.widgets import Button, Input, Label


# ----------------------------
# Data model for a procedure
# ----------------------------


@dataclass
class ProcedureSpec:
    name: str
    description: str
    input_schema: dict[str, str]  # field -> type name (e.g., "str", "int", "float", "bool")
    metadata: dict[str, Any]
    output_spec: dict[str, str]  # field -> type name (e.g., "str", "dict")
    file_path: Path
    presets: list[dict[str, Any]]  # list of {"name": str, "params": dict}


def _load_procedure_file(path: Path) -> ProcedureSpec | None:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return None

    cmd = dict(data.get("command") or {})
    name = cmd.get("name") or path.stem
    description = cmd.get("description") or ""
    input_schema = dict(data.get("input") or {})
    metadata = dict(data.get("metadata") or {})
    output_spec = dict(data.get("output") or {})
    presets_data = data.get("presets", [])
    presets: list[dict[str, Any]] = []
    for preset in presets_data:
        if isinstance(preset, dict):
            preset_dict = cast(dict[str, Any], preset)
            preset_name = str(preset_dict.get("name", ""))
            params: dict[str, Any] = {str(k): v for k, v in preset_dict.items() if k != "name"}
            presets.append({"name": preset_name, "params": params})
    return ProcedureSpec(
        name=name,
        description=description,
        input_schema=input_schema,
        metadata=metadata,
        output_spec=output_spec,
        file_path=path,
        presets=presets,
    )


def _iter_procedure_specs(root: Path) -> list[ProcedureSpec]:
    specs: list[ProcedureSpec] = []
    for path in sorted(root.glob("*.toml")):
        spec = _load_procedure_file(path)
        if spec is not None:
            specs.append(spec)
    return specs


# ------------------------------------
# Screen to collect procedure inputs
# ------------------------------------


class ProcedureFormScreen(ModalScreen[dict[str, Any] | None]):
    """顶层表格屏幕：显示字段/类型/值，并允许编辑值后提交。

    交互：
    - 同时展示所有输入控件（每个 key 一个 Input）。
    - 输入值即生效（on_input_changed），无需显式确认。
    - “提交”返回值字典；“取消”关闭且返回 None。
    """

    # 覆盖窗口样式：半透明遮罩 + 居中对话框，至少占 60% 空间
    DEFAULT_CSS = """
    ProcedureFormScreen {
        background: rgba(0,0,0,0.6);
    }
    #overlay {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    #dialog {
        width: 70%;
        height: 60%;
        background: $panel;
        border: heavy $primary;
        padding: 1 2;
        layout: vertical;
    }
    #title {
        content-align: center middle;
        height: auto;
        padding: 1 0;
    }
    #desc {
        color: $text-muted;
        height: auto;
        padding: 0 0 1 0;
    }
    #form {
        height: 1fr;
        overflow: auto;
    }
    .form-row {
        layout: horizontal;
        height: auto;
        padding: 0 0 1 0;
    }
    .field-label {
        width: 24%;
        text-align: right;
        padding-right: 1;
    }
    .form-input {
        width: 1fr;
    }
    .field-type {
        width: 12%;
        color: $text-muted;
        text-style: italic;
    }
    #actions {
        padding-top: 1;
        layout: horizontal;
        align-horizontal: right;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("ctrl+enter", "submit", "提交"),
        ("pagedown", "submit", "提交"),
    ]

    def __init__(self, spec: ProcedureSpec) -> None:
        super().__init__()
        self.spec = spec
        self.values: dict[str, Any] = {k: "" for k in spec.input_schema.keys()}
        self.hint: Label | None = None

    def compose(self) -> ComposeResult:
        with Container(id="overlay"):
            with Vertical(id="dialog"):
                yield Label(f"填写参数：{self.spec.name}", id="title")
                if self.spec.description:
                    yield Label(self.spec.description, id="desc")
                with VerticalScroll(id="form"):
                    for field, typ in self.spec.input_schema.items():
                        with Horizontal(classes="form-row"):
                            yield Label(field, classes="field-label")
                            yield Input(id=f"input-{field}", placeholder=f"请输入 {field}", classes="form-input")
                            yield Label(str(typ), classes="field-type")
                with Horizontal(id="actions"):
                    yield Button.success("提交", id="btn-submit")
                    yield Button.error("取消", id="btn-cancel")
                self.hint = Label("输入即生效，Ctrl+Enter 提交，Esc 取消", id="proc-hint")
                yield self.hint

    def on_mount(self) -> None:
        # 聚焦第一个输入框
        if self.spec.input_schema:
            first_field = next(iter(self.spec.input_schema.keys()))
            try:
                node = self.query(f"#input-{first_field}").first()
                if isinstance(node, Input):
                    node.focus()
            except Exception:
                pass

    # Actions
    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        # 类型转换
        casted: dict[str, Any] = {}
        for field, typ in self.spec.input_schema.items():
            raw = self.values.get(field, "")
            casted[field] = self._cast_value(str(raw), str(typ))
        self.dismiss(casted)

    # 不需要逐项确认动作

    # Helpers: 已不需要逐行编辑逻辑

    @staticmethod
    def _cast_value(value: str, typ: str) -> Any:
        t = typ.strip().lower()
        if t in ("str", "string", "text"):
            return value
        if t in ("int", "integer"):
            try:
                return int(value)
            except Exception:
                return value
        if t in ("float", "number"):
            try:
                return float(value)
            except Exception:
                return value
        if t in ("bool", "boolean"):
            v = value.strip().lower()
            if v in ("true", "1", "yes", "y", "on"):
                return True
            if v in ("false", "0", "no", "n", "off"):
                return False
            return value
        # 默认原样返回
        return value

    # Events: 输入即写入缓存
    def on_input_changed(self, event: Input.Changed) -> None:  # type: ignore[name-defined]
        input_id = event.input.id or ""
        if not input_id.startswith("input-"):
            return
        field = input_id[len("input-") :]
        self.values[field] = event.value

    # 鼠标点击按钮支持
    def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore[name-defined]
        button_id = event.button.id or ""
        if button_id == "btn-submit":
            self.action_submit()
        elif button_id == "btn-cancel":
            self.action_cancel()
        # 无需“设置值”按钮，输入实时生效


# ------------------------------------
# Command Provider
# ------------------------------------


class ProcedureCommands(Provider):
    """在命令面板中提供所有 `config/procedure/*.toml` 的命令。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._specs: list[ProcedureSpec] = []

    def _scan(self) -> list[ProcedureSpec]:
        root = Path("config/procedure")
        # 在线程中执行纯同步扫描
        return _iter_procedure_specs(root)

    async def startup(self) -> None:  # noqa: D401
        worker = self.app.run_worker(self._scan, thread=True)
        self._specs = await worker.wait()

    async def search(self, query: str) -> Hits:  # noqa: D401
        matcher = self.matcher(query)
        for spec in self._specs:
            # 主命令
            cmd_text = f"procedure {spec.name}"
            score = matcher.match(cmd_text)
            if score > 0:
                label = matcher.highlight(cmd_text)
                # 调用 App 的表单打开方法（duck-typing，避免循环依赖）
                def _invoke(spec: ProcedureSpec = spec) -> None:
                    app = self.app
                    open_form = getattr(app, "open_procedure_form", None)
                    if callable(open_form):
                        open_form(spec)

                yield Hit(
                    score,
                    label,
                    _invoke,
                    help=spec.description or "运行该 procedure",
                )
            # 预设命令
            for preset in spec.presets:
                preset_cmd = f"procedure {spec.name} {preset['name']}"
                score = matcher.match(preset_cmd)
                if score > 0:
                    label = matcher.highlight(preset_cmd)
                    def _invoke_preset(spec: ProcedureSpec = spec, preset: dict[str, Any] = preset) -> None:
                        app = self.app
                        execute_preset = getattr(app, "execute_procedure_preset", None)
                        if callable(execute_preset):
                            execute_preset(spec, preset["params"])

                    yield Hit(
                        score,
                        label,
                        _invoke_preset,
                        help=f"运行 {spec.name} 使用预设 {preset['name']}",
                    )
