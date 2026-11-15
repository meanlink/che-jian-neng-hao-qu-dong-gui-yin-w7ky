"""电量对账：供电账单与车间日耗样本的核销组管理。

确认与撤销均在单一数据库事务内完成：中断后重试不会重复占用或重复释放。
账单占用与线体日期占用由唯一约束兜底，并发冲突时整组拒绝。
"""
import math
import time
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.models import Bill, Dataset, ReconGroup, ReconItem, ReconBillClaim, ReconDayClaim
from src.services.audit import record

TOLERANCE_ABS = 0.5   # kWh，尾差绝对容差
TOLERANCE_REL = 0.001  # 账单电量的千分之一


def _day(value, label='日期'):
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise HTTPException(422, f'{label}须为 ISO 日期（YYYY-MM-DD）') from None


def _span(start, end):
    days, current = [], start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
        if len(days) > 400:
            raise HTTPException(422, '账单起止日跨度不能超过 400 天')
    return days


def _tolerance(bill_kwh):
    return max(TOLERANCE_ABS, abs(bill_kwh) * TOLERANCE_REL)


def import_bills(db, data, actor):
    seen = set()
    for index, row in enumerate(data.bills):
        no = row.bill_no.strip()
        line = row.line.strip()
        if not no or not line:
            raise HTTPException(422, f'第 {index + 1} 条账单号与线体不能为空')
        if no in seen:
            raise HTTPException(422, f'第 {index + 1} 条账单号 {no} 在本次导入中重复')
        seen.add(no)
        start, end = _day(row.start_day, '起始日'), _day(row.end_day, '截止日')
        if start > end:
            raise HTTPException(422, f'账单 {no} 的起始日晚于截止日')
        if not math.isfinite(row.kwh) or row.kwh < 0 or row.kwh > 1_000_000_000:
            raise HTTPException(422, f'账单 {no} 的电量须为 0 至 10 亿 kWh 的有限数值')
    existing = {b.bill_no for b in db.scalars(select(Bill).where(Bill.bill_no.in_(seen)))} if seen else set()
    if existing:
        raise HTTPException(409, '账单号已存在，导入整批拒绝：' + '、'.join(sorted(existing)))
    now = time.time()
    for row in data.bills:
        db.add(Bill(bill_no=row.bill_no.strip(), line=row.line.strip(),
                    start_day=_day(row.start_day).isoformat(), end_day=_day(row.end_day).isoformat(),
                    kwh=round(float(row.kwh), 4), source=data.source, created_at=now))
    record(db, actor, 'bill.import', {'count': len(data.bills), 'source': data.source})
    db.commit()
    return db.scalars(select(Bill).where(Bill.bill_no.in_(seen))).all()


def evaluate(bill, dataset, days):
    """对照账单周期逐日检查所选日样本：缺日、重叠、超期与总量差额。"""
    wanted = {str(d).strip() for d in days}
    for d in wanted:
        _day(d, '样本日期')
    by_day = {}
    for row in dataset.records:
        if row.get('line') == bill.line and str(row.get('day')) in wanted:
            by_day.setdefault(str(row['day']), []).append(row)
    items, issues = [], []
    for day in sorted(by_day):
        rows = by_day[day]
        if len(rows) > 1:
            issues.append(f'重叠：{day} 在批次中有 {len(rows)} 条同线同日记录，需先合并')
        for row in rows:
            try:
                kwh = float(row.get('kwh'))
                if not math.isfinite(kwh) or kwh < 0:
                    raise ValueError()
            except (TypeError, ValueError):
                raise HTTPException(422, f'样本 {day} 的耗电量不是有效的非负数值') from None
            items.append({'line': bill.line, 'day': day, 'kwh': kwh, 'dataset_id': dataset.id})
    covered = set(by_day)
    for day in _span(_day(bill.start_day), _day(bill.end_day)):
        if day not in covered:
            issues.append(f'缺日：账单周期内 {day} 无对应日样本')
    start, end = _day(bill.start_day), _day(bill.end_day)
    for day in sorted(covered):
        if not start <= _day(day) <= end:
            issues.append(f'超期：所选样本 {day} 不在账单周期 {bill.start_day} 至 {bill.end_day} 内')
    total = round(sum(item['kwh'] for item in items), 4)
    diff = round(total - bill.kwh, 4)
    if abs(diff) > _tolerance(bill.kwh):
        issues.append(f'差额：样本合计 {total:.2f} kWh 与账单 {bill.kwh:.2f} kWh 相差 {diff:+.2f} kWh，超出容差 {_tolerance(bill.kwh):.2f}')
    return items, issues, total, diff


def create_group(db, data, user):
    bill = db.get(Bill, data.bill_id)
    if not bill:
        raise HTTPException(404, '供电账单不存在')
    dataset = db.get(Dataset, data.dataset_id)
    if not dataset:
        raise HTTPException(404, '数据批次不存在')
    name = data.name.strip()
    if len(name) < 2:
        raise HTTPException(422, '核销组名称去除空格后至少需要两个字符')
    items, issues, total, diff = evaluate(bill, dataset, data.days)
    group = ReconGroup(name=name, bill_id=bill.id, dataset_id=dataset.id,
                       status='pending' if not issues else 'mismatch',
                       bill_no=bill.bill_no, line=bill.line, start_day=bill.start_day, end_day=bill.end_day,
                       bill_kwh=bill.kwh, sample_kwh=total, diff_kwh=diff, issues=issues,
                       created_by=user.id, created_at=time.time())
    db.add(group)
    db.flush()
    for item in items:
        db.add(ReconItem(group_id=group.id, **item))
    record(db, user.email, 'recon.create', {'id': group.id, 'bill_no': bill.bill_no, 'status': group.status, 'issues': len(issues)})
    db.commit()
    return group


def confirm(db, group_id, user):
    group = db.scalar(select(ReconGroup).where(ReconGroup.id == group_id).with_for_update())
    if not group:
        raise HTTPException(404, '核销组不存在')
    if group.status == 'confirmed':
        return group  # 中断重试：已确认则直接返回，不重复占用
    if group.status != 'pending':
        raise HTTPException(409, '仅待核对（逐日齐全且总量相符）的核销组可以确认；差异组请先撤销后重配')
    if db.scalar(select(ReconBillClaim).where(ReconBillClaim.bill_id == group.bill_id)):
        raise HTTPException(409, f'账单 {group.bill_no} 已归入其他有效核销组，整组拒绝')
    days = [item.day for item in db.scalars(select(ReconItem).where(ReconItem.group_id == group.id))]
    if days:
        taken = db.scalars(select(ReconDayClaim).where(ReconDayClaim.line == group.line, ReconDayClaim.day.in_(days))).all()
        if taken:
            clash = '、'.join(sorted({t.day for t in taken})[:5])
            raise HTTPException(409, f'线体 {group.line} 的日期 {clash} 已归入其他有效核销组，整组拒绝')
    now = time.time()
    db.add(ReconBillClaim(bill_id=group.bill_id, group_id=group.id, created_at=now))
    for day in days:
        db.add(ReconDayClaim(line=group.line, day=day, group_id=group.id, created_at=now))
    group.status = 'confirmed'
    group.confirmed_at = now
    record(db, user.email, 'recon.confirm', {'id': group.id, 'bill_no': group.bill_no, 'days': len(days)})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '并发冲突：同一账单或同一线体日期已被其他核销组占用，整组拒绝') from None
    return group


def revoke(db, group_id, user, reason=''):
    group = db.scalar(select(ReconGroup).where(ReconGroup.id == group_id).with_for_update())
    if not group:
        raise HTTPException(404, '核销组不存在')
    if group.status == 'revoked':
        return group  # 中断重试：已撤销则直接返回，不重复释放
    was_confirmed = group.status == 'confirmed'
    for model in (ReconBillClaim, ReconDayClaim):
        db.query(model).filter(model.group_id == group.id).delete()
    group.status = 'revoked'
    group.revoked_at = time.time()
    group.revoke_reason = reason.strip()
    record(db, user.email, 'recon.revoke', {'id': group.id, 'bill_no': group.bill_no, 'released': was_confirmed})
    db.commit()
    return group
