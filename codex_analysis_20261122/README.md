# 11 月 20 日美股急跌与信用市场

利益关系披露：Codex 由 OpenAI 开发。OpenAI 属于本研究涉及的 AI 基础设施融资行业。

**截至美东 2026-11-22 周日下午，股市已广泛回调，部分压力已传至企业信用市场。现有隔夜融资数据仍不足以判定系统性金融危机已经形成。拟议组合的空头比例为 0%。** 周日现货休市，以下股票数据采用 11/20 常规时段收盘。研究不涉及实际持仓。

## 急跌的范围

| 指数 | 11/20 收盘 | 当日 | 当周 |
|---|---:|---:|---:|
| 标普 500 | 6,910.39 | −3.70% | −8.61% |
| 纳斯达克综合 | 22,617.73 | −5.28% | −10.02% |
| 罗素 2000 小盘股 | 2,581.79 | −2.76% | −7.48% |
| 费城半导体 | 8,408.59 | −10.73% | −17.13% |

自 10/6 收盘高点至周五，标普下跌 11.62%，纳指下跌 18.05%。VIX 从前周五 19.30 升至 35.89，说明期权市场对未来 30 天波动的定价显著上升。其数值不能换算为下周下跌概率。周涨跌以 11/13 收盘为基准，日涨跌以 11/19 收盘为基准，均为价格回报。[美联社收盘核验](https://apnews.com/article/c10b797a17c2acf37924d834efebe135) · [Cboe](https://www.cboe.com/tradable-products/vix/vix-historical-data) · [数据与来源](data/sources_web_20261122.json) · [计算输出](out/summary.json)

## 股价下跌是否已影响信用创造

| 观察窗口 | 事实 | 可以支持的判断 |
|---|---|---|
| 11/13 至 11/19 收盘 | 美国高收益债期权调整利差（OAS）从 323 升至 352 bp，投资级从 89 升至 94 bp | 较弱借款人承受更大的风险溢价。两条序列落后周五股市一个交易日。 |
| 11/19 的二级市场贷款拍卖 | ING 出售约 5 亿美元存量数据中心贷款，报价未达到成交条件，转为逐家商谈 | 买卖双方估值出现分歧。不能由此推断项目违约或所有新贷停发。 |
| 11/20 盘中 | 投资级企业信用违约互换指数 CDX 利差一度上升 2.9 bp 至 65.5 bp | 周五企业信用风险保险价格也上涨。该指数衡量信用保险成本，须与现券 OAS 分开比较。 |
| 11/19 隔夜利率、11/20 联储操作 | SOFR 3.91%，有效联邦基金利率 3.88%，差 3 bp。周五纽约联储常备回购于 08:30 ET 接受金额为零、13:45 ET 为 100 万美元 | 两场操作的需求低。该工具只覆盖合资格对手方，下午操作早于股市收盘。 |

资料来源为 [FRED 高收益债](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)、[FRED 投资级债](https://fred.stlouisfed.org/series/BAMLC0A0CM)、[Bloomberg 贷款拍卖](https://news.bloomberglaw.com/capital-markets/ings-500-million-data-center-loan-auction-stalls-on-low-bids)、[Bloomberg 信用衍生品](https://news.bloomberglaw.com/capital-markets/ai-credit-risk-gauges-worsen-as-tech-selloff-roils-markets)、[纽约联储回购操作](https://markets.newyorkfed.org/api/rp/results/search.json?startDate=2026-11-13&endDate=2026-11-20&operationTypes=repo)及[利率和操作原始数据](data/sources_web_20261122.json)。

系统性危机的传导路径是借款人难以再融资，杠杆机构为补抵押品出售资产，贷款人继而收紧更多行业的信贷。美联储 11 月金融稳定报告显示先进计算行业相关公开债务余额已超过 1.1 万亿美元，因而存在信用传导渠道。该报告的信息截至 10/28。下次需要同时核对非科技借款人的发债成败、两类现券利差能否企稳、隔夜资金价格与联储工具用量是否持续上升。FRED 排定于 11/23 更新两条 OAS，届时才有覆盖周五的观察机会。[美联储金融稳定报告 Box 2.2](https://www.federalreserve.gov/publications/files/financial-stability-report-20261113.pdf) · [FRED](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)

## 急跌之后的方向与拟议组合

以 1990 年起的标普 500 常规收盘价做描述性核对，选择与本周相近的 8% 为单周跌幅界限。本周之前共有 9 个触发周。保留前四个日历周无其他触发的观察后，剩 6 次，其中下一周上涨 5 次、四周后上涨 4 次。2008/10/03 当周暴跌后，标普下一周再跌 18.20%。同年 11/21 当周暴跌后，下一周反弹 12.03%。每周取美东当地最后一个有交易的日期，后续回报自各事件周收盘计算。本周没有后续结果，未计入分母。样本小、来自少数危机周期，且阈值参照当周跌幅选取，无法据此估计下周方向的概率。[全部事件及计算](out/summary.json) · [历史数据来源](data/sources_web_20261122.json)

拟议配置遵循只做多、无杠杆的约束，空头占比 0%。担心回撤的未投入资金可保留现金，仍可一次性决定投入规模。按公开拟议预算 7,000 美元、SGOV 占 11% 推算，其余股票敞口合计 6,230 美元。如果该部分下跌 10% 或 20% 且 SGOV 不变，组合分别损失 623 或 1,246 美元。上述是统一冲击假设。半导体集中敞口意味着真实损益取决于各标的跌幅。卖空需要判断方向及时间，价格急弹时空头可能因保证金压力被迫买回。[现行方案](../current_plan.json) · [SEC 卖空机制](https://www.sec.gov/investor/pubs/regsho.htm)

## 复现

从仓库根目录运行，仅使用 Python 3.10+ 标准库。

```sh
python3 -I codex_analysis_20261122/analyze.py .
```

[来源登记](data/sources_web_20261122.json)标记进入计算的数字、原始 URL 与获取时间。纽约联储 API 响应逐字保存在 data/。指数行情保存用于核验的选定观察值，历史研究保存全部触发周的相关收盘价。用登记中的 SP500_history 链接另行获取日行情 JSON 后，运行下面的独立提取步骤，与冻结的 [weekly_events.json](data/weekly_events.json) 比较，可核对是否遗漏触发周。完整行情的哈希对应获取时的响应，服务商后续修订及响应元数据也会影响哈希。

```sh
python3 -I codex_analysis_20261122/extract_events.py /path/to/gspc_daily.json
```

[清单](manifest.json)记录输入哈希、产出字节数及 clean-export 复跑结果。
