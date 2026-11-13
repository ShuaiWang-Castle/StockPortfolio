// Sample correlation, Ledoit-Wolf (2004) constant-correlation intensity, EWMA(0.97) and 63-day rolling correlations
// -> data/matrix_block.txt (EWMA matrix block omitted from the file; SHA-256 23549f3f... covers the kept lines). Executed after 02_stats.js.
const R=window.__R, cal=window.__cal, i0=window.__i0; const T=Object.keys(R); const N=T.length; const L=cal.length-1;
const rowsIdx=[]; for(let i=i0+1;i<=L;i++){ let ok=true; for(const t of T){ if(isNaN(R[t][i])){ok=false;break;} } if(ok) rowsIdx.push(i); }
const TT=rowsIdx.length; const X=rowsIdx.map(i=>T.map(t=>R[t][i]));
const m=new Array(N).fill(0); for(const x of X) for(let j=0;j<N;j++) m[j]+=x[j]/TT;
const Y=X.map(x=>x.map((v,j)=>v-m[j]));
const S=[...Array(N)].map(()=>new Array(N).fill(0)); for(const y of Y) for(let i=0;i<N;i++){ const yi=y[i]; for(let j=0;j<=i;j++) S[i][j]+=yi*y[j]/TT; } for(let i=0;i<N;i++) for(let j=0;j<i;j++) S[j][i]=S[i][j];
const sd=S.map((r,i)=>Math.sqrt(r[i]));
let rbar=0,cnt=0; for(let i=0;i<N;i++) for(let j=0;j<i;j++){ rbar+=S[i][j]/(sd[i]*sd[j]); cnt++; } rbar/=cnt;
const P2=[...Array(N)].map(()=>new Array(N).fill(0)); const th=[...Array(N)].map(()=>new Array(N).fill(0));
for(const y of Y){ for(let i=0;i<N;i++){ const a=y[i]*y[i]-S[i][i]; for(let j=0;j<N;j++){ const b=y[i]*y[j]-S[i][j]; P2[i][j]+=b*b/TT; th[i][j]+=a*b/TT; } } }
let pi=0; for(let i=0;i<N;i++) for(let j=0;j<N;j++) pi+=P2[i][j];
let rho=0; for(let i=0;i<N;i++) rho+=P2[i][i];
for(let i=0;i<N;i++) for(let j=0;j<N;j++){ if(i===j) continue; rho+=(rbar/2)*(Math.sqrt(S[j][j]/S[i][i])*th[i][j]+Math.sqrt(S[i][i]/S[j][j])*th[j][i]); }
let gam=0; for(let i=0;i<N;i++) for(let j=0;j<N;j++){ const f=(i===j)?S[i][i]:rbar*sd[i]*sd[j]; gam+=(f-S[i][j])**2; }
const kappa=(pi-rho)/gam; const delta=Math.max(0,Math.min(1,kappa/TT));
const lam=0.97; const E=[...Array(N)].map(()=>new Array(N).fill(0)); for(let k=0;k<60;k++){ const x=X[k]; for(let i=0;i<N;i++) for(let j=0;j<=i;j++) E[i][j]+=x[i]*x[j]/60; }
for(let k=60;k<TT;k++){ const x=X[k]; for(let i=0;i<N;i++) for(let j=0;j<=i;j++) E[i][j]=lam*E[i][j]+(1-lam)*x[i]*x[j]; }
const lines=[]; lines.push('TICKERS '+T.join(',')); lines.push(`LW delta=${delta.toFixed(5)} rbar=${rbar.toFixed(5)} T=${TT} first=${cal[rowsIdx[0]]} last=${cal[rowsIdx[TT-1]]}`);
lines.push('VOL '+sd.map(v=>(v*Math.sqrt(252)).toFixed(5)).join(','));
lines.push('MEANLOG '+m.map(v=>(v*252).toFixed(5)).join(','));
lines.push('CORR'); for(let i=1;i<N;i++){ const r=[]; for(let j=0;j<i;j++) r.push((S[i][j]/(sd[i]*sd[j])).toFixed(3)); lines.push(r.join(',')); }
lines.push('EWMA'); for(let i=1;i<N;i++){ const r=[]; for(let j=0;j<i;j++) r.push((E[i][j]/Math.sqrt(E[i][i]*E[j][j])).toFixed(2)); lines.push(r.join(',')); }
lines.push('EWVOL '+T.map((t,i)=>(Math.sqrt(E[i][i]*252)).toFixed(4)).join(','));
const sel=['COST','KO','XLP','AMZN','SBUX','GLD','TLT','BTAL','XOM','GOOGL','SMH','SPY']; const jn=T.indexOf('NVDA'); const W=63; const dates=[]; const roll={}; sel.forEach(s=>roll[s]=[]);
for(let k=W;k<=TT;k+=5){ dates.push(cal[rowsIdx[k-1]]); for(const s of sel){ const j=T.indexOf(s); let mx=0,my=0; for(let q=k-W;q<k;q++){mx+=X[q][jn]/W; my+=X[q][j]/W;} let sxy=0,sxx=0,syy=0; for(let q=k-W;q<k;q++){ const a=X[q][jn]-mx, b=X[q][j]-my; sxy+=a*b; sxx+=a*a; syy+=b*b;} roll[s].push((sxy/Math.sqrt(sxx*syy)).toFixed(2)); } }
lines.push('ROLLDATES '+dates.join(',')); for(const s of sel) lines.push('ROLL '+s+' '+roll[s].join(','));
window.__B=lines.join('\n');
