from pathlib import Path
from datetime import date,timedelta
import csv,random
BASE=Path(__file__).resolve().parent; DATA=BASE/'data'; DATA.mkdir(exist_ok=True); random.seed(42)
today=date.today(); start=today-timedelta(days=89)
products=[('P01','Milk',22,30,23,1,3,18,0,2,1,1),('P02','Bread',15,35,25,1,2,12,0,2,1,1),('P03','Rice',5,70,54,4,365,18,5,7,1,5),('P04','Biscuits',8,10,6,2,180,9,0,5,12,6),('P05','Cooking Oil',2,160,135,3,365,55,0,7,1,1),('P06','Eggs',12,7,5,1,14,8,0,2,6,6),('P07','Tea',3,120,92,3,365,10,0,7,1,1),('P08','Sugar',4,48,38,2,365,20,0,7,1,1),('P09','Curd',9,25,18,1,4,5,0,2,1,1),('P10','Instant Noodles',7,15,9,2,180,10,0,5,1,5),('P11','Soap',2,40,27,4,365,7,0,7,1,1),('P12','Bananas',10,6,3.5,1,4,7,0,2,1,1)]
with (DATA/'sales.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['date','product_id','product_name','quantity_sold','unit_price','unit_cost'])
 for pid,name,base,price,cost,*rest in products:
  for i in range(90):
   d=start+timedelta(days=i); wf=[.9,.9,.95,1,1.05,1.25,1.2][d.weekday()]; promo=2.8 if name=='Biscuits' and i==64 else 1
   q=max(0,round(base*wf*random.uniform(.78,1.22)*promo))
   if name=='Milk' and i>76:q=max(0,round(base*1.15*random.uniform(.78,1.22)))
   w.writerow([d.isoformat(),pid,name,q,price,cost])
with (DATA/'product_settings.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['product_id','current_stock','incoming_stock','lead_time_days','review_period_days','shelf_life_days','min_order_qty','pack_size','unit_cost'])
 for pid,name,base,price,cost,lead,shelf,stock,incoming,review,moq,pack in products:w.writerow([pid,stock,incoming,lead,review,shelf,moq,pack,cost])
