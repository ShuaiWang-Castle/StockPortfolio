# 黄仁勋回任概率、NVIDIA 的竞争优势与 NVDA 首次配置

Codex 由 OpenAI 开发。OpenAI 与 NVIDIA 有算力与商业合作。研究以 2026 年 11 月 20 日 **16:00 美东常规股市收盘**为价格截点。预测合约和盈利预期是在收盘后数分钟取得的快照，各自的获取时间见[来源记录](data/sources_web_20261120.json)。

**我的判断是按黄不会近期回任来评估 NVDA。** 在基础的 $7,000 一次性方案中，我倾向 **7.5% 直接仓位（$525）**。我把 11/19 已生效、直接限制若干海外数据中心先进芯片销售渠道的 BIS 规则纳入原出口条款。若 Shuai 原意限于专门点名 NVIDIA 的限制，则该规则单独不足以触发减仓，原方案仍给出 12.5%（$875）。这个选择取决于销售边界和个人愿意承担的风险。价格下跌、董事会拒绝复职均未单独构成原规则的触发项。[已采纳规则](../current_plan.json) · [法规原文](https://www.govinfo.gov/content/pkg/FR-2026-11-19/html/2026-23529.htm) · [组合计算](out/summary.json)

## 回任有多大可能

把“回去”定义为 NVIDIA 正式宣布黄重新担任永久 CEO。从 11/20 算起，我估计未来 **3 个月内为 2%–5%，12 个月内为 5%–10%**。这是累计主观区间，代表证据支持的判断精度，不能用来计算某一天的回归概率。作为董事或顾问参与、短期代理均排除。区间也允许先任命另一位永久 CEO、之后黄再回来，这种路径需要第二次人事决定。

- **压低概率的证据**是董事长代表董事会公开排除复任、已聘猎头、临时 CEO 确认该决定，董事长次日又向员工谈及信任问题。独立调查仍在进行，加州 11/19 发出调查传票。恢复他对调查证人的管理权，需要董事会解释为何改变判断。[公司托管的财报会逐字稿，第 2 页](https://s201.q4cdn.com/141608511/files/content_files/NVDA-3Q27-Earnings-Transcript.pdf) · [员工大会](https://www.wired.com/story/inside-nvidias-first-all-hands-without-jensen-huang-as-ceo/) · [加州总检察长公告](https://oag.ca.gov/node/633133)
- **保留非零概率的证据**是黄本人愿回任，亦有少数董事支持的匿名报道，特朗普在 11/20 继续公开支持。会实质上调判断的信号是董事会正式将黄列入候选，或独立调查出现有利结论且董事会重新评估人选。宣布另一位永久 CEO 或查实严重合规问题会明显下调判断。[黄本人声明](https://apnews.com/article/jensen-huang-return-nvidia-0f6d83fc6d97a30fc54bd66b5ac42eda) · [Semafor 采访](https://www.semafor.com/article/11/17/2026/some-nvidia-directors-push-to-bring-huang-back-despite-board-opposition) · [白宫记者会](https://apnews.com/article/540e631e21d003b83877ee4174cde2c0)
- **价格参照。** 11/20 16:09 ET，Kalshi 的“下一任正式 CEO 是黄仁勋”合约 Yes 买价 9 美分、卖价 10 美分、最近成交 10 美分，每份兑付最高 $1。合约截止 2029-01-01，正式公告即可，临时和代理不计，其他人先任正式 CEO 会改变结算结果。该价格为独立参照，不能直接套成一年内的频率。其他平台的“重新加入公司”题目还包括顾问、董事等职务。[Kalshi 交易所接口](https://api.elections.kalshi.com/trade-api/v2/markets/KXNVDACEO-29JAN-JENS) · [报价摘录](data/raw/next_ceo_market.json) · [较宽的 Polymarket 条款](https://polymarket.com/event/jensen-huang-rejoins-nvidia-byptptpt)

## 黄不回来，技术和经营会损失多少

**未来 1–4 个季度，我判断已部署产品的技术领先受影响有限；组织交接和出口许可能让销售提前受到影响。** CUDA 软件、工程团队、机架、网络及客户已完成的验证都能继续使用。CoreWeave 在 9 月确认 Cognition 已用 Rubin 跑生产负载，这是离任前的基础。离任后，Google Cloud 在 11/13 继续列出 Rubin A5X 供用户选择，韩国科技部长在与 NVIDIA 会谈后重申面向政府与业界的约 26 万颗 GPU 合作计划。该数字是原有计划，不是新增订单或已经交付的数量。一份谷歌产品公告与韩国的确认也不能代表所有客户。[CoreWeave 的客户部署](https://investors.coreweave.com/news/news-details/2026/CoreWeave-Delivers-NVIDIA-Vera-Rubin-NVL72-Performance-at-Production-Scale-Starting-With-Cognition/default.aspx) · [Google Cloud 11/13 技术更新](https://cloud.google.com/blog/topics/hpc/whats-new-in-hpc-and-ai-at-sc26) · [韩国方面离任后的确认](https://en.yna.co.kr/view/AEN20261113008400320)

**未来 2–4 年，我会降低对领先幅度的确信。** 黄的作用包括取舍架构、预订产能、同步芯片与网络，以及让客户提前为下一代系统投资。这些能力要经过新一轮决策和交付才能验证。Kress 11/17 重申 Rubin Ultra 在 2027 年、Feynman 在 2028 年。要看两代产品是否按时达到客户可部署状态，大客户是否把原定工作量转给 TPU、Trainium 或 AMD，及同一模型在相同延迟和质量下，每美元、每瓦完成多少工作。Anthropic 已披露使用超过一百万颗 Trainium2 训练和服务 Claude，替代技术已有真实用量。缺少可比订单、毛利和全成本数据，不能可靠地把创始人缺席换算成若干个百分点的市场份额。[NVIDIA 11/17 电话会](https://s201.q4cdn.com/141608511/files/content_files/NVDA-3Q27-Earnings-Transcript.pdf) · [Anthropic 实际使用的算力](https://www.anthropic.com/news/anthropic-amazon-compute)

Q3 截至 10/25，整个季度都在黄任内。Q3 数据中心收入 $107.6B 与已开始交付的 Rubin 反映交接起点。离任后管理层给出的 Q4 收入指引为 $130B ±3%、GAAP 毛利率 71%–72%，FY28 收入增长框架约 75%。这些有待兑现。若季收入固定为 $130B，毛利率每降低一个百分点会少约 $1.30B 毛利，这个敏感性说明定价与替代的经济分量，不能用于估计其中多少由黄的去留造成。[公司财报](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Third-Quarter-Fiscal-2027/) · [公司电话会](https://s201.q4cdn.com/141608511/files/content_files/NVDA-3Q27-Earnings-Transcript.pdf)

## 今天跌了多少，还会不会跌

| 11/20 常规时段 | NVDA | SOXX 半导体 ETF | QQQ | SPY |
|---|---:|---:|---:|---:|
| 11/19 收盘 | $145.98 | $137.95 | $645.04 | $715.87 |
| 11/20 收盘 | **$125.53** | $123.40 | $608.45 | $690.43 |
| 收盘到收盘 | **−14.01%** | −10.55% | −5.67% | −3.55% |

NVDA 从 11/3 收盘 $206.69 跌 **39.27%**；从 11/17 财报公布前收盘 $155.46 跌 **19.25%**。单日比 SOXX 多跌 3.46 个百分点，只是一项相对收益观察；SOXX 本身持有 NVDA。单凭这个差额无法识别调查、创始人、出口政策或板块抛售各自的贡献。[Nasdaq 当日快照](data/raw/NVDA_info.json) · [Nasdaq 11/3–19 历史记录](data/raw/NVDA_historical.json) · [指数 ETF 输出](out/summary.json)

**接下来数周，我会把继续下跌作为实际需要承受的情景，盘面不足以判断下一个交易日涨跌。** 加州已送达传票，Reuters 11/20 援引两名知情者报道称 SEC 对公司的调查涉及会计，尚未披露具体科目或错报结论。特朗普 11/20 提到对海外建设数据中心施加限制或重税，讲话没有给出税率、生效文本与实施细则。这与 11/19 已生效的 BIS 许可新规是两件事。客户付款、出口许可、毛利率或盈利预期若恶化，下跌可以延续；稳定回款、指引兑现以及调查边界明确则有利于估值企稳。[Reuters 11/20 采访](https://in.marketscreener.com/news/nvidia-s-accounting-is-a-focus-of-us-sec-investigation-sources-say-ce785ed3dd8ff526) · [总统记者会报道](https://apnews.com/article/f1ac03b73d13445400eeed8631d9d879) · [已生效条文](https://www.govinfo.gov/content/pkg/FR-2026-11-19/html/2026-23529.htm)

**当前价格隐含的盈利门槛。** 收盘后取得的 Nasdaq 年度一致预期为 FY27 EPS $9.60、FY28 $16.09（各 18 份估计）。按剩余财年 72/365 天加权，NTM EPS 约 $14.81、NTM P/E **8.48×**。接口未给分析师最后更新日期或逐项会计调整，无法断言已经反映当天消息，亦未对预期 EPS 重复剔除非经营项。按 `价格 = 预期每股盈利 × 市盈率`，若两者从这里各下调 10%，对应 **$101.68（−19%）**；若 EPS 稳定而倍数修复 15%，对应 **$144.36（+15%）**。这是同一盈利口径上的静态情景，非点位预测。[Nasdaq 盈利预期原始数据](data/raw/earnings_forecast.json) · [情景输出](out/summary.json)

以现有 2021-11 至今的复权样本，筛选过去单日跌至少 10%、此后有完整 20 个交易日的 NVDA 历史事件，仅有 **2 次**。从当日收盘买入，五日后分别为 +15.14%（2024/4/19）和 −1.49%（2025/1/27）。这两个样本既未匹配当时的估值，也未匹配公司治理和行业环境，无法推出此次会持续下跌或立即反弹的可靠频率。[复算所用事件与后续回报](out/summary.json)

## $7,000 的首次配置怎么选

下表使用原定一次买入组合，不计尚待决定的 ANT。为使比较只反映 NVDA 仓位，三档都把从 12.5% 释放的资金，按既定 ERC（等风险贡献）份额分给其余七家 AI 公司。10% 取长期锚的数字，其余头寸依本次可比口径分配，并不等于完整的中性组合。三档均只做多。

| 直接 NVDA | 拟投入 | 含 VTI 的 NVDA 敞口 | NVDA 占组合风险 | 年化波动 | 若仅 NVDA 从买入价再跌 30% |
|---|---:|---:|---:|---:|---:|
| **7.5%** | **$525** | **8.57%** | **18.4%** | **17.18%** | **−$180** |
| 10% | $700 | 11.07% | 24.3% | 17.49% | −$233 |
| 12.5% | $875 | 13.57% | 30.1% | 17.83% | −$285 |

从 12.5% 选到 7.5%，差额 **$350** 分给其余 AI 七家。若只有 NVDA 跌 30%，损失少 **$105**；若只有 NVDA 涨 30%，收益也少 $105。若 AI 八家同时都跌 30%，其余发行人不动，三档均约损失 **$1,105**。因此换仓处理的是对 NVIDIA 单家公司的依赖，无法消除行业共跌。[权重、风险贡献与压力计算](out/summary.json)

若另行采纳上次讨论的 **3% ANT**（VTI 出 2pp、BRK-B 出 1pp），以同一因子模型做敏感性比较，NVDA 配 7.5% / 10% / 12.5% 时，NVDA 风险贡献约 **17.5% / 23.0% / 28.6%**，模型总波动 **18.02% / 18.33% / 18.67%**。若 AI 八家都跌 30%、ANT 跌 60%，其余不动，三种 NVDA 档位合计都约亏 **$1,222**。风险份额变小与美元损失减少是不同的概念。ANT 的模型用 AI8 等权日收益 × 1.25 加独立噪声，总年化波动假设为 70%，尚无足够上市记录验证。[此前 ANT 提案](https://github.com/ShuaiWang-Castle/StockPortfolio/pull/8) · [计算](out/summary.json)

**规则与行动。** 我倾向按业务实质解释“专门针对 NVIDIA 数据中心销售”，因为 BIS 新许可证直接影响公司所售的产品和若干境外销售渠道，即使规则也适用于其他厂商，也没有全面禁止销售。管理层在 11/17 已知道新规、仍维持增长框架，Q4 指引未计中国数据中心计算收入，具体增量损失待核实。若 Shuai 要求必须点名 NVIDIA，12.5% 仍是既定分支；在该解释下想先选 10% 属于另行修改拟议首配。对短线跌势或判断失误的担忧本身不改变计划。对下一份财报，我会先核对实际回款、Q4 指引兑现、出口影响和实名客户承诺；对下一代产品，查实际交付日期和跨平台成本。[既定规则](../current_plan.json) · [11/19 出口条款复核](https://github.com/ShuaiWang-Castle/StockPortfolio/pull/7) · [CFO 说明](https://s201.q4cdn.com/141608511/files/doc_financials/2027/Q327/Q3FY27-CFO-Commentary.pdf)

## 数据与复现

在仓库根目录运行 `python3 -I codex_analysis_20261120_b/analyze.py .`。先用原先 2023-11-14 至 2026-11-13 的 753 个日收益，断言复现组合年化波动 17.62% 与 NVDA 风险份额 30.3%。再用 11/13 同日复权价格比率衔接之后五个交易日（包括 MSFT 除息），按 2023-11-21 至 2026-11-20 的滚动三年样本重新估计。VTI 以已核过的 9/30 成分权重及相对价格近似漂移；11/20 VTI 中 NVDA 估计为 4.30%，与实时持仓报告可能有差异。其余 VTI 的收益每日按前一天权重剔除七家已识别发行人后计算。风险贡献为 Euler 方差份额，不是未来亏损概率。[输入来源](data/sources_web_20261120.json) · [离线脚本](analyze.py) · [完整性清单](manifest.json)
