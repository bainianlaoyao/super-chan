# 数据载荷设计

UI层通过标准化的载荷结构与后端通信，确保类型安全和序列化兼容性。

## InputPayload 输入载荷

### 字段定义

```python
@dataclass
class InputPayload:
    type: Literal["procedure", "nl"]      # 载荷类型
    input: str | dict[str, Any]           # 载荷内容
    timestamp: datetime | None = None     # 时间戳
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
```

### 字段说明

- **type**: 载荷类型
  - `"nl"`: 自然语言输入，input 应为字符串
  - `"procedure"`: 程序化命令输入，input 应为字典
- **input**: 实际载荷内容，根据 type 确定格式
- **timestamp**: 可选时间戳，使用 UTC 时区
- **metadata**: 扩展元数据字典

### 构造示例

```python
# 自然语言输入
nl_payload = InputPayload(
    type="nl",
    input="请帮我查询用户信息",
    timestamp=datetime.now(timezone.utc)
)

# 程序化命令输入
proc_payload = InputPayload(
    type="procedure",
    input={"command": "query_user", "user_id": 123},
    metadata={"source": "terminal"}
)
```

## OutputPayload 输出载荷

### 字段定义

```python
@dataclass
class OutputPayload:
    output: str | dict[str, Any]          # 输出内容
    type: Literal['text', 'dict']         # 输出类型
    timestamp: datetime | None = None     # 时间戳
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
```

### 字段说明

- **output**: 输出内容，可以是字符串或结构化字典
- **type**: 输出类型标识
  - `"text"`: 纯文本输出
  - `"dict"`: 结构化数据输出
- **timestamp**: 可选时间戳
- **metadata**: 扩展元数据

### 序列化支持

两个载荷类都支持序列化为字典和从字典反序列化：

```python
# 序列化
payload_dict = payload.to_dict()

# 反序列化
payload = InputPayload.from_dict(payload_dict)
```

## 类型安全

- 构造时会验证 type 和 input 的类型匹配性
- 提供向后兼容的反序列化处理
- 时间戳自动处理时区转换

## 参考源码

- [`superchan/ui/io_payload.py`](superchan/ui/io_payload.py:1)