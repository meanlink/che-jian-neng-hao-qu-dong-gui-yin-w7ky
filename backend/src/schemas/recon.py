from pydantic import BaseModel, Field
class BillRow(BaseModel):
    bill_no: str = Field(min_length=1, max_length=64)
    line: str = Field(min_length=1, max_length=80)
    start_day: str = Field(min_length=10, max_length=10)
    end_day: str = Field(min_length=10, max_length=10)
    kwh: float
class BillImport(BaseModel):
    source: str = Field(default='manual.json', max_length=200)
    bills: list[BillRow] = Field(min_length=1, max_length=500)
class ReconGroupInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    bill_id: int
    dataset_id: int
    days: list[str] = Field(min_length=1, max_length=400)
class RevokeInput(BaseModel):
    reason: str = Field(default='', max_length=300)
