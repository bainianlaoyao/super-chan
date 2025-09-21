# anime 模块：处理逻辑概述

本文档仅描述模块的运行时处理逻辑（简洁版），顺序为：输入 -> 引擎处理 -> 生成输出文本 -> anime 使用 LLM 对 payload 中的输出文本进行后处理 -> 返回 UI。

处理流程（高层次）：

1. 输入（Input）
   - 类型：自然语言文本或结构化命令
   - 载荷示例：{ "type": "nl", "input": "给我一些二次元风格的问候语" }
   - 责任：验证基本格式并注入必要的 metadata（timestamp、request_id 等）

2. 引擎处理（Engine Processing）
   - 目标：将输入路由到主处理引擎（如程序化执行器或 LLM 执行器），获取初步响应文本或结构化结果
   - 输入：标准化后的 InputPayload
   - 输出：EngineResponsePayload，包含至少字段：{ "output_text": str, "output_type": "text" | "dict", "metadata": {...} }
   - 错误模式：若引擎超时或返回错误，应返回带错误码和可显示错误消息的 OutputPayload

3. 生成输出文本（Generate Output Text）
   - 说明：从 EngineResponsePayload 中提取或格式化为最终待后处理的文本形式
   - 输出形态：string（纯文本）或 dict（含多段文本或结构化片段）

4. anime 模块的 LLM 后处理（anime LLM Post-process）
   - 目的：对引擎产出的文本执行风格化/润色/二次元化转写、插入情绪标签、生成动画指令片段等
   - 输入：Payload（至少包含 output_text）
   - 处理示例（伪代码）：
     - 构建 prompt：将 output_text 与上下文 metadata 拼接成一个后处理请求
     - 调用 LLM（或本地润色器）获取 post_processed_text
     - 可选：解析 LLM 返回的结构化 annotations（如 emotion, animation_cues）
   - 输出：PostProcessedPayload { "post_text": str, "annotations": dict, "metadata": {...} }

5. 返回 UI（Return to UI）
   - 将 PostProcessedPayload 封装为 OutputPayload 并通过 IoRouter/Transport 返回给调用的 UI
   - OutputPayload 最低包含：{ "type": "text", "output": post_text, "metadata": {...} }
   - 可选：若包含 annotations（动画/情绪指令），则同时以附加字段返回，供 UI（如 TerminalUI）驱动动画或音频播放

简要伪代码实现（Python 风格，描述性，供参考）：

```python
def handle_anime_request(input_payload):
    # 1. 验证并标准化输入
    payload = normalize_input(input_payload)

    # 2. 路由到主引擎处理
    engine_resp = engine.process(payload)

    # 3. 提取/格式化输出文本
    output_text = extract_text(engine_resp)

    # 4. 使用 LLM 进行后处理（风格化 / 注释）
    post_payload = llm_postprocess({"output_text": output_text, "metadata": engine_resp.get("metadata", {})})

    # 5. 构建最终 OutputPayload 并返回给 UI
    return {
        "type": "text",
        "output": post_payload["post_text"],
        "metadata": post_payload.get("metadata", {}),
        "annotations": post_payload.get("annotations", {}),
    }
```

注意事项与边界情况：
- 空输入：应返回带有提示的 OutputPayload，提示用户补充内容
- 引擎错误或超时：返回明确的错误消息与 code，方便 UI 呈现重试按钮
- LLM 后处理不确定：如果 LLM 返回不符合约定结构，应退化为原始 engine 输出文本并记录警告
- 大文本：对过长文本进行截断或分页返回，metadata 中注明截断信息

此文档仅作为运行时处理逻辑说明，详尽的实现细节（如具体 prompt、重试策略、并发限制、缓存策略）应在代码级别或另一份设计文档中规范。
