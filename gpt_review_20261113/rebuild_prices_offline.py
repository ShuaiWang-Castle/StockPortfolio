"""Regenerate the 20-asset panel from included raw Yahoo JSONs, with no network."""
from pathlib import Path
import json
import pandas as pd
BASE=Path(__file__).resolve().parent
D=BASE/'data_audit'
tick=['NVDA','TSM','AVGO','MU','GOOGL','META','MSFT','AMZN','BTAL','XLP','KO','JNJ','XOM','VTI','SGOV','BRK-B','XLV','SPY','BIL','SMH']
adj={};close={}
for t in tick:
    j=json.load(open(D/'raw'/f'{t}.json'))['chart']['result'][0]
    assert j['meta']['currency']=='USD'
    dates=pd.to_datetime(j['timestamp'],unit='s',utc=True).tz_convert(None).normalize()
    adj[t]=pd.Series(j['indicators']['adjclose'][0]['adjclose'],index=dates)
    close[t]=pd.Series(j['indicators']['quote'][0]['close'],index=dates)
a=pd.DataFrame(adj).loc['2021-11-15':'2026-11-13'];c=pd.DataFrame(close).loc[a.index]
assert len(a)==1255 and a.notna().all().all() and c.notna().all().all()
a.to_csv(D/'adjusted_close.csv',index_label='Date');c.to_csv(D/'close.csv',index_label='Date')
print(a.shape,a.index[0],a.index[-1])
