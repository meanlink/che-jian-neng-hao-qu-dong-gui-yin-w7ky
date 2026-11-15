from sqlalchemy import String, JSON, Double, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Bill(Base):
    __tablename__ = 'bills'
    id: Mapped[int] = mapped_column(primary_key=True)
    bill_no: Mapped[str] = mapped_column(String(64), unique=True)
    line: Mapped[str] = mapped_column(String(80))
    start_day: Mapped[str] = mapped_column(String(10))
    end_day: Mapped[str] = mapped_column(String(10))
    kwh: Mapped[float] = mapped_column(Double)
    source: Mapped[str] = mapped_column(String(200), default='manual.json')
    created_at: Mapped[float] = mapped_column(Double)
class ReconGroup(Base):
    __tablename__ = 'recon_groups'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    bill_id: Mapped[int] = mapped_column(ForeignKey('bills.id'))
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    bill_no: Mapped[str] = mapped_column(String(64))
    line: Mapped[str] = mapped_column(String(80))
    start_day: Mapped[str] = mapped_column(String(10))
    end_day: Mapped[str] = mapped_column(String(10))
    bill_kwh: Mapped[float] = mapped_column(Double)
    sample_kwh: Mapped[float] = mapped_column(Double)
    diff_kwh: Mapped[float] = mapped_column(Double)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
    confirmed_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    revoked_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    revoke_reason: Mapped[str] = mapped_column(String(300), default='')
class ReconItem(Base):
    __tablename__ = 'recon_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey('recon_groups.id'))
    line: Mapped[str] = mapped_column(String(80))
    day: Mapped[str] = mapped_column(String(10))
    kwh: Mapped[float] = mapped_column(Double)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
class ReconBillClaim(Base):
    __tablename__ = 'recon_bill_claims'
    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey('bills.id'), unique=True)
    group_id: Mapped[int] = mapped_column(ForeignKey('recon_groups.id'))
    created_at: Mapped[float] = mapped_column(Double)
class ReconDayClaim(Base):
    __tablename__ = 'recon_day_claims'
    id: Mapped[int] = mapped_column(primary_key=True)
    line: Mapped[str] = mapped_column(String(80))
    day: Mapped[str] = mapped_column(String(10))
    group_id: Mapped[int] = mapped_column(ForeignKey('recon_groups.id'))
    created_at: Mapped[float] = mapped_column(Double)
    __table_args__ = (UniqueConstraint('line', 'day', name='uq_recon_day_claim'),)
