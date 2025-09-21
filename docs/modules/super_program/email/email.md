# Email Program Group Design

## 概述

Email Program Group 是 Super Program 模块的核心组件之一，提供完整的邮件处理解决方案。该组包含三个主要组件：Email Fetcher、Email Summariser 和 Email Pusher，共同实现邮件的获取、处理和分发功能。

## 架构设计

```
email/
├── __init__.py
├── fetcher/
│   ├── __init__.py
│   ├── base_fetcher.py      # 基础获取器接口
│   ├── imap_fetcher.py      # IMAP 客户端
│   ├── pop3_fetcher.py      # POP3 客户端
│   ├── smtp_fetcher.py      # SMTP 客户端 (如果需要)
│   ├── api_fetcher.py       # REST API 客户端
│   └── outlook_fetcher.py   # 本地 Outlook 客户端
├── summariser/
│   ├── __init__.py
│   ├── base_summariser.py   # 基础摘要器接口
│   └── llm_summariser.py    # LLM 驱动摘要
├── pusher/
│   ├── __init__.py
│   ├── base_pusher.py       # 基础推送器接口
│   ├── webhook_pusher.py    # Webhook 推送
│   ├── mqtt_pusher.py       # MQTT 推送
│   ├── email_pusher.py      # 邮件转发推送
│   └── api_pusher.py        # REST API 推送
├── models/
│   ├── email_message.py     # 邮件消息模型
│   ├── summary.py           # 摘要模型
│   └── config.py            # 配置模型
├── utils/
│   ├── validators.py        # 数据验证工具
│   ├── parsers.py           # 邮件解析工具
│   └── formatters.py        # 数据格式化工具
└── config/
    └── email_config.toml    # 邮件配置模板
```

## 组件详细设计

### 1. Email Fetcher (邮件获取器)

#### 功能特性
- 支持多种邮件协议：IMAP、POP3、SMTP、REST API、本地 Outlook 客户端
- 自动连接管理和重试机制
- 邮件过滤和搜索功能
- 增量同步支持
- 多账户并发处理

#### 支持的客户端/方法

##### IMAP Fetcher
```python
class IMAPFetcher(BaseFetcher):
    def __init__(self, host: str, port: int, username: str, password: str):
        # IMAP4_SSL 或 IMAP4 连接
        pass

    async def fetch_emails(self, criteria: dict) -> List[EmailMessage]:
        # 支持的搜索条件：
        # - 日期范围
        # - 发送者
        # - 主题关键词
        # - 邮件状态 (已读/未读)
        pass

    async def mark_as_read(self, message_ids: List[str]):
        pass
```

##### POP3 Fetcher
```python
class POP3Fetcher(BaseFetcher):
    def __init__(self, host: str, port: int, username: str, password: str):
        # POP3_SSL 或 POP3 连接
        pass

    async def fetch_emails(self, limit: int = None) -> List[EmailMessage]:
        # POP3 通常不支持复杂搜索
        # 支持限制获取数量
        pass
```

##### API Fetcher
```python
class APIFetcher(BaseFetcher):
    def __init__(self, base_url: str, api_key: str, auth_method: str):
        # 支持 OAuth2, API Key, Basic Auth 等
        pass

    async def fetch_emails(self, endpoint: str, params: dict) -> List[EmailMessage]:
        # REST API 集成，如 Gmail API, Outlook API
        pass
```

##### Outlook Fetcher (本地客户端)
```python
# 依赖库：pywin32 (包含 win32com)
# 安装：pip install pywin32
# 注意：仅支持 Windows 平台，且需要安装 Microsoft Outlook

import win32com.client
from typing import List, Optional
from datetime import datetime

class OutlookFetcher(BaseFetcher):
    def __init__(self, profile_name: str = None):
        """
        初始化 Outlook 获取器
        
        Args:
            profile_name: Outlook 配置文件名，默认使用默认配置文件
        """
        self.profile_name = profile_name
        self.outlook = None
        self.namespace = None
        
    def _connect(self):
        """连接到 Outlook 应用程序"""
        try:
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            if self.profile_name:
                # 如果指定了配置文件，使用特定配置文件
                pass  # Outlook COM API 通常使用默认配置文件
        except Exception as e:
            raise ConnectionError(f"无法连接到 Outlook: {e}")
    
    def _disconnect(self):
        """断开 Outlook 连接"""
        if self.outlook:
            # Outlook COM 对象通常不需要显式断开
            self.outlook = None
            self.namespace = None
    
    async def fetch_emails(self, folder_name: str = "Inbox", 
                          criteria: Optional[dict] = None, 
                          limit: int = None) -> List[EmailMessage]:
        """
        从指定文件夹获取邮件
        
        Args:
            folder_name: 文件夹名，如 "Inbox", "Sent Items"
            criteria: 过滤条件，如 {"unread": True, "date_from": datetime}
            limit: 限制获取数量
            
        Returns:
            邮件消息列表
        """
        if not self.outlook:
            self._connect()
            
        try:
            # 获取指定文件夹
            folder = self.namespace.GetDefaultFolder(self._get_folder_constant(folder_name))
            
            # 应用过滤条件
            items = folder.Items
            if criteria:
                items = self._apply_filters(items, criteria)
            
            # 排序（最新邮件优先）
            items.Sort("[ReceivedTime]", True)
            
            emails = []
            count = 0
            for item in items:
                if limit and count >= limit:
                    break
                    
                if item.Class == 43:  # olMail 类型
                    email = self._convert_to_email_message(item)
                    emails.append(email)
                    count += 1
                    
            return emails
            
        except Exception as e:
            raise RuntimeError(f"获取邮件失败: {e}")
    
    def _get_folder_constant(self, folder_name: str) -> int:
        """获取 Outlook 文件夹常量"""
        constants = {
            "Inbox": 6,        # olFolderInbox
            "Sent Items": 5,   # olFolderSentMail
            "Drafts": 16,      # olFolderDrafts
            "Deleted Items": 3,# olFolderDeletedItems
            "Junk": 23,        # olFolderJunk
        }
        return constants.get(folder_name, 6)  # 默认 Inbox
    
    def _apply_filters(self, items, criteria: dict):
        """应用过滤条件"""
        filter_str = ""
        
        if criteria.get("unread"):
            filter_str += "[UnRead] = True"
        
        if "date_from" in criteria:
            date_str = criteria["date_from"].strftime("%Y-%m-%d %H:%M:%S")
            if filter_str:
                filter_str += " AND "
            filter_str += f"[ReceivedTime] >= '{date_str}'"
        
        if "sender" in criteria:
            sender = criteria["sender"]
            if filter_str:
                filter_str += " AND "
            filter_str += f"[SenderEmailAddress] = '{sender}'"
        
        if filter_str:
            return items.Restrict(filter_str)
        return items
    
    def _convert_to_email_message(self, outlook_item) -> EmailMessage:
        """将 Outlook 邮件对象转换为 EmailMessage"""
        # 处理邮件正文
        body = ""
        if outlook_item.BodyFormat == 1:  # olFormatPlain
            body = outlook_item.Body
        elif outlook_item.BodyFormat == 2:  # olFormatHTML
            body = outlook_item.HTMLBody
        elif outlook_item.BodyFormat == 3:  # olFormatRichText
            body = outlook_item.RTFBody
        
        # 处理收件人
        recipients = []
        if outlook_item.Recipients:
            for recipient in outlook_item.Recipients:
                recipients.append(recipient.Address)
        
        # 处理附件
        attachments = []
        if outlook_item.Attachments:
            for attachment in outlook_item.Attachments:
                attachments.append({
                    "filename": attachment.FileName,
                    "size": attachment.Size,
                    "content": attachment  # 实际使用时需要保存到临时文件
                })
        
        return EmailMessage(
            message_id=outlook_item.EntryID,
            subject=outlook_item.Subject or "",
            sender=outlook_item.SenderEmailAddress or "",
            recipients=recipients,
            body=body,
            attachments=attachments,
            timestamp=outlook_item.ReceivedTime,
            flags=self._get_flags(outlook_item),
            raw_data=None  # Outlook COM 不提供原始数据
        )
    
    def _get_flags(self, outlook_item) -> set:
        """获取邮件标志"""
        flags = set()
        if outlook_item.UnRead:
            flags.add("unread")
        else:
            flags.add("read")
        
        if outlook_item.FlagStatus == 1:  # olFlagMarked
            flags.add("flagged")
        
        if outlook_item.IsMarkedAsTask:
            flags.add("task")
            
        return flags
    
    async def mark_as_read(self, message_ids: List[str]):
        """标记邮件为已读"""
        if not self.outlook:
            self._connect()
            
        try:
            for message_id in message_ids:
                item = self.namespace.GetItemFromID(message_id)
                item.UnRead = False
                item.Save()
        except Exception as e:
            raise RuntimeError(f"标记邮件已读失败: {e}")
    
    async def move_to_folder(self, message_ids: List[str], folder_name: str):
        """移动邮件到指定文件夹"""
        if not self.outlook:
            self._connect()
            
        try:
            target_folder = self.namespace.GetDefaultFolder(self._get_folder_constant(folder_name))
            
            for message_id in message_ids:
                item = self.namespace.GetItemFromID(message_id)
                item.Move(target_folder)
        except Exception as e:
            raise RuntimeError(f"移动邮件失败: {e}")
```

#### 依赖和要求
- **Python 库**: `pywin32` (通过 `pip install pywin32` 安装)
- **系统要求**: Windows 操作系统
- **软件要求**: Microsoft Outlook 已安装并配置
- **权限要求**: 需要访问 Outlook COM API 的权限

#### 配置示例
```toml
[email.fetcher.outlook]
enabled = true
profile_name = "Outlook"  # 可选，默认使用默认配置文件
default_folder = "Inbox"
auto_mark_read = false

[fetcher.outlook.filters]
unread_only = true
date_from = "2024-01-01"
max_emails = 50
```

#### 使用注意事项
1. **平台限制**: 仅在 Windows 平台上工作
2. **Outlook 版本**: 支持 Outlook 2007 及以上版本
3. **性能考虑**: 大量邮件处理时可能较慢，建议使用分页获取
4. **安全**: 需要确保 Outlook 安全设置允许 COM 访问
5. **并发**: Outlook COM 对象不是线程安全的，避免多线程同时访问

#### 配置示例
```toml
[email.fetcher]
default_protocol = "imap"
accounts = [
    { name = "gmail", protocol = "imap", host = "imap.gmail.com", port = 993 },
    { name = "outlook", protocol = "imap", host = "outlook.office365.com", port = 993 }
]

[fetcher.filters]
unread_only = true
date_from = "2024-01-01"
max_emails = 100
```

### 2. Email Summariser (邮件摘要器)

#### 功能特性
- LLM 驱动的智能摘要生成
- 支持多种语言和 LLM 提供商
- 可配置摘要长度和格式
- 智能关键词提取和情感分析
- 自动识别优先级和行动项

#### LLM Summariser
```python
class LLMSummariser(BaseSummariser):
    def __init__(self, llm_provider: str, model: str, api_key: str, 
                 max_tokens: int = 500, temperature: float = 0.3):
        """
        初始化 LLM 摘要器
        
        Args:
            llm_provider: LLM 提供商 ('openai', 'anthropic', 'ollama' 等)
            model: 模型名称 ('gpt-4', 'claude-3', 'llama2' 等)
            api_key: API 密钥
            max_tokens: 最大输出 token 数
            temperature: 生成温度 (0.0-1.0)
        """
        self.llm_provider = llm_provider
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = self._init_client()
    
    def _init_client(self):
        """初始化 LLM 客户端"""
        if self.llm_provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=self.api_key)
        elif self.llm_provider == "anthropic":
            from anthropic import Anthropic
            return Anthropic(api_key=self.api_key)
        elif self.llm_provider == "ollama":
            from ollama import Client
            return Client()
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.llm_provider}")
    
    async def summarise(self, email: EmailMessage) -> Summary:
        """
        生成邮件摘要
        
        Args:
            email: 邮件消息对象
            
        Returns:
            摘要对象
        """
        prompt = self._build_prompt(email)
        
        try:
            if self.llm_provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                content = response.choices[0].message.content
                
            elif self.llm_provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                
            elif self.llm_provider == "ollama":
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        "num_predict": self.max_tokens,
                        "temperature": self.temperature
                    }
                )
                content = response["response"]
            
            return self._parse_summary(content, email.message_id)
            
        except Exception as e:
            raise RuntimeError(f"LLM 摘要生成失败: {e}")
    
    def _build_prompt(self, email: EmailMessage) -> str:
        """构建摘要提示词"""
        prompt = f"""
请为以下邮件生成一个简洁的摘要，包括以下信息：

邮件主题: {email.subject}
发件人: {email.sender}
收件人: {', '.join(email.recipients)}
发送时间: {email.timestamp}
邮件正文:
{email.body[:2000]}...  # 限制正文长度

请提供以下格式的摘要：
1. 标题：简短描述邮件主题
2. 内容：邮件主要内容的总结（50-100字）
3. 优先级：高/中/低
4. 类别：工作/个人/通知/垃圾邮件/其他
5. 关键词：3-5个关键词
6. 情感：积极/消极/中性
7. 行动项：需要采取的行动（如果有）

请用JSON格式返回结果。
"""
        return prompt
    
    def _parse_summary(self, content: str, message_id: str) -> Summary:
        """解析 LLM 输出为 Summary 对象"""
        import json
        
        try:
            # 尝试解析 JSON
            data = json.loads(content)
            
            return Summary(
                email_id=message_id,
                title=data.get("标题", ""),
                content=data.get("内容", ""),
                priority=self._map_priority(data.get("优先级", "中")),
                category=data.get("类别", "其他"),
                keywords=data.get("关键词", "").split(",") if isinstance(data.get("关键词"), str) else data.get("关键词", []),
                sentiment=self._map_sentiment(data.get("情感", "中性")),
                action_items=data.get("行动项", "").split("\n") if isinstance(data.get("行动项"), str) else data.get("行动项", []),
                generated_at=datetime.now()
            )
            
        except json.JSONDecodeError:
            # 如果不是有效 JSON，用默认解析
            return self._fallback_parse(content, message_id)
    
    def _map_priority(self, priority_str: str) -> str:
        """映射优先级字符串"""
        mapping = {"高": "high", "中": "medium", "低": "low"}
        return mapping.get(priority_str, "medium")
    
    def _map_sentiment(self, sentiment_str: str) -> float:
        """映射情感字符串为数值"""
        mapping = {"积极": 0.8, "中性": 0.5, "消极": 0.2}
        return mapping.get(sentiment_str, 0.5)
    
    def _fallback_parse(self, content: str, message_id: str) -> Summary:
        """备用解析方法"""
        # 简单的文本解析作为后备
        lines = content.split("\n")
        title = lines[0] if lines else "无标题"
        content_summary = " ".join(lines[1:3]) if len(lines) > 1 else content[:100]
        
        return Summary(
            email_id=message_id,
            title=title,
            content=content_summary,
            priority="medium",
            category="其他",
            keywords=[],
            sentiment=0.5,
            action_items=[],
            generated_at=datetime.now()
        )
```

#### 配置示例
```toml
[email.summariser]
llm_provider = "openai"
model = "gpt-4"
api_key = "your-api-key-here"
max_tokens = 500
temperature = 0.3

# 可选：支持多个 LLM 配置用于不同场景
[summariser.fallback]
llm_provider = "ollama"
model = "llama2"
api_base = "http://localhost:11434"
```

### 3. Email Pusher (邮件推送器)

#### 功能特性
- 多渠道推送支持
- 实时和批量推送模式
- 推送状态跟踪
- 失败重试机制
- 推送过滤和路由

#### 支持的推送方法

##### Webhook Pusher
```python
class WebhookPusher(BasePusher):
    def __init__(self, webhook_url: str, secret: str):
        # 支持签名验证
        pass

    async def push(self, summary: Summary, target: str):
        # 发送 HTTP POST 请求到 webhook
        # 包含摘要数据和元信息
        pass
```

##### MQTT Pusher
```python
class MQTTPusher(BasePusher):
    def __init__(self, broker: str, port: int, topic: str):
        # MQTT 客户端连接
        pass

    async def push(self, summary: Summary, target: str):
        # 发布到 MQTT topic
        # 支持 QoS 级别
        pass
```

##### Email Pusher
```python
class EmailPusher(BasePusher):
    def __init__(self, smtp_config: dict):
        # SMTP 配置用于转发
        pass

    async def push(self, summary: Summary, target: str):
        # 将摘要作为新邮件发送
        # 支持附件和格式化
        pass
```

##### API Pusher
```python
class APIPusher(BasePusher):
    def __init__(self, base_url: str, auth_config: dict):
        # REST API 推送
        pass

    async def push(self, summary: Summary, target: str):
        # 发送 POST/PUT 请求到目标 API
        pass
```

#### 配置示例
```toml
[email.pusher]
default_method = "webhook"
webhook_url = "https://api.example.com/webhooks/email-summary"
mqtt_broker = "mqtt.example.com"

[pusher.routing]
urgent = "webhook:urgent-channel"
meeting = "email:manager@example.com"
newsletter = "mqtt:news/topic"
```

## 数据模型

### EmailMessage
```python
@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    recipients: List[str]
    body: str
    attachments: List[Attachment]
    timestamp: datetime
    flags: Set[str]  # read, answered, etc.
    raw_data: bytes
```

### Summary
```python
@dataclass
class Summary:
    email_id: str           # 关联的邮件ID
    title: str              # 摘要标题
    content: str            # 摘要内容
    priority: str           # 优先级: high, medium, low
    category: str           # 类别: urgent, meeting, newsletter, etc.
    keywords: List[str]     # 关键词列表
    sentiment: float        # 情感得分: -1.0(消极) 到 1.0(积极)
    action_items: List[str] # 行动项列表
    generated_at: datetime  # 生成时间戳
```

#### Summary 数据结构设计意义

相比纯字符串，结构化 Summary 数据具有以下优势：

1. **可查询性**: 可以按优先级、类别、情感等维度过滤和搜索摘要
2. **可操作性**: 结构化字段支持自动化处理，如优先级排序、类别分组
3. **可扩展性**: 新增字段不会破坏现有数据结构
4. **类型安全**: 强类型定义减少运行时错误
5. **标准化**: 统一的格式便于下游系统集成
6. **分析能力**: 支持统计分析，如情感分布、关键词频率等

**为什么不使用纯字符串？**
- 纯字符串摘要虽然简单，但无法支持复杂的业务逻辑
- 难以从纯文本中提取结构化信息（如优先级判断）
- 不利于系统的模块化和可维护性
- 限制了后续处理的自动化程度

**实际应用场景**:
- 邮件客户端可以根据 `priority` 字段对邮件进行排序显示
- 工作流系统可以根据 `action_items` 自动创建任务
- 分析工具可以基于 `sentiment` 和 `category` 生成统计报告
- 搜索功能可以利用 `keywords` 提供更精准的检索

## 安全考虑

- 敏感信息加密存储
- API 密钥安全管理
- 网络通信使用 TLS
- 输入验证和 XSS 防护
- 速率限制和 DDoS 防护

## 监控和日志

- 详细的操作日志
- 性能指标收集
- 错误监控和告警
- 健康检查端点

## 扩展性

- 插件架构支持自定义组件
- 配置驱动的灵活性
- 异步处理支持高并发
- 容器化部署支持

## 测试策略

- 单元测试覆盖核心逻辑
- 集成测试验证组件协作
- 端到端测试模拟完整流程
- 性能测试确保扩展性

## 部署和运维

- Docker 容器化
- Kubernetes 编排
- 配置管理
- 日志聚合
- 备份和恢复策略