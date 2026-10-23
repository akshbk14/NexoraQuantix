import math
PRIORITY={'Critical':0,'High':1,'Medium':2,'Low':3}
def optimize_product(product, forecast_result, settings, service_level=.95):
    p=dict(product); s=dict(settings); fc=[max(0,float(x)) for x in forecast_result.get('forecast',[])]; lead=max(0,int(s.get('lead_time_days',1))); review=max(1,int(s.get('review_period_days',7))); h=max(1,lead+review)
    if not fc:fc=[0.0]*h
    if len(fc)<h:fc += [fc[-1]]*(h-len(fc))
    current=max(0,float(s.get('current_stock',0))); incoming=max(0,float(s.get('incoming_stock',0))); shelf=max(1,int(s.get('shelf_life_days',365))); moq=max(1,int(s.get('min_order_qty',1))); pack=max(1,int(s.get('pack_size',1)))
    usable=current
    age=s.get('stock_age_days')
    if age not in (None,''):
        try:
            if int(age)>=shelf: usable=0
        except (ValueError,TypeError): pass
    demand=sum(fc[:h]); sigma=max(0,float(forecast_result.get('sigma_daily',0) or 0)); z=1.65 if service_level>=.95 else (1.28 if service_level>=.90 else 0.84); safety=z*sigma*math.sqrt(h); target=demand+safety
    shelf_h=min(shelf,h+review); shelf_cap=sum(fc[:shelf_h])*1.10
    if shelf<365: target=min(target,shelf_cap)
    raw=max(0,target-usable-incoming); order=0
    if raw>0:
        order=int(math.ceil(max(moq,math.ceil(raw))/pack)*pack)
        if shelf<365 and order>shelf_cap-usable-incoming:
            order=max(0,int(math.floor(max(0,shelf_cap-usable-incoming)/pack)*pack))
            if order<moq:order=0
    avg=demand/h; cover=usable/avg if avg>0 else float('inf')
    priority='Critical' if cover<lead else ('High' if cover<lead+review else ('Medium' if order>0 else 'Low'))
    price=max(0,float(p.get('unit_price',0) or 0)); cost=float(p.get('unit_cost') or price*.7); margin=max(0,price-cost); shortfall=max(0,demand-usable-incoming)
    warning=[]
    if shelf<365: warning.append(f'Shelf-life cap: demand over {shelf_h} days + 10% buffer.')
    if forecast_result.get('confidence')=='low confidence':warning.append('Low-confidence forecast: short history.')
    if incoming:warning.append(f'Includes {incoming:g} incoming units.')
    if raw>0 and order==0:warning.append('No valid order fits MOQ/pack and shelf-life constraints.')
    w=forecast_result.get('wape'); covertxt='infinite' if math.isinf(cover) else f'{cover:.1f} days'
    explain=f'Cover {covertxt} is compared with {lead}-day lead time. Forecast demand {demand:.1f}, safety stock {safety:.1f}, usable stock {usable:g}, incoming {incoming:g}, order {order}. Model {forecast_result.get("model","unknown")}; WAPE {"not available" if w is None else f"{w:.1f}%"}.'
    if shelf<365:explain+=f' Shelf-life cap applied using {shelf_h}-day demand plus 10% buffer.'
    return {'product_id':str(p.get('product_id','')),'product_name':str(p.get('product_name',p.get('product_id','Unknown'))),'current_stock':current,'forecast_demand':round(demand,2),'safety_stock':round(safety,2),'lead_time_days':lead,'review_period_days':review,'recommended_order':int(order),'days_of_cover':None if math.isinf(cover) else round(cover,2),'priority':priority,'profit_at_risk':round(shortfall*margin,2),'estimated_order_cost':round(order*max(0,cost),2),'model':forecast_result.get('model'),'wape':w,'mae':forecast_result.get('mae'),'confidence':forecast_result.get('confidence'),'warning':' '.join(warning),'explanation':explain,'forecast':fc[:h],'sigma_daily':sigma}
def rank_reorders(rows,budget_limit=None):
    rows=sorted(rows,key=lambda r:(PRIORITY.get(r.get('priority','Low'),9),-float(r.get('profit_at_risk',0)),float('inf') if r.get('days_of_cover') is None else float(r['days_of_cover'])))
    remaining=None if budget_limit in (None,'') else max(0,float(budget_limit))
    for r in rows:
        r['deferred_over_budget']=False
        if remaining is not None:
            if float(r.get('estimated_order_cost',0))>remaining:r['deferred_over_budget']=True;r['warning']=(r.get('warning','')+' Deferred, over budget.').strip()
            else:remaining-=float(r.get('estimated_order_cost',0))
    return rows
