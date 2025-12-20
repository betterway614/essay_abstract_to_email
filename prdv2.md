
# 产品需求文档 (PRD): Academic Daily Digest (多源聚合版)


## 1. 项目背景与目标

原有的 ArXiv Daily Digest 系统虽然稳定，但仅覆盖预印本数据，无法获取已发表在 IEEE、ACM、Springer 等期刊会议上的正式论文。
为了满足科研人员“全网学术情报获取”的需求，本项目将集成 **Semantic Scholar API**。相比 Google Scholar，Semantic Scholar 提供官方免费 API，且直接包含清洗后的**摘要 (Abstract)** 数据，能够有效解决反爬虫和数据提取难题。

**核心目标：**

* **扩大覆盖面：** 从单一源扩展为双源（ArXiv + Semantic Scholar）。
* **保持低成本：** 继续利用 GitHub Actions 和免费 API 额度。
* **统一体验：** 对不同来源的论文进行去重和格式统一，用户感知的输出依然是整洁的日报邮件。

## 2. 总体架构设计 (Architecture)

### 2.1 架构变更：策略模式 (Strategy Pattern)

为了支持多源扩展，需重构 `src/arxiv_client.py`，抽象出通用的获取层。

* **Before (v1.0):** `Main` -> `ArxivClient` -> `LLM` -> `Mailer`
* **After (v2.0):**
```mermaid
graph TD
    Main[Main Workflow] --> Manager[Fetch Manager]

    subgraph Fetch Strategy
    Manager -->|Call| A[ArxivFetcher]
    Manager -->|Call| B[SemanticScholarFetcher]
    end

    A -->|List[Paper]| D[Deduplicator]
    B -->|List[Paper]| D

    D -->|Unique Papers| LLM[LLM Processor]
    LLM --> Mailer[Email Sender]

```



### 2.2 数据流向

1. **并行获取：** 系统同时调用 ArXiv API 和 Semantic Scholar API。
2. **数据归一化：** 各 Fetcher 将原始数据清洗为统一的 `Paper` 字典格式（含 `source` 字段）。
3. **全局去重：** 根据**归一化标题**（小写、去标点）对两路数据进行合并去重。优先保留 ArXiv 版本（通常含 PDF 链接）或信息更全的版本。
4. **智能处理：** 统一送入 LLM 生成摘要。
5. **邮件推送：** 在邮件中标记论文来源（如 `[ArXiv]` 或 `[S2]`）。

## 3. 功能需求说明 (Functional Requirements)

### 3.1 多源获取模块 (Multi-Source Fetcher)

| ID | 功能模块 | 需求描述 | 优先级 |
| --- | --- | --- | --- |
| **F-01** | **Fetcher 接口定义** | 定义抽象基类 `BaseFetcher`，规范输出字段：`title`, `authors`, `summary`, `pub_date`, `pdf_url`, `source`。 | P0 |
| **F-02** | **Semantic Scholar 集成** | 实现 `SemanticScholarFetcher`。<br>

<br>1. 接口地址：`https://api.semanticscholar.org/graph/v1/paper/search`<br>

<br>2. 参数：`query={keyword}`, `year={current_year}`, `fields=title,abstract,url,venue,publicationDate`<br>

<br>3. 过滤：仅保留最近 **3天** 内发表的论文（S2 数据更新有延迟，需放宽窗口）。 | P0 |
| **F-03** | **API Key 配置** | 支持在 GitHub Secrets 中配置 `SEMANTIC_SCHOLAR_API_KEY`（可选，配置后速率限制更宽松）。 | P1 |
| **F-04** | **ArXiv 模块重构** | 将原 `ArxivClient` 适配为 `ArxivFetcher`，逻辑保持不变，增加 `source="ArXiv"` 字段。 | P0 |

### 3.2 数据清洗与去重 (Data Processing)

| ID | 功能模块 | 需求描述 | 优先级 |
| --- | --- | --- | --- |
| **F-05** | **全局去重逻辑** | 实现 `Deduplicator` 类。<br>

<br>1. **规则：** 将标题转为小写并移除所有标点符号，计算哈希值作为指纹。<br>

<br>2. **冲突解决：** 若两源存在同一篇论文，优先保留 **ArXiv** 版本（因 ArXiv 通常直接提供 PDF 下载，而 S2 链接多为出版社付费墙）。 | P0 |
| **F-06** | **空摘要处理** | S2 部分论文可能无摘要（`abstract` 为 null）。若无摘要，需在数据中标记，LLM 处理阶段跳过摘要生成，邮件中显示“摘要未收录”。 | P1 |

### 3.3 配置文件升级 (Configuration)

| ID | 功能模块 | 需求描述 | 优先级 |
| --- | --- | --- | --- |
| **F-07** | **源开关控制** | `config.yaml` 新增 `data_sources` 模块，允许用户单独开启或关闭 `arxiv` 和 `semantic_scholar`。 | P1 |
| **F-08** | **独立关键词配置** | (可选) 允许为 S2 单独配置关键词，或默认复用 `keywords` 列表。v2.0 暂定复用通用关键词列表。 | P2 |

## 4. 接口与数据规范

### 4.1 配置文件 (`config.yaml`) 变更

```yaml
# 新增数据源配置
data_sources:
  arxiv:
    enable: true
  semantic_scholar:
    enable: true
    # S2 的搜索可能比 ArXiv 慢，建议关键词少而精
    api_key_env: "SEMANTIC_SCHOLAR_API_KEY" # 对应 Secrets 里的 key

# 筛选规则 (通用)
criteria:
  categories: ["cs.CV", "cs.LG"] # ArXiv 专用
  keywords: ["LLM", "Agent", "Reasoning"] # 两者共用
  # S2 不支持 category 筛选，仅使用 keywords 搜索

```

### 4.2 统一数据模型 (Python Dict)

所有 Fetcher 必须返回以下格式列表：

```python
{
    "title": "Chain-of-Thought Prompting Elicits Reasoning",
    "authors": ["Jason Wei", "Xuezhi Wang"],
    "summary": "We explore how generating a chain of thought...", # 必须清洗换行符
    "pdf_url": "https://arxiv.org/pdf/2201.11903", # 或 S2 的 DOI 链接
    "published": datetime_obj, # 统一转为 UTC 时间对象
    "source": "ArXiv" # 或 "Semantic Scholar"
}

```

## 5. 开发计划 (Development Plan)

建议按以下顺序执行开发，避免破坏现有功能：

1. **重构阶段 (Refactor):**
* 创建 `src/fetchers/` 目录。
* 定义 `base_fetcher.py`。
* 将 `src/arxiv_client.py` 迁移为 `src/fetchers/arxiv_fetcher.py`。
* **测试：** 确保仅开启 ArXiv 时，系统行为与 v1.0 完全一致。


2. **集成阶段 (Integration):**
* 开发 `src/fetchers/semantic_scholar_fetcher.py`。
* 编写单元测试，模拟 S2 API 响应，测试解析逻辑。


3. **聚合阶段 (Aggregation):**
* 在 `src/main.py` 中引入 `FetchManager` 或简单的聚合逻辑。
* 实现去重函数 `deduplicate_papers(papers_list)`。


4. **UI 适配 (UI Update):**
* 修改 `templates/email_template.html`，在标题旁增加来源标签（例如使用徽章样式：`<span class="badge">ArXiv</span>`）。



## 6. 风险与对策

* **API 速率限制：** S2 免费 API 限制较严。
* *对策：* 代码中加入 `time.sleep(1)` 间隔；若请求失败（HTTP 429），自动降级为跳过该关键词或仅使用 ArXiv 数据。


* **数据噪音：** S2 搜索全是关键词匹配，可能搜出很多非 CS 领域的论文。
* *对策：* 在 S2 Fetcher 中增加简单过滤，或者接受一定的噪音（由用户通过精简关键词控制）。


* **PDF 获取率：** S2 返回的 `url` 往往跳到 Publisher 页面（需付费）。
* *对策：* 这是行业通病。PRD 明确：S2 主要提供“情报索引”，看全文需用户自行解决权限（如通过学校库）。邮件中明确标注链接性质。