"""Read-only portfolio review of StockPortfolio PR #1, SHA b13c216e.

No forward-return estimate. Prices: USD adjusted close (dividend/split adjusted).
All portfolio paths include initial NAV=1. No trading costs or tax estimates.
Quarterly/monthly convention: reset at the prior period's last close, so the
first return in the new period has target weights. 'claude_monthly' deliberately
matches js/04_backtest.js: reset AFTER the first trading day's return.
"""
from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
OUT = BASE / 'review_results'
OUT.mkdir(exist_ok=True)
P = pd.read_csv(BASE/'data_audit/adjusted_close.csv',index_col=0,parse_dates=True)
CLAUDE = BASE/'reference_inputs' if (BASE/'reference_inputs').exists() else BASE/'review_repo/claude_analysis_20261113'
AI = ['NVDA','TSM','AVGO','MU','GOOGL','META','MSFT','AMZN']
C = {'NVDA':.09,'TSM':.10,'AVGO':.06,'MU':.05,'GOOGL':.11,'META':.08,'MSFT':.12,'AMZN':.09,
     'BTAL':.08,'XLP':.06,'KO':.06,'JNJ':.06,'XOM':.04}
B = {'VTI':.35,'NVDA':.15,'GOOGL':.15,'MSFT':.10,'META':.05,'BRK-B':.10,'XLV':.05,'SGOV':.05}
E = {**B,'NVDA':.10,'SGOV':.10}
def transfer(w,source,dest,amt):
    o=w.copy();o[source]=o.get(source,0)-amt;o[dest]=o.get(dest,0)+amt
    assert min(o.values())>=-1e-12
    return {k:v for k,v in o.items() if v>1e-12}
def common_nvda(w,new):
    o=w.copy();other=[k for k in AI if k!='NVDA' and k in o]
    total=sum(o[k] for k in other);delta=new-o['NVDA']
    for k in other:o[k]*=(total-delta)/total
    o['NVDA']=new
    return o
PORTS={
 'Claude':C,'conviction8':B,'entry':E,'VTI':{'VTI':1.0},
 'Claude_BTAL_to_SGOV':transfer(C,'BTAL','SGOV',.08),
 'conviction8_BTAL_cash_first':transfer(transfer(B,'SGOV','BTAL',.05),'VTI','BTAL',.03),
 'conviction8_BTAL_VTI_only':transfer(B,'VTI','BTAL',.08),
 'entry_BTAL_cash_first':transfer(E,'SGOV','BTAL',.08),
 'Claude_NVDA15':common_nvda(C,.15),
 'Claude_NVDA10':common_nvda(C,.10),
 'conviction8_NVDA9_cash':transfer(B,'NVDA','SGOV',.06),
 'conviction8_NVDA9_VTI':transfer(B,'NVDA','VTI',.06),
 'conviction8_proxy':{'SPY':.35,'NVDA':.15,'GOOGL':.15,'MSFT':.10,'META':.05,'BRK-B':.10,'XLV':.05,'BIL':.05},
 'entry_proxy':{'SPY':.35,'NVDA':.10,'GOOGL':.15,'MSFT':.10,'META':.05,'BRK-B':.10,'XLV':.05,'BIL':.10},
 'SPY':{'SPY':1.0},
}
# Attribution path: each step keeps NVDA=9%. The chosen financing path is
# explicit, not a unique causal decomposition. B' = B after NVDA->SGOV 6pp.
q=PORTS['conviction8_NVDA9_cash'].copy()
# Swap 35% VTI into the other seven Claude AI issuers, pro rata to C's 61%.
v=q.pop('VTI')
for k in AI:
    if k!='NVDA':q[k]=q.get(k,0)+v*C[k]/.61
PORTS['path_replace_VTI_by_AI7']=q.copy()
# Now set exactly the final AI sleeve (70% total), retain baseline defensive
# BRK/XLV 15%, and put residual in SGOV 15%.
q={k:C[k] for k in AI};q.update({'BRK-B':.10,'XLV':.05,'SGOV':.15})
PORTS['path_Claude_AI_original_defense']=q
# C without BTAL follows by swapping this 30% defense into XLP/KO/JNJ/XOM/SGOV.
assert all(abs(sum(w.values())-1)<1e-10 for w in PORTS.values())

WINDOWS={
 'three_year':('2023-11-13','2026-11-13'),
 'stress2022':('2022-01-03','2022-10-12'),
 'full_year2022':('2021-12-31','2022-12-30'),
 'election_2d':('2026-11-03','2026-11-05'),
 'election_full':('2026-11-03','2026-11-13'),
 'drawdown_oct':('2026-10-06','2026-11-13'),
 'risk_rebound':('2025-06-30','2026-06-30'),
 '2024':('2023-12-29','2024-12-31'),
 '2025':('2024-12-31','2025-12-31'),
 '2026ytd':('2025-12-31','2026-11-13'),
 'pre_2026_event':('2023-11-13','2026-11-03'),
}
def path(w,start,end,rule='quarterly'):
    names=list(w);z=P.loc[start:end,names]
    assert len(z)>1 and str(z.index[0].date())==start and str(z.index[-1].date())==end
    assert z.notna().all().all()
    target=np.array([w[k] for k in names],float)
    hold=target.copy();v=[1.0];wr=[target.copy()]
    for i in range(1,len(z)):
        prev,cur=z.index[i-1],z.index[i]
        month=cur.to_period('M')!=prev.to_period('M')
        quarter=cur.to_period('Q')!=prev.to_period('Q')
        if (rule=='monthly' and month) or (rule=='quarterly' and quarter):hold=hold.sum()*target
        wr.append(hold/hold.sum())
        hold*=z.iloc[i].to_numpy()/z.iloc[i-1].to_numpy()
        v.append(hold.sum())
        if rule=='claude_monthly' and month:hold=hold.sum()*target
    return pd.Series(v,index=z.index,name='NAV'),pd.DataFrame(wr,index=z.index,columns=names)

def metrics(v):
    r=v.pct_change().iloc[1:];dd=v/v.cummax()-1;n=len(r)
    tail=r.nsmallest(math.ceil(.05*n))
    return dict(n=n,cumulative_return=float(v.iloc[-1]-1),
       realized_vol=float(r.std(ddof=1)*np.sqrt(252)),max_drawdown=float(dd.min()),
       mdd_date=str(dd.idxmin().date()),es95_daily=float(tail.mean()),worst_day=float(r.min()))

rows=[];paths={};weights_path={}
for window,(start,end) in WINDOWS.items():
    for rule in ['quarterly','monthly','buy_hold','claude_monthly']:
        for name,w in PORTS.items():
            v,wr=path(w,start,end,rule)
            rows.append(dict(window=window,rule=rule,portfolio=name,**metrics(v)))
            if window=='three_year' and rule=='quarterly':paths[name]=v;weights_path[name]=wr
M=pd.DataFrame(rows);M.to_csv(OUT/'metrics.csv',index=False)
pd.DataFrame(paths).to_csv(OUT/'quarterly_nav_three_year.csv',index_label='Date')
pd.DataFrame({name:path(w,*WINDOWS['stress2022'],'quarterly')[0] for name,w in PORTS.items()}).to_csv(OUT/'quarterly_nav_stress2022.csv',index_label='Date')

R=P.loc['2023-11-13':'2026-11-13'].pct_change(fill_method=None).iloc[1:]
LOG=np.log(P.loc['2023-11-13':'2026-11-13']).diff().iloc[1:]
assert len(R)==753
S=R.cov()*252
SigmaLog=LOG.cov()*252
statrows=[];rcrows=[];tails=[]
for name,w in PORTS.items():
    ww=pd.Series(w).reindex(R.columns,fill_value=0)
    covw=S@ww;s2=float(ww@covw);sp=np.sqrt(s2)
    rp=R@ww
    dr=paths[name].pct_change().iloc[1:]
    statrows.append(dict(portfolio=name,vol_simple=float(sp),vol_log=float(np.sqrt(ww@SigmaLog@ww)),
       beta_VTI=float(covw['VTI']/S.loc['VTI','VTI']),beta_SPY=float(covw['SPY']/S.loc['SPY','SPY']),
       rho_NVDA=float(covw['NVDA']/np.sqrt(s2*S.loc['NVDA','NVDA'])),
       direct_AI_weight=sum(w.get(k,0) for k in AI)))
    for k in w:rcrows.append(dict(portfolio=name,ticker=k,weight=w[k],variance_share=float(ww[k]*covw[k]/s2),vol_contribution=float(ww[k]*covw[k]/sp)))
    for ref,pctl in [('NVDA',.1),('SMH',.05),('SMH',.1),('VTI',.05)]:
        mask=R[ref]<=R[ref].quantile(pctl)
        own=rp<=rp.quantile(pctl)
        tails.append(dict(portfolio=name,ref=ref,pctl=pctl,n=int(mask.sum()),
          ref_mean=float(R.loc[mask,ref].mean()),fixed_target_mean=float(rp[mask].mean()),
          quarterly_mean=float(dr[mask].mean()),positive_fraction=float((rp[mask]>0).mean()),
          coexceed_count=int((mask&own).sum()),conditional_coexceed=float(own[mask].mean())))
pd.DataFrame(statrows).to_csv(OUT/'target_risk.csv',index=False)
pd.DataFrame(rcrows).to_csv(OUT/'risk_contributions.csv',index=False)
pd.DataFrame(tails).to_csv(OUT/'conditional_tail.csv',index=False)

# Recover all reported proxy risk numbers from exactly the frozen rounded matrix.
L=(CLAUDE/'data/matrix_block.txt').read_text().rstrip('\n').splitlines()
tick=L[0].split(' ',1)[1].split(',');nn=len(tick)
kv=dict(v.split('=') for v in L[1].split(' ')[1:]);delta=float(kv['delta']);rbar=float(kv['rbar'])
vol=np.array(list(map(float,L[2].split(' ',1)[1].split(','))))
cor=np.eye(nn)
for i in range(1,nn):cor[i,:i]=list(map(float,L[4+i].split(',')));cor[:i,i]=cor[i,:i]
scov=cor*np.outer(vol,vol);target=rbar*np.outer(vol,vol);np.fill_diagonal(target,vol*vol)
lw=delta*target+(1-delta)*scov
st=pd.read_csv(CLAUDE/'data/stats_daily.csv').set_index('t')
frozen={}
for name,w in PORTS.items():
    proxy={}
    for k,v in w.items():
        k={'VTI':'SPY','SGOV':'BIL'}.get(k,k);proxy[k]=proxy.get(k,0)+v
    a=pd.Series(proxy).reindex(tick,fill_value=0).to_numpy()
    v=float(np.sqrt(a@lw@a))
    frozen[name]={'vol':v,'beta_spy':float((lw@a)[tick.index('SPY')]/lw[tick.index('SPY'),tick.index('SPY')]),
       'r22_rounded_inputs':float(sum(x*st.loc[k,'r22'] for k,x in proxy.items())),
       'rE1_rounded_inputs':float(sum(x*st.loc[k,'rE1'] for k,x in proxy.items()))}
json.dump(frozen,open(OUT/'frozen_matrix_recompute.json','w'),indent=2)

# Historical BTAL cost and reverse scenarios, no future carry estimate.
assetrows=[]
for wn,(start,end) in WINDOWS.items():
    for ticker in ['BTAL','SGOV','BIL','NVDA','VTI','SPY','XLP','KO','JNJ','XOM']:
        z=P.loc[start:end,ticker];v=z/z.iloc[0]
        assetrows.append(dict(window=wn,ticker=ticker,**metrics(v)))
pd.DataFrame(assetrows).to_csv(OUT/'hedge_periods.csv',index=False)
btal_corr=[]
for wn,(start,end) in WINDOWS.items():
    r=P.loc[start:end,['BTAL','NVDA','SMH','VTI']].pct_change(fill_method=None).iloc[1:]
    if len(r)>20:
        btal_corr.append(dict(window=wn,n=len(r),rho_NVDA=r['BTAL'].corr(r['NVDA']),rho_SMH=r['BTAL'].corr(r['SMH']),rho_VTI=r['BTAL'].corr(r['VTI'])))
pd.DataFrame(btal_corr).to_csv(OUT/'btal_correlations.csv',index=False)

# Paired stationary-block resampling: uncertainty in historical vol DIFFERENCES.
# These are not forward-return scenarios and do not estimate expected returns.
names=['Claude','conviction8','entry','Claude_BTAL_to_SGOV','conviction8_BTAL_cash_first','entry_BTAL_cash_first']
RR=pd.DataFrame(paths)[names].pct_change().iloc[1:].to_numpy()
gen=np.random.default_rng(20261113);nn=len(RR);out=[]
pairs=[('Claude','conviction8'),('Claude','entry'),('Claude','Claude_BTAL_to_SGOV'),
       ('conviction8_BTAL_cash_first','conviction8'),('entry_BTAL_cash_first','entry')]
draw={pair:[] for pair in pairs}
for _ in range(2000):
    inds=np.empty(nn,dtype=int);inds[0]=gen.integers(nn)
    restart=gen.random(nn)<.05;starts=gen.integers(nn,size=nn)
    for t in range(1,nn):inds[t]=starts[t] if restart[t] else (inds[t-1]+1)%nn
    sv=RR[inds].std(axis=0,ddof=1)*np.sqrt(252)
    for a,b in pairs:draw[(a,b)].append(sv[names.index(a)]-sv[names.index(b)])
for (a,b),ds in draw.items():
    out.append(dict(a=a,b=b,estimate=float((RR[:,names.index(a)].std(ddof=1)-RR[:,names.index(b)].std(ddof=1))*np.sqrt(252)),
       low=float(np.quantile(ds,.025)),high=float(np.quantile(ds,.975)),n_boot=2000,mean_block=20))
json.dump(out,open(OUT/'vol_difference_bootstrap.json','w'),indent=2)

json.dump(PORTS,open(OUT/'weights.json','w'),indent=2)
meta={'reviewed_sha':'b13c216e6d4394f25e18d58f49eaf367f1e32ab5','price_input_sha256':hashlib.sha256((BASE/'data_audit/adjusted_close.csv').read_bytes()).hexdigest(),
 'windows':WINDOWS,'primary_rebalancing':'calendar quarter end, BEFORE first return in new quarter; initial NAV=1',
 'returns':'USD adjusted-close simple daily returns; no duplicate dividend addition',
 'risk_estimator':'sample covariance ddof=1, common 753 daily returns; frozen Claude LW separately reproduced',
 'stress':'2022 values are retrospective historical scenarios, not true out-of-sample validation',
 'forward_returns':'not estimated; all returns are historical',
 'BTAL_financing':'conviction8 cash first: SGOV -5pp and VTI -3pp. Entry: SGOV -8pp. VTI-only sensitivity: VTI -8pp.',
 'matched_NVDA':'Claude_NVDA15/10 set direct NVDA to 15/10% and proportionally reduce other 7 AI issuers, holding AI 70% and defense 30%',
 'caveats':['No transaction costs, tax, spread or FX effects. ETF net price performance already includes fund expenses.',
 'Weights selected with 2026 information; all earlier results are retrospective, including 2022.',
 'Original Claude raw 52-asset file is missing. This independent 20-asset price reconstruction matches frozen overlap to displayed precision.',
 'Paired stationary bootstrap is historical sampling sensitivity conditional on selected portfolios, not a correction for selection bias.']}
json.dump(meta,open(OUT/'methodology.json','w'),indent=2)
print('THREE-YEAR PRIMARY')
print(M[(M.window=='three_year')&(M.rule=='quarterly')][['portfolio','realized_vol','max_drawdown','es95_daily']].to_string(index=False))
print('STRESS PRIMARY')
print(M[(M.window=='stress2022')&(M.rule.isin(['quarterly','buy_hold','monthly','claude_monthly']))].pivot(index='portfolio',columns='rule',values='cumulative_return').to_string())
print('BOOTSTRAP',json.dumps(out,indent=2))
