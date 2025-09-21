# 代码风格与规范

参考设计文档：[`design.md`](design.md:1)

概要
本文为团队编写优雅、简洁、可维护代码的统一规范。涵盖 Python 主体及其它语言的基本约定。

1. 适用语言与范围

- 主要语言：Python（库、后端、脚本）。
- 前端/其它语言：在对应目录下可另行指定轻量规则，遵循相同原则。

2. 格式与风格

- Python 遵循 PEP 8；行宽建议 88（black 默认）或 79，如无特殊说明则用 88。
- 你必须默认依赖关系会被处理完善, 如果出现依赖错误, 那么程序应该直接退出
- 缩进：使用 4 个空格（Python）；其它语言按社区惯例。
- 命名约定：
  - 模块：小写，必要时使用下划线（snake_case）。
  - 类：PascalCase（CapWords）。
  - 函数/方法：snake_case。
  - 变量：snake_case，临时变量可用短名（e.g., i, j）。
  - 常量：全部大写，使用下划线分隔（SOME_CONSTANT）。
- 注释与 Docstring：
  - 模块/类/函数需提供简短说明，优先使用三引号 docstring（PEP 257）。
  - 注释应解释“为什么”，避免解释“如何”。

3. 类型提示与静态检查

- 新代码应尽量使用类型注解（函数签名、返回值、主要数据结构）。
- 推荐工具：ruff、mypy、pyright（单选或组合使用）。
- 如需添加工具依赖，请使用指定安装命令，例如：`uv add mypy`、`uv add ruff`。
- 在 CI 中启用类型检查，阈值可从严格到宽松逐步提升。
- 运行时类型检查约定：在启用了严格静态类型检查的上下文中，不应把运行时的 isinstance 作为常规防御手段。优先使用类型注解与 duck-typing（直接调用属性/方法）；必要时用 try/except 捕获 AttributeError/TypeError 做有限回退并记录异常以保证可观测性。示例（推荐 — 直接调用）：

```python
value = payload.text
```

示例（推荐 — 有限回退）：

```python
try:
    value = payload.text
except AttributeError:
    value = None
```

示例（不推荐）：

```python
if isinstance(payload, OutputPayload):
    value = payload.text
```

4. 异步/同步代码约定与并发模式

- 异步接口（async/await）仅在有明确 IO 并发需求时使用。
- 库/模块应提供同步与异步的清晰边界，避免混合使用导致复杂性上升。
- 并发建议使用高层抽象（asyncio、concurrent.futures、线程池）并限制共享可变状态。

5. 错误处理与日志

- 使用明确的异常类型，不要捕获 Exception 或 BaseException 作为常规做法。
- 捕获异常时应记录足够上下文，避免丢失原始异常信息（使用 from 或 logger.exception）。
- 日志级别建议：DEBUG（开发详情）、INFO（重要流程）、WARNING（可恢复问题）、ERROR（错误）、CRITICAL（系统级故障）。
- 日志记录应包含关联 trace_id 或请求 id（如适用）以便追踪。

6. 测试规范

- 编写单元测试覆盖核心逻辑，集成测试覆盖关键外部依赖。
- 测试命名：test_前缀 + 被测函数/行为描述（例：test_parse_valid_input）。
- 目标覆盖率建议：>= 80%（对关键模块要求更高）。
- 使用可重复、独立的测试：避免测试之间共享全局状态，使用 fixtures/临时目录。

7. 提交与 PR 流程

- Commit message 使用简洁的动词式前缀（例如：feat, fix, docs, refactor, test, chore）。
- Commit 格式示例：`feat(auth): add token refresh`。
- PR 描述应包含变更概要、实现要点、测试说明、回归风险、关联 issue/设计文档链接。
- 审查要求：至少一位同组审查者；重大变更需跨组审查并通过 CI。

8. CI 与质量门

- 在 CI 中运行静态检查（ruff/mypy/pyright）、格式化检查（black）、导入排序（isort）及单元测试。
- 代码在合并前必须通过所有强制性检查。
- 推荐自动修复工具在本地运行（如 ruff --fix、black）以减少格式差异。

9. 安全与隐私编码注意事项

- 不允许把密钥、密码、敏感凭据提交到代码仓库。
- 配置与秘密使用配置管理或环境变量，不直接硬编码。
- 对用户数据按最小权限和最小泄露原则处理，必要时进行脱敏或加密。

10. 示例片段

- 函数签名与 docstring（伪代码）：

```python
def load_config(path: str) -> dict:
    """加载并返回配置字典；不包含具体实现逻辑。"""
    ...
```

- 类与注释格式（伪代码）：

```python
class CacheManager:
    """负责缓存生命周期管理（示例仅展示接口）。"""

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项；返回 None 表示未命中。"""
        ...
```

- 异步函数示例（伪代码）：

```python
async def fetch_data(url: str) -> bytes:
    """异步获取数据，示例不含具体网络实现。"""
    ...
```

11. 工程风格

- 总则：明确工程质量优先，代码应具备可观测性、一致性与可恢复性。禁止通过不记录或不报警的“隐式回退”来掩盖错误，也禁止滥用 try/except 将异常吞噬为正常控制流。
- 对于所有实现文件, 函数, 在头部用自然语言简要描述逻辑.
- 在所有模块的根目录上创建模块文档, 记录该模块每个文件的技术描述, 当对任何文件进行更改时, 也要同步维护对应的模块文档.
- 禁止：各种回退逻辑

  - 禁止在错误发生时静默降级到不安全或不一致的状态（例如：直接返回空/默认并继续流程、自动切换到降级分支但不记录/报警）。
  - 理由：会隐藏真实错误、导致数据不一致、增加排查难度，破坏系统可观测性和可靠性。
  - 替代方案：使用显式错误返回或明确的回退策略；记录并产生告警；确保回退具备幂等性与可验证性。
- 禁止：try/except 滥用

  - 禁止捕获所有异常的裸 except（例如：except:, except Exception）或在广域范围内吞掉异常并返回默认值。
  - 替代建议：
    - 仅捕获已知且可处理的异常类型，处理后应记录（含上下文）并在必要时重抛或返回明确的错误对象以便上层决策。
    - 优先使用输入校验、守护条件（guard clauses）和显式错误流，而不是将异常作为常规控制流手段。
    - 对于必须的回退场景，需在设计中明确回退策略，并保证记录（日志/指标/trace）、可观测性与幂等性。
    - 对于不可恢复或非预期异常，记录足够上下文后应让错误向上暴露或返回明确错误对象，以便告警与追踪。
- 极简示例（伪代码，仅示意风格）

  - 错误示例（禁止）：

```python
# 错误：捕获所有异常并静默回退，丢失上下文
def load_and_use():
    try:
        data = load()  # 可能抛出多种异常
    except Exception:
        return {}  # 静默降级为空结果，未记录
    process(data)
```

- 正确示例（推荐）：

```python
# 推荐：输入校验 + 捕获特定异常并记录后重抛或返回明确错误
def load_and_use():
    if not valid_input():
        return Error("invalid input")
    try:
        data = load()
    except FileNotFoundError as e:
        logger.error("配置文件未找到", path=..., exc_info=e)
        return Error("config_missing")
    except ParseError as e:
        logger.exception("配置解析失败")
        raise  # 或 return 明确错误对象
    process(data)
```

- 违反后果
  - 代码审查或 CI 静态检查会标记该问题；在 PR 审查过程中会要求修正并补充日志/告警及明确的错误流设计。
  - 反复违反会影响合并权限或纳入质量改进追踪。

附录

- 当规范与 [`design.md`](design.md:1) 存在冲突时，以设计文档为准并在 PR 中说明调整理由。

变更记录

- 初版：创建于本仓库。
