# 从哪里拨款给 ANT

Codex 由 OpenAI 开发。Anthropic 与 OpenAI 竞争，微软持有 OpenAI 股权。

如果希望保留直接持有 NVDA 的比例，又愿意提高模型公司的权重，可以从 VTI 或 BRK-B 拨款。用 VTI，能保留医疗和短债的专门配置，代价是按比例减持整个美国股市，包括少量 NVDA。用 BRK-B，能完整保留通过 VTI 持有的 NVDA，代价是放弃一部分保险、铁路和能源业务的收益。两者各出一部分，可以分摊这两项取舍。

下表采用已采纳的一次性买入方案和 7,000 美元预算。每行独立演示拨 **1 个百分点，即 70 美元**。表中 AI 敞口按组合已追踪的 8 家发行人加 ANT 统计，并只穿透 VTI，企业间持股留在各发行人名下。[已采纳方案](../current_plan.json) · [11/13 穿透权重](../claude_analysis_20261114/out/summary.json)

| 资金来源 | 该项拟议权重变化 | 追踪的 9 家 AI 公司净增 | 这 70 美元原来买什么 |
|---|---:|---:|---|
| VTI | 25% → 24% | 0.763 个百分点 | 约 16.59 美元是已追踪的 7 家 AI 公司，其中 3.57 美元是 NVDA。其余 53.41 美元分布在其他美国股票中，也包含其他科技公司。VTI 在 9/30 持有 3,519 只股票。[Vanguard 季末概况](https://workplace.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0970.pdf) |
| BRK-B | 11% → 10% | 1 个百分点 | 保险、铁路、能源等经营业务及管理层的资本配置。9/30 保险及其他业务持有的现金、等价物和美国短债扣除待结算采购款后合计 3,523 亿美元。股东通过股价分享收益，不能自行调动这笔现金。[Berkshire 10-Q](https://www.sec.gov/Archives/edgar/data/1067983/000119312526452412/brka-20260930.htm) |
| XLV | 6% → 5% | 1 个百分点 | 相当于减少 **六分之一** 的医疗专属仓位。11/18 基金中制药占 37.28%、生物技术占 20.04%，其经营驱动包括临床结果、药价和支付政策。市场整体下跌时医疗股票仍可下跌。[State Street 基金与行业配置](https://www.ssga.com/us/en/intermediary/etfs/state-street-health-care-select-sector-spdr-etf-xlv) |
| SGOV | 11% → 10% | 1 个百分点 | 可用于季度再平衡的短债从 770 美元减至 700 美元。11/18 有效久期 0.11 年，30 日 SEC 收益率 3.89%。若该收益率持续一年，少配的 70 美元对应约 2.72 美元收入，同时失去这部分低波动资产。[iShares 基金数据](https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf) |
| MSFT | 7% → 6% | 0 个百分点 | 把一部分 Azure、企业软件业务及 OpenAI 间接权益转给 Anthropic。微软 9/30 披露其持有 OpenAI 约 24% 的按转换口径权益；计算微软市值中由这笔权益贡献的比例还需要 OpenAI 的股权估值。[Microsoft 10-Q](https://www.sec.gov/Archives/edgar/data/789019/000119312526436133/msft-20260930.htm) |

**VTI 的交叉持仓。** Vanguard 9/30 列出 NVDA 占 7.1%，其余 6 家合计 19.5%。仓库按股价相对 VTI 的变化推至 11/13，得到 NVDA 占 5.1055%、7 家合计 23.7050%。表中每 70 美元分别乘以这两个估计值；它们和 11/19 的基金实际持仓可以不同。[Vanguard 季末概况](https://workplace.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0970.pdf) · [仓库计算结果](../claude_analysis_20261114/out/summary.json)

Vanguard 在 11/11 预计，VTI 跟踪的指数可在 IPO 后第 5 个交易日收盘后纳入 ANT，初始权重约 0.05%–0.15%。这是发行前按假设流通市值测算的区间。若 VTI 权重是 25%，对应组合中 0.0125%–0.0375% 的 ANT，在 7,000 美元预算中仅约 0.88–2.63 美元。未来核算直接加间接 ANT 仓位时应用实际成分权重。[Vanguard 对 ANT 纳入指数的说明](https://advisors.vanguard.com/insights/article/anthropics-ipo-puts-index-rules-in-the-spotlight)

同样配置 1% ANT，组合相对原方案的期间收益变化等于 `1% ×（ANT 回报 − 资金来源回报）`。例如，假设 ANT 跌 50%、VTI 跌 20%、SGOV 持平，VTI 拨款会比原方案少 21 美元，SGOV 拨款会少 35 美元。两种方案里的 ANT 都亏了 35 美元，差别来自原资产在同一期间的表现。此例用于说明损益机制，各项跌幅均为假设。
