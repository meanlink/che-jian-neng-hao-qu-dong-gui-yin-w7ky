from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Bill, ReconGroup, ReconItem, ReconBillClaim
from src.schemas.recon import BillImport, ReconGroupInput, RevokeInput
from src.middlewares.auth import current_user, can_write, admin_only
from src.services import recon
from src.utils.serialization import bill_dict, recon_group_dict, recon_item_dict
router = APIRouter()

@router.get('/bills')
def bills(db=Depends(get_db), u=Depends(current_user)):
    claimed = {c.bill_id for c in db.scalars(select(ReconBillClaim))}
    return [bill_dict(b, b.id in claimed) for b in db.scalars(select(Bill).order_by(Bill.id.desc()))]

@router.post('/bills/import', status_code=201)
def import_bills(data: BillImport, db=Depends(get_db), u=Depends(can_write)):
    return [bill_dict(b, False) for b in recon.import_bills(db, data, u.email)]

@router.get('/bills/{id}')
def bill_detail(id: int, db=Depends(get_db), u=Depends(current_user)):
    b = db.get(Bill, id)
    if not b:
        raise HTTPException(404, '供电账单不存在')
    claimed = db.scalar(select(ReconBillClaim).where(ReconBillClaim.bill_id == id)) is not None
    return bill_dict(b, claimed)

@router.get('/recon/groups')
def groups(status: str = '', db=Depends(get_db), u=Depends(current_user)):
    query = select(ReconGroup).order_by(ReconGroup.id.desc())
    if status:
        if status not in ('pending', 'mismatch', 'confirmed', 'revoked'):
            raise HTTPException(422, '未知的核销组状态')
        query = query.where(ReconGroup.status == status)
    return [recon_group_dict(g) for g in db.scalars(query).all()]

@router.post('/recon/groups', status_code=201)
def create_group(data: ReconGroupInput, db=Depends(get_db), u=Depends(can_write)):
    return recon_group_dict(recon.create_group(db, data, u))

@router.get('/recon/groups/{id}')
def group_detail(id: int, db=Depends(get_db), u=Depends(current_user)):
    g = db.get(ReconGroup, id)
    if not g:
        raise HTTPException(404, '核销组不存在')
    items = db.scalars(select(ReconItem).where(ReconItem.group_id == id).order_by(ReconItem.day)).all()
    return {**recon_group_dict(g), 'items': [recon_item_dict(i) for i in items]}

@router.post('/recon/groups/{id}/confirm')
def confirm(id: int, db=Depends(get_db), u=Depends(admin_only)):
    return recon_group_dict(recon.confirm(db, id, u))

@router.post('/recon/groups/{id}/revoke')
def revoke(id: int, data: RevokeInput | None = None, db=Depends(get_db), u=Depends(admin_only)):
    return recon_group_dict(recon.revoke(db, id, u, (data.reason if data else '') or ''))
