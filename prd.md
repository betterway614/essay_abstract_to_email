# 产品需求文档 (PRD): ArXiv Daily Digest Workflow (AI 增强版)

| 文档版本 | 日期 | 修改人 | 变更描述 |
| --- | --- | --- | --- |
| **v1.0.0** | 2023-10-XX | 架构师/PM/RE | 整合基础爬取与 LLM 摘要功能，定稿 MVP 方案 |

## 1. 项目背景与目标

用户希望构建一个自动化的情报获取工具，旨在解决科研人员“手动检索耗时”和“摘要阅读低效”的痛点。
系统将利用 **GitHub Actions** 作为无服务器运行环境，每日定时从 **ArXiv** 获取最新论文，通过 **LLM (大语言模型)** 生成中文结构化简报，并以 **HTML 邮件** 形式推送至用户邮箱。

**核心价值：**

* **零维护成本：** 无需服务器，依托 GitHub Actions 免费额度。
* **信息降噪：** 通过关键词精准过滤 + AI 提炼核心价值。
* **自动化闭环：** 配置一次，每日自动运行。

## 2. 总体架构设计

由于不涉及前端开发，系统主要由 Python 脚本和工作流配置文件组成。

### 2.1 技术栈选型

* **编程语言：** Python 3.9+
* **运行环境：** GitHub Actions (Ubuntu-latest)
* **数据源：** ArXiv Official API (xml/atom)
* **AI 引擎：** OpenAI SDK 兼容接口 (支持 OpenAI, DeepSeek, Claude, Moonshot 等)
* **通知渠道：** SMTP 协议 (支持 Gmail, Outlook, QQ 邮箱等)

### 2.2 逻辑架构图

```mermaid
graph TD
    A[GitHub Actions Timer (Daily)] --> B[Python Script Start]
    B --> C[Load Config & Secrets]
    
    subgraph Data Acquisition
    C --> D[Query ArXiv API]
    D -->|Filter Date (Last 24h)| E[Raw Paper List]
    E -->|Filter Keywords (Title/Abs)| F[Target Paper List]
    end
    
    subgraph Intelligent Processing
    F --> G{Is List Empty?}
    G -- Yes --> H[End / Notify Empty]
    G -- No --> I{Enable LLM?}
    
    I -- Yes --> J[Async Loop: Call LLM API]
    J -->|Success| K[Generate Structured Summary]
    J -->|Fail/Timeout| L[Fallback: Use Original Abstract]
    I -- No --> L
    end
    
    subgraph Delivery
    K & L --> M[Render HTML Email Template]
    M --> N[Send via SMTP]
    end

```

## 3. 功能需求说明 (Functional Requirements)

### 3.1 配置管理模块 (Configuration)

系统需支持两类配置方式：**公开配置文件** (业务逻辑) 与 **加密环境变量** (敏感凭证)。

| ID | 需求项 | 详细描述 | 优先级 |
| --- | --- | --- | --- |
| **F-01** | **业务参数配置** | 支持通过 `config.yaml` 配置：<br>

<br>1. `subjects`: 关注的学科 (如 `cs.CV`, `cs.LG`)<br>

<br>2. `keywords`: 过滤关键词 (如 `LLM`, `Agent`)<br>

<br>3. `filter_mode`: 关键词匹配模式 (AND/OR) | P0 |
| **F-02** | **凭证安全注入** | 必须通过 GitHub Secrets 注入以下变量：<br>

<br>1. `MAIL_USER` / `MAIL_PASS`<br>

<br>2. `LLM_API_KEY`<br>

<br>3. `LLM_BASE_URL` (可选，适配不同厂商) | P0 |

### 3.2 数据获取与过滤 (Data Fetcher)

| ID | 需求项 | 详细描述 | 优先级 |
| --- | --- | --- | --- |
| **F-03** | **API 数据抓取** | 调用 ArXiv API，参数设置为 `sortBy=submittedDate`, `sortOrder=descending`。 | P0 |
| **F-04** | **时间窗筛选** | 严格计算时间窗口，仅保留 `submittedDate` 在过去 24 小时内的记录 (考虑时区 UTC)。 | P0 |
| **F-05** | **关键词过滤** | 对论文的 `Title` 和 `Summary` 进行关键词匹配。支持大小写不敏感匹配。 | P0 |

### 3.3 智能摘要 (LLM Processor)

| ID | 需求项 | 详细描述 | 优先级 |
| --- | --- | --- | --- |
| **F-06** | **AI 摘要生成** | 若配置了 API Key，则调用 LLM 对每篇论文生成总结。 | P1 |
| **F-07** | **结构化 Prompt** | Prompt 需指示 LLM 输出包含：<br>

<br>1. **背景/痛点**<br>

<br>2. **核心方法**<br>

<br>3. **主要结论**<br>

<br>并要求输出语言可配置 (默认中文)。 | P1 |
| **F-08** | **并发与限流** | 使用 `asyncio` 或线程池并发请求 LLM，但需限制最大并发数 (如 3-5) 以防触发 API 限流。 | P2 |
| **F-09** | **服务降级** | 若 LLM 调用超时、报错或额度耗尽，系统**不应中断**，而是标记该论文为“无 AI 摘要”，仅展示原文摘要。 | P0 |

### 3.4 邮件推送 (Notifier)

| ID | 需求项 | 详细描述 | 优先级 |
| --- | --- | --- | --- |
| **F-10** | **HTML 渲染** | 使用 Jinja2 模板生成邮件。包含：论文标题 (链接)、作者、**AI 速读板块** (高亮显示)、原文摘要 (折叠或置后)。 | P0 |
| **F-11** | **空结果处理** | 若当日无符合条件的论文，可配置 `send_empty` 开关决定是否发送“今日无更新”通知。 | P2 |

## 4. 接口与数据规范

### 4.1 配置文件 (`config.yaml`) 示例

```yaml
# 筛选规则
criteria:
  categories: ["cs.CL", "cs.AI"]
  keywords: ["Large Language Model", "Reasoning", "Chain of Thought"]
  match_logic: "OR" # 只要命中一个关键词即可

# LLM 设置
llm:
  enable: true
  provider: "openai" # 兼容 openai 格式
  model: "gpt-3.5-turbo" # 或 deepseek-chat
  language: "zh-CN"
  
# 邮件设置
email:
  recipient: "user@example.com"
  subject_prefix: "[ArXiv Daily 🚀]"

```

### 4.2 邮件内容布局示意

```text
Subject: [ArXiv Daily 🚀] 2023-10-27Update: 3 Papers Found

--------------------------------------------------
1. Title: Chain-of-Thought Prompting Elicits Reasoning
   Authors: Jason Wei, et al.
   
   [🤖 AI 速读]
   📌 痛点：大模型在复杂算术和逻辑推理任务上表现不佳。
   💡 方法：通过在 Prompt 中加入中间推理步骤（Chain of Thought）。
   🚀 结论：在 GSM8K 等数据集上准确率大幅提升，甚至超越微调模型。

   [原始摘要] (点击链接查看原文 PDF)
--------------------------------------------------
2. Title: ...
...

```

## 5. 非功能需求 (NFR)

1. **稳定性：** 脚本运行超时时间设置为 15 分钟（GitHub Actions 限制通常为 6 小时，绰绰有余）。
2. **安全性：** 代码仓库中绝不包含任何 API Key 或密码。必须在 README 中引导用户设置 Secrets。
3. **兼容性：** LLM 模块需通过更改 `BASE_URL` 即可适配 DeepSeek、Moonshot、Yi 等国产大模型 API。
4. **成本控制：** LLM 请求仅发送 `Title` 和 `Abstract`，严禁发送全文 PDF 内容，以控制 Token 消耗。

