from superchan.ui.io_payload import OutputPayload
def dispatch_output(output: OutputPayload) -> str:
    """根据 OutputPayload 的内容分发输出。

    - 如果 output.type 是 "text"，则打印文本内容。
    - 如果 output.type 是 "dict"，则打印字典的 'text' 字段（如果存在）。
    - 其他类型暂不处理。
    """
    text_to_show: str
    if isinstance(output.output, dict):
        # 规则：dict 输出时，展示 output['text']（若不存在则回退为 str(dict)）
        text_to_show = str(output.output.get("text", str(output.output)))
        
        match output.metadata.get("command_name"):
            case "echo":
                text_to_show = f"[Echo] {text_to_show} (耗时: {output.output.get('time_used', '未知')} 秒)"
            case _:
                pass
    else:
        # 规则：text 输出时，直接展示为字符串
        text_to_show = str(output.output)
    return text_to_show