"""Cash-flow basis and EPS timing sensitivities; no expected-return estimate."""
from pathlib import Path
import ast, json
import numpy as np
import pandas as pd
from scipy.optimize import brentq
BASE=Path(__file__).resolve().parent
SRC=BASE/'reference_inputs' if (BASE/'reference_inputs').exists() else BASE/'review_repo/claude_analysis_20261113'
tree=ast.parse((SRC/'analysis.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='V' for t in n.targets))
V=eval(compile(ast.Expression(node.value),'<frozen V assignment>','eval'),{'np':np})
A=pd.read_csv(SRC/'data/stats_daily.csv').set_index('t')
close=pd.read_csv(BASE/'data_audit/close.csv',index_col=0)
def solve(pe,r,first_exponent=1):
    def residual(g):
        cash=sum((1+g)**(t-1+first_exponent)/(1+r)**t for t in range(1,11))
        terminal=(1+g)**(9+first_exponent)*1.03/((r-.03)*(1+r)**10)
        return cash+terminal-pe
    return brentq(residual,-.5,1.5)
out=[]
for name in ['NVDA','TSM','MU']:
    pp,pdte,mc,fpe,pe,rev,oi,ebitda,ni,ocf,capex,fcf,nc,roic=V[name]
    price=float(close.loc['2026-11-13',name]);scale=price/pp
    r=.0486+(.67*A.loc[name,'bSPY']+.33)*.045
    x=fpe*scale
    out.append({'ticker':name,'rescaled_forward_PE':x,'discount_rate_assumption':r,
     'original_forward_EPS_g':solve(x,r),'TTM_FCF_g':solve((mc*scale-nc)/fcf,r),
     'forward_EPS_times_FCF_conversion_g':solve(x/(fcf/ni),r),
     'forward_EPS_first_year_timing_g':solve(x,r,0),
     'fcf_to_net_income':fcf/ni})
df=pd.DataFrame(out);df.to_csv(BASE/'review_results/valuation_sensitivity.csv',index=False)
print(df.to_string(index=False))
