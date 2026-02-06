# Task

I am a PHD student majoring in traffic engineering and AI, I want to develop such a tool：给定研究领域和关键词，帮我在arxiv, scopus, ieee xplore等平台搜索最新的论文，自行判定相关性并做排序，然后总结最相关的10篇论文形成简报发给我并保存在本地文件夹；我会给出简报的内容格式要求。

我打算先以arxiv平台为基础做出这个工具，实现基本的功能，以后再添加IEEE Xplore,Scopus（Elsevier）作为新的检索源。构思这样一个工具：
1 用户自定义的配置文件：待检索的领域关键词；生成简报的格式，我先给你一个初始版本，该简报要按照以下格式用英语编排：论文标题、作者、发文单位、原文链接、code repo链接（若有）等基本信息，该文章要解决什么问题，该文如何解决问题，该文的方法论创新是什么，该文的实验/实证创新是什么，如何用4-5句话向别人讲述这篇文章。
2 该工具输出的内容：每隔48h在早上9点在目标目录下生成markdown格式简报，以日期MMDD_papers.md命名文件；同时存一份 SQLite 缓存（避免重复总结、支持回溯与增量
3 要求：检索最近一周上线的论文，先去重(不仅当天内容要去重，也要保证与之前的内容不重复)，然后做相关性排序，只根据最相关的10篇论文生成当天的简报。我会给你一个zai/glm4.7模型的api key (c08ff386f21d4e3bb91c88e02241283b.KUDj29Zq6Po5crR0)，使用这个模型完成检索、去重、排序、生成简报等工作。

下面给出一个以 **arXiv 为唯一检索源的 MVP**（后续可无缝扩展到 IEEE Xplore / Scopus）的技术路线与 Python 实现方案（架构与逻辑）。其中会把“去重、排序、生成简报”等关键环节拆成可测试、可替换的模块，并明确哪些地方应交给 GLM-4.7，哪些地方必须用确定性逻辑保证稳定性。

---

## A. MVP 总体架构（arXiv-only，可扩展）

### 1) 模块划分（建议按包/子模块组织）

1. **config**：加载/校验用户配置（JSON），生成运行时配置对象
2. **sources.arxiv**：arXiv 论文检索与元数据解析（只做“拿数据”，不做智能判断）
3. **normalize & dedup**：标题规范化、ID 归一化、跨天/跨周去重（确定性逻辑）
4. **cache (SQLite)**：持久化候选论文、处理状态、摘要结果、每次简报记录（增量与回溯的核心）
5. **ranker (LLM)**：相关性评分/排序（GLM-4.7）
6. **enricher**（可选但强烈建议留接口）：

   * code repo 链接提取（regex + Papers with Code / 其他源）
   * affiliation（单位）抽取（优先 arXiv 元数据中存在则用，否则 PDF→GROBID→解析）
7. **summarizer (LLM)**：结构化信息抽取 + 4–5 句“对外讲述”（GLM-4.7）
8. **renderer**：把结构化 JSON 渲染成你要求的 Markdown 模板
9. **scheduler wrapper**：本地定时（macOS launchd）+ “48h 闸门”逻辑（避免 launchd 难以精确表达 48 小时周期）

### 2) 数据流（一次运行）

1. 读取配置
2. 从 arXiv 拉取 **最近 7 天**候选（例如先取最近 N=200 条，再本地按日期过滤）
3. 规范化与去重（本次候选内部 + 与 SQLite 历史记录对比）
4. 对剩余候选做相关性评分（LLM ranker）
5. 选 Top 5–10 篇
6. 对 Top 5–10 篇生成结构化摘要（LLM summarizer）
7. 渲染 Markdown → 写入目标目录 `MMDD_papers.md`
8. 更新 SQLite（记录本次 digest、论文处理状态、摘要与评分、输出文件路径、运行时间戳）

---

## B. arXiv 检索策略（确定性、可复现）

### 1) arXiv API 查询

* arXiv API 支持 `sortBy=submittedDate/lastUpdatedDate` 与 `sortOrder=descending`，适合“抓最新”。([info.arxiv.org][1])
* 实务上建议：

  * 查询端先按关键词/类别取一批（例如 200–500）最新结果；
  * 然后在本地用 `published/submitted date` 过滤到最近 7 天（避免查询语法对日期过滤的限制带来的不稳定）。

（你也可用 Python 的 `arxiv` 包作为 wrapper，减少 XML 解析成本；但注意它对 affiliation 等字段可能不完全暴露，需要时仍要访问原始 feed）。([PyPI][2])

### 2) 候选集合构建建议

* 用配置文件定义：

  * `include_keywords`（必含词组/同义词组）
  * `exclude_keywords`（排除项）
  * `categories`（如 `cs.AI`, `cs.LG`, `stat.ML` 等）
  * `max_results`（抓取上限）
* 生成 query 时采用：

  * `ti:`（标题）+ `abs:`（摘要）组合；
  * 对交通工程/AI方向，建议至少使用“领域描述（自然语言）+ 关键词列表”双轨：关键词用于召回，领域描述用于 LLM 评分。

---

## C. SQLite 缓存设计（保证“不重复”与可回溯）

你提出的“去重不仅当天，还要与历史不重复”，本质上需要一个“事实真相源（SQLite）”。

### 1) 最小表结构（建议）

* `papers`：每篇论文一行

  * `paper_id`（主键：优先 arXiv_id + version；例如 `2402.01234v1`）
  * `source`（固定 `arxiv`）
  * `title_raw`, `title_norm`, `abstract_raw`
  * `authors_raw`
  * `published_at`, `updated_at`
  * `arxiv_url`, `pdf_url`
  * `code_urls`（JSON array）
  * `affiliations`（JSON，可能为空）
  * `first_seen_at`（你系统首次看到它的时间）
* `paper_processing`：处理状态（可与 papers 合并，也可分表便于状态机）

  * `paper_id`, `rank_score`, `rank_reason`
  * `summary_json`（LLM 输出的结构化结果）
  * `status`（NEW/RANKED/SUMMARIZED/EMITTED/FAILED）
  * `last_error`, `updated_at`
* `digests`：每次运行输出一条

  * `digest_id`, `run_at`, `window_days=7`, `top_k`
  * `output_path`, `model_used`（glm-4.7）
* `digest_items`：digest 与 paper 的多对多

  * `digest_id`, `paper_id`, `rank_order`

### 2) 去重策略（建议强约束）

* **首选 key**：`arxiv_id + version`（v1/v2 视作不同版本是否要重复出现，由你定义）
* **次选 key**：规范化标题 hash（防止交叉源重复、或 arXiv ID 缺失的情况）
* **三选**：`(title_norm, first_author, year)` 组合 hash（抗噪）

---

## D. “发文单位/机构”字段：必须直面数据缺口

你要求“发文单位”，但 arXiv 元数据通常并不稳定提供机构信息：arXiv 提交流程本身不强制 affiliation 字段，很多时候需要从作者字段或 PDF 首页抽取。([docs.ropensci.org][3])
同时，arXiv API feed 在“有提供时”可以包含 `<arxiv:affiliation>` 子元素，但并非普遍存在。([info.arxiv.org][1])

### 推荐实现（分层退化）

1. **优先**：若 arXiv feed 存在 `arxiv:affiliation`，直接写入
2. **否则**：下载 PDF（仅对 Top 10 篇）→ 用 **GROBID** 抽取 TEI/XML → 解析 affiliation（最可控、可复现）([grobid.readthedocs.io][4])
3. **再否则（可选）**：接入 OpenAlex / Semantic Scholar 做补全（但要接受 coverage 不完整的现实）

---

## E. code repo 链接：建议“确定性提取 + 外部补全”双轨

### 1) 确定性提取（低成本、低幻觉）

* 从 `abstract/comment`、PDF 首页、附录等位置用 regex 抓 `github.com / gitlab.com` 等链接。
* 只要你把“repo 链接必须来自原文可见 URL”设为硬规则，就能杜绝 LLM 猜 repo。

### 2) 外部补全（可选但很有用）

* **Papers with Code** 有公开 API 生态，且有成熟的 Python client，可用标题/DOI/arXiv ID 做匹配以获得 repo/实现信息。([GitHub][5])
* 如果你未来做“agent 化工具链”，也有现成的 **mcp-paperswithcode** 作为“技能/工具端点”。([GitHub][6])

---

## F. 相关性排序：LLM 只做“评分”，不要做“数据真相”

你要求“自行判定相关性并排序”，建议采用 **LLM 评分 + 可解释理由** 的策略，而不是让 LLM 自己决定候选集合。

### 1) Ranker 输入

* 研究领域自然语言描述（你在配置中写 5–15 行）
* 关键词列表（include/exclude）
* 每篇论文：title + abstract + categories +（可选）authors/affiliation
* 时间窗口信息：只评“最近 7 天候选”里的

### 2) Ranker 输出（结构化）

* `relevance_score`（0–100）
* `tags`（如 “traffic safety / trajectory prediction / causality / spatiotemporal / graph learning”）
* `reason`（不超过 3 条要点，方便你审阅）

### 3) 降成本策略（建议）

* 先用确定性启发式过滤（关键词命中、类别过滤、黑名单词排除）把候选从 500 降到 50–100，再让 LLM 评分。
* 评分可以 batch：一次 prompt 评 10–20 篇（输出 JSON array），并加入严格 schema 校验。

---

## G. 生成简报：用“JSON 结构化抽取”保证格式稳定

你给的英文简报字段，最稳的实现是：

1. **LLM summarizer**：对单篇论文输出严格 JSON（全英文），字段包括：

   * `basic`: title, authors, affiliations(optional), links(arxiv/pdf), code_urls(optional)
   * `problem`（文章解决什么问题）
   * `approach`（如何解决：核心方法流程）
   * `methodological_novelty`（方法论创新点）
   * `empirical_novelty`（实验/实证创新点：数据/对比/指标/结论）
   * `tell_someone_in_4_5_sentences`（4–5 句对外讲述）
   * `evidence_quotes_or_anchors`（可选：让模型指出它依据摘要中的哪些短语得出判断；用于降低幻觉）
2. **renderer**：把 JSON 渲染为 Markdown 模板（你随时改模板不影响 LLM 抽取逻辑）

---

## H. GLM-4.7 接入（你提供 key 后的工程要点）

智谱/BigModel 平台的 HTTP 调用方式是标准 `Authorization: Bearer <API_KEY>`，Chat Completions 端点为 `.../api/paas/v4/chat/completions`，模型字段可用 `"glm-4.7"`；也提供 JWT 鉴权选项与“coding 端点/通用端点”的区分。([docs.bigmodel.cn][7])

工程建议：

* **把 key 放环境变量**（不要进配置文件，不要进日志）
* 抽象一个 `LLMClient`：

  * `chat(messages, model, temperature, max_tokens, response_format)`
* 对 ranker/summarizer 都走同一个 client，但用不同的 system prompt 与 schema。

---

## I. “每 48h 早上 9 点运行”在 macOS 上的可行实现

`launchd` 更擅长“每天几点/每小时/固定日历点”而不是“严格每 48h”。最可靠做法是：

* **launchd：每天 09:00 触发一次**
* 程序启动后读取 SQLite 里的 `last_run_at`：若距离上次成功运行未满 48h，则直接退出；否则执行完整流程。

这种“高频触发 + 程序内部做时间闸门”的模式在 launchd 场景中是常见实践。([Ask Different][8])

---

## J. 可扩展性：未来接 IEEE Xplore / Scopus 时不重构

关键是把 `sources` 抽象成统一接口，例如：

* `search(window_days, query_profile) -> List[PaperCandidate]`
* 候选结构统一：`source`, `external_id`, `title`, `abstract`, `published_at`, `urls`, `raw_payload`

未来新增 `sources.ieee` / `sources.scopus`：

* 只新增“取数与规范化”模块；
* 去重、ranker、summarizer、renderer、cache 完全复用。

---

## K. 简报模版

```markdown
# Daily Paper Summary - MMDD, YYYY  

## Paper 1: [Title of the Paper](arxiv_url)

### Paper Information
- **Authors**: Author 1, Author 2, ...
- **Affiliations**: Institution 1, Institution 2, ...
- **arXiv Link**: [arxiv_url](arxiv_url)
- **PDF Link**: [pdf_url](pdf_url)
- **Code Repository**: [code_url_1](code_url_1), [code_url_2](code_url_2) (if available)

### Problem Addressed
A concise description of the problem the paper aims to solve.

### Approach
A summary of the methods and techniques used to address the problem.

### Methodological Novelty
An explanation of the innovative aspects of the methodology proposed in the paper.

### Empirical Novelty
A description of the novel experiments or empirical findings presented in the paper.

### Summary for Communication
A 4-5 sentence summary that effectively communicates the essence of the paper to others.

## Paper 2: [Title of the Paper](arxiv_url)

...

```

---

## L. 参考

[1]: https://info.arxiv.org/help/api/user-manual.html?utm_source=chatgpt.com "arXiv API User's Manual"
[2]: https://pypi.org/project/arxiv/?utm_source=chatgpt.com "arxiv"
[3]: https://docs.ropensci.org/aRxiv/articles/aRxiv.html?utm_source=chatgpt.com "aRxiv tutorial - Docs - rOpenSci"
[4]: https://grobid.readthedocs.io/en/latest/Principles/?utm_source=chatgpt.com "How GROBID works"
[5]: https://github.com/paperswithcode/paperswithcode-client "GitHub - paperswithcode/paperswithcode-client: API Client for paperswithcode.com"
[6]: https://github.com/hbg/mcp-paperswithcode?utm_source=chatgpt.com "hbg/mcp-paperswithcode"
[7]: https://docs.bigmodel.cn/cn/guide/develop/http/introduction "HTTP API 调用 - 智谱AI开放文档"
[8]: https://apple.stackexchange.com/questions/414301/launchd-how-to-run-a-command-every-3-minutes-during-working-hours-on-a-weekday?utm_source=chatgpt.com "launchd, how to run a command every 3 minutes, during ..."
[9]: https://github.com/danimal141/arxiv-search-mcp?utm_source=chatgpt.com "danimal141/arxiv-search-mcp: An MCP server that ..."
[10]: https://docs.langchain.com/oss/python/integrations/document_loaders/arxiv?utm_source=chatgpt.com "ArxivLoader document loader integration guide for ..."
[11]: https://github.com/YuzeHao2023/Awesome-MCP-Servers?utm_source=chatgpt.com "YuzeHao2023/Awesome-MCP-Servers"
[12]: https://github.com/AutoLLM/ArxivDigest?utm_source=chatgpt.com "AutoLLM/ArxivDigest: ArXiv Digest and Personalized ..."
[13]: https://github.com/monologg/nlp-arxiv-daily?utm_source=chatgpt.com "GitHub - monologg/nlp-arxiv-daily: Automatically Update ..."


