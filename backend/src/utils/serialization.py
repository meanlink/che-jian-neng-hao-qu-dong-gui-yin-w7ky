import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j):
    return {k:getattr(j,k) for k in ['id','name','dataset_id','params','status','result','error','approved','created_at','finished_at']}
def report_dict(r):
    return {k:getattr(r,k) for k in ['id','name','job_id','destination','interval_seconds','next_run','enabled']}
def delivery_dict(d):
    return {k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination']}
def bill_dict(b,claimed=False):
    return {**{k:getattr(b,k) for k in ['id','bill_no','line','start_day','end_day','kwh','source','created_at']},'claimed':claimed}
def recon_group_dict(g):
    return {k:getattr(g,k) for k in ['id','name','bill_id','dataset_id','status','bill_no','line','start_day','end_day','bill_kwh','sample_kwh','diff_kwh','issues','created_at','confirmed_at','revoked_at','revoke_reason']}
def recon_item_dict(i):
    return {k:getattr(i,k) for k in ['id','group_id','line','day','kwh','dataset_id']}
