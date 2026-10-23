import numpy as np
import pandas as pd

def wape(actual, pred):
    den=float(np.abs(actual).sum())
    return 0.0 if den==0 and float(np.abs(pred).sum())==0 else (100.0 if den==0 else float(np.abs(actual-pred).sum()/den*100))
def mae(a,p): return float(np.mean(np.abs(np.asarray(a)-np.asarray(p)))) if len(a) else 0.0

def _predict(v, name, h):
    v=np.maximum(np.asarray(v,dtype=float),0)
    if not len(v): return np.zeros(h)
    if name=='moving_average_7': return np.full(h, np.mean(v[-7:]))
    if name=='seasonal_naive_7': return np.array([v[-7+i%7] if len(v)>=7 else np.mean(v) for i in range(h)])
    if name=='simple_exponential_smoothing':
        best=(float('inf'),.3)
        for alpha in [.15,.3,.5,.7,.9]:
            level=v[0]; errs=[]
            for x in v[1:]: errs.append(x-level); level=alpha*x+(1-alpha)*level
            score=np.mean(np.square(errs)) if errs else 0
            if score<best[0]: best=(score,alpha)
        alpha=best[1]; level=v[0]
        for x in v[1:]: level=alpha*x+(1-alpha)*level
        return np.full(h,max(0,float(level)))
    if name=='weekday_profile':
        profile=[np.mean(v[np.arange(len(v))%7==k]) for k in range(7)]
        return np.array([profile[(len(v)+i)%7] for i in range(h)])
    raise ValueError(name)

def forecast_product(daily_sales, horizon):
    v=np.maximum(np.nan_to_num(np.asarray(daily_sales,dtype=float),nan=0),0); n=len(v); h=max(1,int(horizon))
    if n<7:
        avg=float(np.mean(v)) if n else 0
        return {'forecast':[avg]*h,'model':'short_history_average','wape':None,'mae':None,'sigma_daily':float(np.std(v)) if n else 0,'confidence':'low confidence','note':f'Only {n} days; using average demand.'}
    candidates=['moving_average_7','seasonal_naive_7','simple_exponential_smoothing','weekday_profile'] if n>=28 else ['moving_average_7']
    scores={}
    start=max(1,n-14)
    for name in candidates:
        actual=[]; pred=[]; residual=[]
        for origin in range(start,n):
            pp=float(_predict(v[:origin],name,1)[0]); actual.append(v[origin]); pred.append(pp); residual.append(v[origin]-pp)
        scores[name]={'wape':wape(np.array(actual),np.array(pred)),'mae':mae(actual,pred),'residuals':residual}
    chosen=min(scores,key=lambda x:scores[x]['wape']); sc=scores[chosen]
    return {'forecast':np.maximum(_predict(v,chosen,h),0).tolist(),'model':chosen,'wape':sc['wape'],'mae':sc['mae'],'sigma_daily':float(np.std(sc['residuals'],ddof=1)) if len(sc['residuals'])>1 else 0,'confidence':'backtested' if n>=28 else 'low confidence','note':f"Selected by rolling-origin backtest over {len(sc['residuals'])} days."}

def daily_series(df, product_id):
    d=df[df.product_id.astype(str)==str(product_id)].copy()
    if d.empty: return np.array([])
    d['date']=pd.to_datetime(d.date,errors='coerce'); d=d.dropna(subset=['date'])
    if d.empty:return np.array([])
    s=d.groupby('date').quantity_sold.sum().sort_index(); return s.asfreq('D',fill_value=0).to_numpy(dtype=float)
