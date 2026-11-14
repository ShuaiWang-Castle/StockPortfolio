# StockPortfolio — AI 股票组合研究

截至 **2026-11-13 美国常规交易时段收盘**的研究档案，供 Shuai 与多个 AI agent 共同复核。包含价格数据、公司财报与估值分析、相关性和风险计算、历次组合比较、Excel 报表、图表、来源及复算代码。

**这是研究与拟议配置；没有执行交易，也不代表已持仓。** 预算为 **USD 7,000**。未来收益假设、历史回测和压力情景分别记录，不能互相代替。

## 从这里开始

1. [完整研究报告（中文）](docs/RESEARCH_REPORT_ZH.md)：当前配置、会计分析、相关性、风险与比较结论。
2. [Expected return：收益假设与复利口径](docs/EXPECTED_RETURN_ZH.md)：回答未来年化收益是多少；与历史 18.66% 明确区分。
3. [决策、假设与未决事项](docs/DECISIONS_AND_ASSUMPTIONS.md)：区分用户偏好、模型结果和仍需确认的信息。
4. [复现说明](docs/REPRODUCIBILITY.md)：使用冻结的数据重算，而不是下载新数据覆盖旧结果。
5. [多 agent 协作约定](docs/AGENT_COLLABORATION.md)：来源、文件责任、方案版本和复核方式。

## 当前方案

当前机器可读结果：[portfolio_conviction_review.json](portfolio_refresh_20261113/analysis/portfolio_conviction_review.json)。方案 ID 为 `conviction8`；进入阶段为 `conviction_entry`。

| 资产 | 目标权重 | 目标金额 | 进入阶段权重 | 进入阶段金额 |
|---|---:|---:|---:|---:|
| VTI | 35% | $2,450 | 35% | $2,450 |
| NVDA | 15% | $1,050 | 10% | $700 |
| GOOGL | 15% | $1,050 | 15% | $1,050 |
| MSFT | 10% | $700 | 10% | $700 |
| META | 5% | $350 | 5% | $350 |
| BRK-B | 10% | $700 | 10% | $700 |
| XLV | 5% | $350 | 5% | $350 |
| SGOV | 5% | $350 | 10% | $700 |
| **总计** | **100%** | **$7,000** | **100%** | **$7,000** |

进入阶段额外保留的 $350 SGOV 用于后续决策，并非预先承诺财报后自动买入 NVDA。目标含 95% 股票及 45% 直接 AI 公司股票；VTI 还包含间接重叠持仓。组合没有被证明为最大夏普、风险平价或全局最优。

### 版本识别

- `conviction8`：根据用户继续看好 NVIDIA 业务的明确意见形成的**当前目标**。
- `conviction_entry`：对应的拟议进入阶段。
- `prior7`：上一版七资产方案，用作比较。
- `revised7` / 早期 `entry`：本轮中途较审慎的方案，**已被后续偏好更新取代，不是当前目标**。
- `conviction_crm`、`conviction_qcom`、`conviction_sbux` 等：替换实验，不是已批准交易。

## 报表与图表

- [最新 Excel 报表](outputs/ai_portfolio_20261113/ai_portfolio_review_20261113.xlsx)
- [最新组合图表](outputs/ai_portfolio_20261113/ai_portfolio_review_20261113.png)
- [最新原始交付数据与代码压缩包](outputs/ai_portfolio_20261113/ai_portfolio_review_20261113_data_code.zip)
- [此前会计估值 Excel](outputs/ai_valuation/ai_portfolio_valuation.xlsx)
- [此前会计估值图表](outputs/ai_valuation/portfolio_risk_review.png)
- [此前会计估值数据与代码](outputs/ai_valuation/ai_portfolio_valuation_data_and_code.zip)
- [最初价格与组合分析 Excel](outputs/portfolio_review/portfolio_analysis.xlsx)
- [最初价格与组合数据与代码](outputs/portfolio_review/portfolio_data_and_code.zip)

报表和 ZIP 保留原交付内容；仓库脚本有单独记录的路径可移植性修正。`ai_portfolio_review_20261113_cautious.xlsx` 是被取代的审慎比较档案。

## 数据与方法

最新价格数据覆盖 39 个资产，原始观测最早为 2021-11-05、最晚为 2026-11-13。主五年窗口的价格锚点为 2021-11-12；主两年窗口为 2024-11-13。价格来源、获取时间、调整方式和质量检查见 [market_data_extended](portfolio_refresh_20261113/market_data_extended/)。

历史组合以拆股、分红调整后的美元日收益计算，按季度再平衡；未计个人税款、交易佣金和价差。当前目标的五年假设回测 CAGR 为 **18.66%**，年化波动率 **21.00%**，最大回撤 **−33.11%**；两年 CAGR 为 **16.16%**。这些不是实际账户业绩，也不是未来预期收益。

原模型没有估计未来收益向量。新增收益说明将 **10% 单年算术收益**作为主观规划假设，在约 21% 波动下粗略对应 **8% 长期复合增长**；这不构成数据已证实的预测或收益保证。完整口径、敏感性及限制见[收益说明](docs/EXPECTED_RETURN_ZH.md)。

会计分析使用各公司已披露期间的 TTM、现金流、资本开支、股权激励、非经营收益、税项和股数口径。静态 P/E、DCF 假设输出及未来可实现收益不能画等号。来源见各研究 JSON 及报告链接；旧的聊天内引用 ID 仅为溯源记录，以可访问 URL 和报告日期为准。

## 目录

| 路径 | 内容 |
|---|---|
| `docs/` | 当前研究、收益假设、决策记录、协作与复现说明 |
| `portfolio_refresh_20261113/` | 最新 39 资产分析、公司与政策核查、最终配置及独立审计 |
| `valuation_research/` | 此前财务实际值、FCFF / DCF、会计估值模型与来源缓存 |
| `ai_expansion_analysis/` | 扩大 AI 候选池时的比较分析 |
| `investment_plan_analysis/` | 此前六资产 / 七资产组合的数据与结果 |
| `market_analysis/`、`market_data/` | 最初跨行业相关性、历史回报与组合研究 |
| `outputs/` | 原始交付 Excel、图表、ZIP 与验证记录 |
| `tools/` | 离线复算或资料完整性检查入口 |
| `manifest.json` | 文件清单、SHA-256 与快照说明 |

所有“最新”均指本次 **2026-11-13** 快照。新增日期的研究应保留旧快照、明确新信息截止时间，并在 README 指向新的当前方案。

## Claude 独立版本（2026-11-13 收盘）

[`claude_analysis_20261113/`](claude_analysis_20261113/README.md) 是与上文 GPT 方案相互独立的分析，内容包括：
- 52 个资产的日频数据，Ledoit-Wolf 协方差、PCA/RMT 和最小生成树；
- 对冲诊断：ρ、ρ²、尾部依赖、不对称 β；
- 会计质量与反推增长率；
- ERC 加最小方差对冲腿，2022 历史压力回放（原文误称“样本外”，见 [勘误](claude_analysis_20261113/ERRATA_20261114.md)），平稳块自助法；
- 拟议的 AI 70% / 对冲 30% 组合，以及与 `conviction8` 的同口径对照。

数据、代码、图表与 SHA-256 清单都在该目录内。此节不改变上文的“当前方案”。

## 2026-11-14 第二轮（GPT 复核入库 + Claude 跟进）

新闻截至 2026-11-14；价格截至 2026-11-13 收盘。

- [`gpt_review_20261113/`](gpt_review_20261113/README_IMPORT.md)：GPT 对 PR #1 的独立复核，原样入库。其 MANIFEST 68/68 一致；对话版评审另存为 `GPT_chat_review_20261113.md`。
- [`claude_analysis_20261114/`](claude_analysis_20261114/README.md)：Claude 的跟进分析，内容包括：
  - 用独立代码复现 GPT 的全部路径与指标；
  - NVIDIA CEO 交接（8-K，11/12）后，NVDA 江湖地位的分层证据与事件研究；
  - 无杠杆的 Hybrid 组合（VTI 25%、NVDA 10%、其余 7 家 AI 按 ERC 分配、BRK-B/XLV/SGOV），按"同历史风险"对标 GPT 的两版方案和 Claude 11/13 版；
  - 对 11/13 版的勘误；
  - 11/17 财报前后的预先承诺规则。
- 上文的“当前方案”**没有改动**，是否采用 Hybrid 由 Shuai 决定。
- 说明：上文“从这里开始”和“目录”中引用的 `docs/`、`portfolio_refresh_20261113/`、`manifest.json` 等路径，在当前 `main` 分支中不存在（截至 `ad94904` 只有 `README.md` 与 Claude 目录），链接会 404。可能需要 GPT 补传。
