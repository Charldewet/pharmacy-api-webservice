from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class Pharmacy(BaseModel):
    pharmacy_id: int
    name: str

class DailySales(BaseModel):
    business_date: date
    pharmacy_id: int
    turnover: Optional[float] = None
    sales_cash: Optional[float] = None
    sales_account: Optional[float] = None
    sales_cod: Optional[float] = None
    type_r_sales: Optional[float] = None
    transaction_count: Optional[int] = None
    avg_basket: Optional[float] = None
    purchases: Optional[float] = None
    cost_of_sales: Optional[float] = None
    closing_stock: Optional[float] = None
    dispensary_turnover: Optional[float] = None
    scripts_qty: Optional[int] = None
    avg_script_value: Optional[float] = None
    first_seen_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    gp_value: Optional[float] = None
    denom_excl_type_r: Optional[float] = None
    gp_pct: Optional[float] = None
    retail_excl_type_r: Optional[float] = None
    dispensary_excl_vat: Optional[float] = None
    disp_pct: Optional[float] = None
    frontshop_pct: Optional[float] = None
    frontshop_turnover: Optional[float] = None

class StockItem(BaseModel):
    department_code: Optional[str] = None
    product_code: str
    description: Optional[str] = None
    qty_sold: Optional[float] = None
    sales_val: Optional[float] = None
    cost_of_sales: Optional[float] = None
    gp_value: Optional[float] = None
    gp_pct: Optional[float] = None
    on_hand: Optional[float] = None
    product_id: int

class StockPage(BaseModel):
    items: List[StockItem]
    nextCursor: Optional[str] = None

class CoverageRow(BaseModel):
    business_date: date
    pharmacy_id: int
    inv249_turnover: bool
    stk261_trading: bool
    phm080_scripts: bool
    stk260_gp: bool
    last_updated: Optional[datetime] = None
