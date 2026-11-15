import time, json, calendar
from types import SimpleNamespace
from sqlalchemy import select, func
from src.config.database import Session
from migrations.initial import migrate
from src.models import User, Dataset, Job, Report, Delivery, Audit, Bill, ReconGroup
from src.services.business import metadata, seed_records, analyze
from src.services.reports import deliver
from src.services import recon as recon_service
from src.utils.security import hash_password
from src.utils.serialization import checksum
def seed_recon(db,d,admin):
    by_month={}
    for row in d.records:by_month.setdefault(row['day'][:7],[]).append(row)
    def month_sum(month,end=None):return round(sum(r['kwh'] for r in by_month.get(month,[]) if end is None or r['day']<=end),2)
    def month_end(month):return month+'-'+str(calendar.monthrange(int(month[:4]),int(month[5:]))[1]).zfill(2)
    bills={}
    for no,month,end in [('GD-202605-P01','2026-05',None),('GD-202606-P01','2026-06',None),('GD-202607-P01','2026-07',None)]:
        b=db.scalar(select(Bill).where(Bill.bill_no==no))
        if not b:
            b=Bill(bill_no=no,line='冲压P01',start_day=month+'-01',end_day=month_end(month),kwh=month_sum(month,end),source='seed-供电账单-2026.csv',created_at=time.time())
            db.add(b);db.flush()
        bills[month]=b
    def make_group(name,month,days):
        g=db.scalar(select(ReconGroup).where(ReconGroup.name==name))
        if g:return g
        data=SimpleNamespace(name=name,bill_id=bills[month].id,dataset_id=d.id,days=days)
        return recon_service.create_group(db,data,admin)
    may_days=[r['day'] for r in by_month['2026-05']]
    g=make_group('2026年5月 冲压P01 电费核销','2026-05',may_days)
    if g.status=='pending':recon_service.confirm(db,g.id,admin)
    july_days=[r['day'] for r in by_month['2026-07'] if r['day']<='2026-07-30']
    make_group('2026年7月 冲压P01 电费核销','2026-07',july_days)
def seed():
    migrate()
    with Session() as db:
        for role,name in [('admin','林知 · 业务负责人'),('analyst','陈舟 · 分析员'),('viewer','周禾 · 观察员')]:
            email=role+'@demo.local'
            if not db.scalar(select(User).where(User.email==email)):
                db.add(User(email=email,name=name,role=role,password=hash_password('Demo123!')))
        db.flush()
        m=metadata()
        d=db.scalar(select(Dataset).where(Dataset.name==m['dataset_name']))
        if not d:
            rows=seed_records()
            d=Dataset(name=m['dataset_name'],source=m['short']+'-202611.csv',records=rows,checksum=checksum(rows),created_at=time.time())
            db.add(d); db.flush()
        if not db.scalar(select(Job).where(Job.name=='基线复核 · '+m['name'])):
            params={p['key']:p['default'] for p in m.get('parameters',[])}
            result=analyze(d.records,params)
            json.dumps(result,ensure_ascii=False,allow_nan=False)
            admin=db.scalar(select(User).where(User.role=='admin'))
            j=Job(name='基线复核 · '+m['name'],dataset_id=d.id,params=params,status='completed',result=result,created_by=admin.id,created_at=time.time()-3600,finished_at=time.time()-3595,approved=True)
            db.add(j);db.flush()
            r=Report(name='每日业务复核简报',job_id=j.id,destination='业务复核组 · 本地收件箱',interval_seconds=86400,next_run=time.time()+86400,enabled=True)
            db.add(r);db.flush();deliver(db,r)
            db.add(Audit(actor='seed',action='demo.baseline',detail={'dataset':d.id},at=time.time()))
        db.commit()
        admin=db.scalar(select(User).where(User.role=='admin'))
        seed_recon(db,d,admin)
        counts={model.__tablename__:db.scalar(select(func.count()).select_from(model)) for model in [User,Dataset,Job,Report,Delivery,Audit,Bill,ReconGroup]}
        print(json.dumps(counts,ensure_ascii=False))
        return counts
if __name__=='__main__':seed()
