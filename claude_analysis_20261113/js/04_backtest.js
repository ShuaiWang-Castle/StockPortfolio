// Monthly-rebalanced backtests, 2022 stress window, election windows, stationary block bootstrap (mean block 20d, 4000 paths, seed 42,
// de-meaned daily log returns + CAPM drift) -> data/backtest.json (SHA-256 78f6c006...). Executed after 02_stats.js.
const P=window.__P, cal=window.__cal; const N=cal.length, L=N-1; const idx={}; cal.forEach((d,i)=>idx[d]=i);
const PORT={"FINAL":{"NVDA":0.09,"TSM":0.10,"AVGO":0.06,"MU":0.05,"GOOGL":0.11,"META":0.08,"MSFT":0.12,"AMZN":0.09,"BTAL":0.08,"XLP":0.06,"KO":0.06,"JNJ":0.06,"XOM":0.04},"AI60":{"NVDA":0.07373,"TSM":0.08374,"AVGO":0.04676,"MU":0.06043,"GOOGL":0.08773,"META":0.06961,"MSFT":0.10291,"AMZN":0.07509,"BTAL":0.08,"XLP":0.1,"KO":0.06,"JNJ":0.06,"XOM":0.07,"WMT":0.01925,"GLD":0.01075},"AI80":{"NVDA":0.10176,"TSM":0.11552,"AVGO":0.06448,"MU":0.0556,"GOOGL":0.12104,"META":0.096,"MSFT":0.142,"AMZN":0.1036,"BTAL":0.08,"KO":0.02,"JNJ":0.06,"XOM":0.04},"AI100":{"NVDA":0.1272,"TSM":0.1444,"AVGO":0.0806,"MU":0.0695,"GOOGL":0.1513,"META":0.12,"MSFT":0.1775,"AMZN":0.1295},"HRP13":{"MU":0.00901,"AVGO":0.00964,"NVDA":0.01115,"TSM":0.02612,"MSFT":0.04552,"META":0.02158,"GOOGL":0.07503,"AMZN":0.07427,"XOM":0.13667,"BTAL":0.11161,"JNJ":0.14579,"XLP":0.20043,"KO":0.13318},"NVDA":{"NVDA":1},"SMH":{"SMH":1},"SPY":{"SPY":1},"QQQ":{"QQQ":1},"EW_AI10":{"NVDA":0.1,"AVGO":0.1,"TSM":0.1,"AMD":0.1,"MU":0.1,"GOOGL":0.1,"META":0.1,"MSFT":0.1,"AMZN":0.1,"VRT":0.1},"NVDA_SBUX":{"NVDA":0.5,"SBUX":0.5},"NVDA_AMZN":{"NVDA":0.5,"AMZN":0.5},"NVDA_KO":{"NVDA":0.5,"KO":0.5},"NVDA_BTAL":{"NVDA":0.7,"BTAL":0.3}};
const MU={"FINAL":0.0935,"AI60":0.0884,"AI80":0.1003,"AI100":0.1166,"HRP13":0.0632,"NVDA":0.1367,"SMH":0.1351,"SPY":0.0936,"QQQ":0.1046,"EW_AI10":0.1276,"NVDA_SBUX":0.1112,"NVDA_AMZN":0.1225,"NVDA_KO":0.0925,"NVDA_BTAL":0.0986};
function bt(w,a,b){const n=Object.keys(w); let s=0; for(const k of n){ if(isNaN(P[k][a])) return null; s+=w[k]; } let hold=n.map(k=>w[k]/s); const V=[1]; let lm=cal[a].slice(0,7); for(let t=a+1;t<=b;t++){ let tot=0; for(let j=0;j<n.length;j++){ hold[j]*=P[n[j]][t]/P[n[j]][t-1]; tot+=hold[j]; } V.push(tot); const m=cal[t].slice(0,7); if(m!==lm){ hold=n.map(k=>w[k]/s*tot); lm=m; } } return V; }
function mdd(V){let pk=-1e9,m=0; for(const v of V){pk=Math.max(pk,v); m=Math.min(m,v/pk-1);} return m;}
function q(a,p){const s=a.slice().sort((x,y)=>x-y); const pos=(s.length-1)*p, lo=Math.floor(pos), hi=Math.ceil(pos); return s[lo]+(s[hi]-s[lo])*(pos-lo);}
let seed=42; const rnd=()=>{seed|=0; seed=seed+0x6D2B79F5|0; let t=Math.imul(seed^seed>>>15,1|seed); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296;};
const i0=idx['2023-11-13'], a22=idx['2022-01-03'], b22=idx['2022-10-12'];
const bil=P['BIL'][L]/P['BIL'][i0]; const yrs=(L-i0)/252; const rfc=Math.pow(bil,1/yrs)-1;
const res={}; const curves={}; const c22={}; const step=5;
for(const [k,w] of Object.entries(PORT)){
 const V=bt(w,i0,L); const r=[]; for(let t=1;t<V.length;t++) r.push(V[t]/V[t-1]-1);
 const n=r.length; const m=r.reduce((x,y)=>x+y,0)/n; const sd=Math.sqrt(r.reduce((x,y)=>x+(y-m)**2,0)/(n-1));
 const cagr=Math.pow(V[V.length-1],252/n)-1; const vol=sd*Math.sqrt(252);
 const dn=r.filter(x=>x<0); const dsd=Math.sqrt(dn.reduce((x,y)=>x+y*y,0)/n)*Math.sqrt(252);
 const v95=q(r,0.05); const cv95=r.filter(x=>x<=v95).reduce((x,y)=>x+y,0)/r.filter(x=>x<=v95).length;
 const r21=[]; for(let t=21;t<V.length;t++) r21.push(V[t]/V[t-21]-1); const m95=q(r21,0.05); const mc95=r21.filter(x=>x<=m95).reduce((x,y)=>x+y,0)/r21.filter(x=>x<=m95).length;
 let ew=0; const lr=r.map(x=>Math.log(1+x)); const init=lr.slice(0,60); ew=init.reduce((x,y)=>x+y*y,0)/60; for(let t=60;t<lr.length;t++) ew=0.97*ew+0.03*lr[t]*lr[t];
 const at=(d)=>V[idx[d]-i0];
 const V22=bt(w,a22,b22);
 const ml=lr.reduce((x,y)=>x+y,0)/lr.length; const z=lr.map(x=>x-ml); const drift=Math.log(1+MU[k])/252; const R1=[],MD=[]; seed=42;
 for(let pth=0;pth<4000;pth++){ let pos=Math.floor(rnd()*z.length); let cum=0, pk=0, md=0; for(let d=0;d<252;d++){ if(rnd()<0.05) pos=Math.floor(rnd()*z.length); else pos=(pos+1)%z.length; cum+=z[pos]+drift; pk=Math.max(pk,cum); md=Math.min(md,Math.exp(cum-pk)-1);} R1.push(Math.exp(cum)-1); MD.push(md); }
 res[k]={cagr,vol,sharpe:(cagr-rfc)/vol,sortino:(cagr-rfc)/dsd,mdd:mdd(V),worst:Math.min(...r),var95:v95,cvar95:cv95,var21:m95,cvar21:mc95,ewmaVol:Math.sqrt(ew*252),r22:V22?V22[V22.length-1]-1:null,mdd22:V22?mdd(V22):null,e1:at('2026-11-05')/at('2026-11-03')-1,e2:at('2026-11-13')/at('2026-11-03')-1,e3:at('2026-11-13')/at('2026-10-06')-1,b05:q(R1,0.05),b25:q(R1,0.25),b50:q(R1,0.5),b75:q(R1,0.75),b95:q(R1,0.95),pLoss:R1.filter(x=>x<0).length/R1.length,pL20:R1.filter(x=>x<-0.2).length/R1.length,pL30:R1.filter(x=>x<-0.3).length/R1.length,mddMed:q(MD,0.5),mdd05:q(MD,0.05)};
 if(['FINAL','AI100','NVDA','SMH','SPY','QQQ'].includes(k)){ curves[k]=V.filter((_,t)=>t%step===0||t===V.length-1).map(x=>+x.toFixed(4)); c22[k]=V22.filter((_,t)=>t%step===0||t===V22.length-1).map(x=>+x.toFixed(4)); }
}
const dates=[]; for(let t=0;t<=L-i0;t++){ if(t%step===0||t===L-i0) dates.push(cal[i0+t]); }
const d22=[]; for(let t=0;t<=b22-a22;t++){ if(t%step===0||t===b22-a22) d22.push(cal[a22+t]); }
const R4=x=>(x===null?null:+x.toFixed(4)); const out={rf3y:+rfc.toFixed(4),res:Object.fromEntries(Object.entries(res).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).map(([a,b])=>[a,R4(b)]))])),dates,curves,d22,c22};
window.__BT=JSON.stringify(out);
