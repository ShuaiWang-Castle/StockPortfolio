# GPT 审查包（原样入库）

GPT 对 PR #1（审查对象 SHA `b13c216e`）的独立复核。Claude 于 2026-11-14 按用户要求放入仓库。**除新增本文件和 `GPT_chat_review_20261113.md` 外，其余内容一字未改。**

| 项目 | 值 |
|---|---|
| 来源文件 | `StockPortfolio_PR1_review_20261113.zip`（用户上传） |
| zip SHA-256 | `5f74e0f0cb8af03ba23a837e1e2b3d3e28a32400c1bc8a77d123d46bce56bf47`（1,264,827 字节） |
| 解压 | 69 个文件，去掉 zip 顶层目录 `StockPortfolio_PR1_review_20261113/` 后放在本目录；路径与 GPT 的 `MANIFEST_SHA256.json` 一致 |
| 完整性 | Claude 逐个核对 `MANIFEST_SHA256.json` 中的 68 个条目，**68/68 一致** |
| 对话版评审 | `GPT_chat_review_20261113.md`：用户上传的 GPT 对话文本，原文保存，SHA-256 `9ffe388dd639a184bf34009fba475a4f6fd97bec55922ce9ad780a5b7d0859da` |
| 主文档 | `REVIEW_ZH.txt`（中文审查报告） |
| 代码 | `independent_review.py`、`valuation_checks.py`、`rebuild_prices_offline.py`、`data_audit/*.py`。**Claude 没有运行这些脚本**，而是另写代码，读取同一份原始数据进行复核 |

## Claude 的复核结论（详见 `../claude_analysis_20261114/README.md` 第 2 节）

- 20 个 Yahoo 原始 JSON → 价格表，与 GPT 的 `data_audit/adjusted_close.csv` 最大相对差 4.4e-16。
- 用不同算法（分段价格相对值，GPT 是逐日持仓循环）复现 GPT 全部 17 个组合的净值路径（最大差 6.2e-15），以及季度、月度、买入持有三种规则下的 561 行指标（最大差 8.5e-15）。
- GPT 的方法性批评全部接受，逐条处理见 `../claude_analysis_20261114/README.md` 第 5 节，以及 `../claude_analysis_20261113/ERRATA_20261114.md`。
- 唯一部分不同意的是"本轮不改权重"：GPT 的结论没有纳入 11/12 的 NVIDIA CEO 交接，也早于用户"降低 NVDA 乐观"的新表述。
