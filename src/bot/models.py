from pydantic import BaseModel

class GuardrailCheck(BaseModel):
    is_business: bool
    is_safe: bool
    reason: str
    
class Installment(BaseModel):
    amount: float
    installment_rn: int
    payment_date: str
    
class FinancialPlan(BaseModel):
    car_price: float
    total_paid: float
    installments: list[Installment]
    annual_interest_rate: float
    
class CarData(BaseModel):
    stock_id: int
    price: float
    make: str
    model: str
    year: str
    version: str

class AgentOutput(BaseModel):
    message: str
    needsTriage: bool