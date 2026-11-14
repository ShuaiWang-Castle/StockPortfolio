import pandas as pd,numpy as np,json,pathlib
D=pathlib.Path('/workspace/scratch/f7bbb71d24eb/data_audit')
p=pd.read_csv(D/'adjusted_close.csv',index_col=0,parse_dates=True).loc['2022-01-03':'2022-10-12']
w=pd.Series(json.load(open('/workspace/scratch/f7bbb71d24eb/review_repo/claude_analysis_20261113/out_FINAL.json'))['FINAL'])
p=p[w.index]
def calc(mode):
 holdings=w.copy()/w.sum();v=[float(holdings.sum())];dates=[p.index[0]];contrib=[];rebs=[]
 for i in range(1,len(p)):
  returns=p.iloc[i]/p.iloc[i-1]-1
  pnl=holdings*returns
  holdings+=pnl;value=holdings.sum()
  v.append(float(value));dates.append(p.index[i]);contrib.append({'date':p.index[i],**pnl.to_dict()})
  end = i < len(p)-1 and p.index[i].month!=p.index[i+1].month
  first=p.index[i].month!=p.index[i-1].month
  if (mode=='month_end' and end) or (mode=='first_close' and first):
   rebs.append(str(p.index[i].date()));holdings=w/w.sum()*value
 nav=pd.Series(v,index=dates,name=mode)
 cont=pd.DataFrame(contrib).set_index('date')
 monthly=cont.resample('ME').sum();monthly['total']=monthly.sum(axis=1)
 monthly.to_csv(D/f'stress_contributions_{mode}.csv')
 return {'return':float(nav.iloc[-1]-1),'mdd':float((nav/nav.cummax()-1).min()),'rebalance_dates':rebs,'dollar_contributions':cont.sum().to_dict()},nav,monthly
out={};paths=[];monthly={}
for m in ['buy_hold','month_end','first_close']:
 out[m],nav,month=calc(m);paths.append(nav);monthly[m]=month
pd.concat(paths,axis=1).to_csv(D/'stress_paths.csv')
monthdiff=pd.concat({m:monthly[m]['total'] for m in monthly},axis=1);monthdiff['first_minus_end']=monthdiff['first_close']-monthdiff['month_end'];monthdiff['first_minus_hold']=monthdiff['first_close']-monthdiff['buy_hold'];monthdiff.to_csv(D/'stress_monthly_nav_pnl_differences.csv')
json.dump(out,open(D/'stress_independent.json','w'),indent=2)
print(json.dumps(out,indent=2));print(monthdiff)
