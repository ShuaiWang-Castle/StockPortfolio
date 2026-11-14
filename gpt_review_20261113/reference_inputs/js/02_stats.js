// Per-asset daily statistics -> data/stats_daily.csv (SHA-256 71cdb945...). Executed in the same page after 01_fetch.js.
const D=window.__D; const T=Object.keys(D);
const cal=D['SPY'].d.slice(); const N=cal.length; const idx={}; cal.forEach((d,i)=>idx[d]=i);
const P={}; for(const t of T){const a=new Array(N).fill(NaN); const v=D[t]; for(let k=0;k<v.d.length;k++){const i=idx[v.d[k]]; if(i!==undefined) a[i]=v.a[k];} for(let i=1;i<N;i++){ if(isNaN(a[i])&&!isNaN(a[i-1])) a[i]=a[i-1]; } P[t]=a;}
window.__P=P; window.__cal=cal;
const R={}; for(const t of T){const a=P[t]; const r=new Array(N).fill(NaN); for(let i=1;i<N;i++){ if(a[i]>0&&a[i-1]>0) r[i]=Math.log(a[i]/a[i-1]); } R[t]=r;}
window.__R=R;
const firstIdx=ds=>{for(let i=0;i<N;i++) if(cal[i]>=ds) return i; return -1;};
const lastIdx=ds=>{let j=-1; for(let i=0;i<N;i++) if(cal[i]<=ds) j=i; return j;};
const i0=firstIdx('2023-11-13'); const L=N-1; window.__i0=i0;
function pairs(x,y,a,b){const X=[],Y=[]; for(let i=a;i<=b;i++){ if(!isNaN(x[i])&&!isNaN(y[i])){X.push(x[i]);Y.push(y[i]);} } return [X,Y];}
const mean=a=>a.reduce((s,v)=>s+v,0)/a.length;
function cov(X,Y){const mx=mean(X),my=mean(Y); let s=0; for(let k=0;k<X.length;k++) s+=(X[k]-mx)*(Y[k]-my); return s/(X.length-1);}
function corr(X,Y){return cov(X,Y)/Math.sqrt(cov(X,X)*cov(Y,Y));}
function quant(a,q){const s=a.slice().sort((u,v)=>u-v); const pos=(s.length-1)*q; const lo=Math.floor(pos), hi=Math.ceil(pos); return s[lo]+(s[hi]-s[lo])*(pos-lo);}
const pxAt=(t,ds)=>{const i=idx[ds]; return i===undefined?NaN:P[t][i];};
const iYE=lastIdx('2025-12-31'); const i1y=L-252;
const f=(v,d=3)=>(v===undefined||isNaN(v))?'':(+v).toFixed(d);
const rows=[];
const hdr='t,n,cagr,vol,skew,xkurt,mdd,dd52,r1y,ytd,rOct6,rE1,rE2,rE4,r22,bSPY,bSMH,bNVDA,cNVDA,cSMH,cSPY,cNVDA1y,cNVDAewm,dbSMH,ubSMH,tailSMH,lamL10,lamL05';
for(const t of T){
 const r=R[t]; const p=P[t];
 const rw=[]; for(let i=i0+1;i<=L;i++) if(!isNaN(r[i])) rw.push(r[i]);
 const n=rw.length; const m=mean(rw); const sd=Math.sqrt(cov(rw,rw));
 let sk=0,ku=0; for(const v of rw){sk+=((v-m)/sd)**3; ku+=((v-m)/sd)**4;} sk/=n; ku=ku/n-3;
 const p0=p[i0], pL=p[L]; const yrs=(new Date(cal[L])-new Date(cal[i0]))/(365.25*864e5);
 const cagr=(p0>0)?Math.pow(pL/p0,1/yrs)-1:NaN;
 let pk=-Infinity, mdd=0; for(let i=i0;i<=L;i++){ if(isNaN(p[i])) continue; pk=Math.max(pk,p[i]); mdd=Math.min(mdd,p[i]/pk-1);}
 let hi52=-Infinity; for(let i=L-251;i<=L;i++) if(!isNaN(p[i])) hi52=Math.max(hi52,p[i]); const dd52=pL/hi52-1;
 const r1y=pL/p[i1y]-1, ytd=pL/p[iYE]-1;
 const rOct6=pL/pxAt(t,'2026-10-06')-1, rE1=pxAt(t,'2026-11-05')/pxAt(t,'2026-11-03')-1, rE2=pL/pxAt(t,'2026-11-03')-1, rE4=pL/pxAt(t,'2026-11-05')-1;
 const r22=pxAt(t,'2022-10-12')/pxAt(t,'2022-01-03')-1;
 const B=(x)=>{const [X,Y]=pairs(r,R[x],i0+1,L); return [cov(X,Y)/cov(Y,Y), corr(X,Y)];};
 const [bSPY,cSPY]=B('SPY'), [bSMH,cSMH]=B('SMH'), [bNVDA,cNVDA]=B('NVDA');
 const [X1,Y1]=pairs(r,R['NVDA'],L-251,L); const cNVDA1y=corr(X1,Y1);
 const lam=0.97; let sxx,syy,sxy; { const [Xa,Ya]=pairs(r,R['NVDA'],i0+1,i0+60); sxx=cov(Xa,Xa); syy=cov(Ya,Ya); sxy=cov(Xa,Ya); }
 for(let i=i0+61;i<=L;i++){ const x=r[i], y=R['NVDA'][i]; if(isNaN(x)||isNaN(y)) continue; sxx=lam*sxx+(1-lam)*x*x; syy=lam*syy+(1-lam)*y*y; sxy=lam*sxy+(1-lam)*x*y; }
 const cEW=sxy/Math.sqrt(sxx*syy);
 const [Xs,Ys]=pairs(r,R['SMH'],i0+1,L); const dX=[],dY=[],uX=[],uY=[]; for(let k=0;k<Xs.length;k++){ if(Ys[k]<0){dX.push(Xs[k]);dY.push(Ys[k]);} else if(Ys[k]>0){uX.push(Xs[k]);uY.push(Ys[k]);} }
 const db=cov(dX,dY)/cov(dY,dY), ub=cov(uX,uY)/cov(uY,uY);
 const q05=quant(Ys,0.05), q10=quant(Ys,0.10); let s=0,c=0; for(let k=0;k<Xs.length;k++) if(Ys[k]<=q05){s+=Xs[k];c++;} const tailm=Math.exp(s/c)-1;
 const qx10=quant(Xs,0.10), qx05=quant(Xs,0.05); let a10=0,b10=0,a05=0,b05=0; for(let k=0;k<Xs.length;k++){ if(Ys[k]<=q10){b10++; if(Xs[k]<=qx10) a10++;} if(Ys[k]<=q05){b05++; if(Xs[k]<=qx05) a05++;} }
 rows.push([t,n,f(cagr),f(sd*Math.sqrt(252)),f(sk,2),f(ku,1),f(mdd),f(dd52),f(r1y),f(ytd),f(rOct6),f(rE1),f(rE2),f(rE4),f(r22),f(bSPY,2),f(bSMH,2),f(bNVDA,2),f(cNVDA,2),f(cSMH,2),f(cSPY,2),f(cNVDA1y,2),f(cEW,2),f(db,2),f(ub,2),f(tailm),f(a10/b10,2),f(a05/b05,2)].join(','));
}
const txt=hdr+'\n'+rows.join('\n'); window.__A=txt;
const raw=JSON.stringify(T.map(t=>[t,D[t].d,D[t].a]));
const h=await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw)); const hx=[...new Uint8Array(h)].map(b=>b.toString(16).padStart(2,'0')).join(''); window.__hash=hx;
