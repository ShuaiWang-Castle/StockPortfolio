import urllib.request,urllib.parse,json,hashlib,datetime,pathlib,concurrent.futures
import pandas as pd,numpy as np
ROOT=pathlib.Path('/workspace/scratch/f7bbb71d24eb/data_audit')
OLD=pathlib.Path('/workspace/scratch/7569b1d31554/portfolio_refresh_20261113/market_data_extended')
p=pd.read_csv(OLD/'adjusted_close.csv',index_col=0)
q=pd.read_csv(OLD/'close.csv',index_col=0)
prov=json.load(open(OLD/'provenance.json'))
notes={'old_source_file':str(OLD/'adjusted_close.csv'),'old_source_sha256':hashlib.sha256((OLD/'adjusted_close.csv').read_bytes()).hexdigest(),'old_provenance':str(OLD/'provenance.json'),'fresh':{}}
PARAMS={'period1':1636070400,'period2':1794614400,'interval':'1d','events':'div,splits,capitalGains','includeAdjustedClose':'true'}
def fetch(t):
 u='https://query2.finance.yahoo.com/v8/finance/chart/'+t+'?'+urllib.parse.urlencode(PARAMS)
 f=ROOT/'raw'/f'{t}.json'
 if not f.exists():
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30)
  f.write_bytes(r.read())
 j=json.loads(f.read_bytes());x=j['chart']['result'][0]
 dates=pd.to_datetime(x['timestamp'],unit='s',utc=True).tz_convert('America/New_York').strftime('%Y-%m-%d')
 a=pd.Series(x['indicators']['adjclose'][0]['adjclose'],index=dates,name=t)
 c=pd.Series(x['indicators']['quote'][0]['close'],index=dates,name=t)
 n={'url':u,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'currency':x['meta']['currency'],'n':len(a),'start':a.index.min(),'end':a.index.max(),'raw_file':str(f),'adjustment':'Yahoo AdjClose, includes provider dividend/split adjustment; no forward filling','nulls':int(a.isna().sum())}
 return t,a,c,n
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for t,a,c,n in ex.map(fetch,['BTAL','XLP','BIL','SMH']):
  p[t]=a;q[t]=c;notes['fresh'][t]=n
wanted=['NVDA','TSM','AVGO','MU','GOOGL','META','MSFT','AMZN','BTAL','XLP','KO','JNJ','XOM','VTI','SGOV','BRK-B','XLV','SPY','BIL','SMH']
p=p[wanted].loc['2021-11-15':'2026-11-13'];q=q[wanted].loc[p.index]
notes['combined']={'columns':wanted,'shape':p.shape,'start':p.index.min(),'end':p.index.max(),'nulls':p.isna().sum().to_dict(),'base_price_date':'2023-11-13','estimate_return_dates':['2023-11-14','2026-11-13'],'estimate_n':len(p.loc['2023-11-14':]),'stress_base':'2022-01-03','stress_end':'2022-10-12'}
p.to_csv(ROOT/'adjusted_close.csv',index_label='Date');q.to_csv(ROOT/'close.csv',index_label='Date')
json.dump(notes,open(ROOT/'provenance.json','w'),indent=2)
a=pd.read_csv('/workspace/scratch/f7bbb71d24eb/review_repo/claude_analysis_20261113/data/stats_daily.csv',index_col=0)
r=np.log(p/p.shift(1)).loc['2023-11-14':'2026-11-13']
rows=[]
for t in wanted:
 rows.append({'ticker':t,'n':r[t].count(),'log_vol':r[t].std()*np.sqrt(252),'frozen_vol':a.loc[t,'vol'] if t in a.index else np.nan,'stress_bh':p.loc['2022-10-12',t]/p.loc['2022-01-03',t]-1,'frozen_stress_bh':a.loc[t,'r22'] if t in a.index else np.nan,'last_close':q.iloc[-1][t]})
check=pd.DataFrame(rows);check.to_csv(ROOT/'frozen_cross_check.csv',index=False)
print(json.dumps(notes['combined'],indent=2));print(check.to_string(index=False))
