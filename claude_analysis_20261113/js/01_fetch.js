// Executed in the user's Chrome on https://query1.finance.yahoo.com (same-origin fetch), 2026-11-13 after the close.
const T=["NVDA","AMD","AVGO","MU","INTC","TSM","ASML","MRVL","ANET","GOOGL","META","MSFT","AMZN","ORCL","AAPL","VRT","CEG","VST","ETN","PLTR","NOW","SBUX","MCD","COST","WMT","PG","KO","LLY","JNJ","UNH","ABBV","JPM","BRK-B","V","XOM","CVX","LMT","SPY","QQQ","SMH","XLP","XLV","XLU","XLE","GLD","TLT","IEF","BIL","BTAL","DBMF","USMV","BTC-USD"];
const out={}; const errs={};
const sleep=ms=>new Promise(s=>setTimeout(s,ms));
async function get(t){const u=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(t)}?range=5y&interval=1d&events=div%2Csplit&includeAdjustedClose=true`;
 for(let k=0;k<3;k++){try{const r=await fetch(u,{credentials:'include'}); if(!r.ok){errs[t]='HTTP '+r.status; await sleep(1000); continue;} const j=await r.json(); const res=j.chart.result[0]; const ts=res.timestamp; const q=res.indicators.quote[0]; const ac=res.indicators.adjclose?res.indicators.adjclose[0].adjclose:null; const d=[],a=[],c=[]; for(let i=0;i<ts.length;i++){const cl=q.close[i]; const aj=ac?ac[i]:cl; if(cl==null||aj==null) continue; d.push(new Date(ts[i]*1000).toISOString().slice(0,10)); a.push(aj); c.push(cl);} out[t]={d,a,c,cur:res.meta.currency,last:res.meta.regularMarketPrice,lt:res.meta.regularMarketTime}; delete errs[t]; return;}catch(e){errs[t]=String(e); await sleep(1000);}}}
for(let i=0;i<T.length;i+=6){await Promise.all(T.slice(i,i+6).map(get)); await sleep(250);}
window.__D=out;
// raw-data hash recorded in data/meta.json: SHA-256 of JSON.stringify(T.map(t=>[t,D[t].d,D[t].a])) (computed in 02_stats.js)
