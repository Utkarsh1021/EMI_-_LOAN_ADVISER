from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class LoanType(str, Enum):
    HOME = "home"
    PERSONAL = "personal"
    CAR = "car"
    EDUCATION = "education"
    GOLD = "gold"
    PROPERTY = "property"
    TWO_WHEELER = "two_wheeler"
    CONSUMER_DURABLE = "consumer_durable"


class InterestRateType(str, Enum):
    FIXED = "fixed"
    FLOATING = "floating"
    HYBRID = "hybrid"


class EmploymentType(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    PROFESSIONAL = "professional"
    BUSINESS_OWNER = "business_owner"


class LoanOption(BaseModel):
    name: str
    principal: float = Field(gt=0)
    annual_rate: float = Field(ge=0, le=30)
    tenure_years: int = Field(gt=0, le=30)
    processing_fee: float = Field(default=0, ge=0)
    prepayment_charges: float = Field(default=0, ge=0)
    loan_type: LoanType = LoanType.PERSONAL
    interest_rate_type: InterestRateType = InterestRateType.FIXED
    lender: str = ""


class EMIResult(BaseModel):
    monthly_emi: float
    total_interest: float
    total_payment: float
    principal: float
    processing_fee: float = 0
    effective_rate: float = 0


class AmortizationRow(BaseModel):
    month: int
    year: int
    opening_balance: float
    emi: float
    principal_paid: float
    interest_paid: float
    closing_balance: float
    cumulative_principal: float
    cumulative_interest: float


class AmortizationSchedule(BaseModel):
    rows: List[AmortizationRow]
    total_principal: float
    total_interest: float
    total_payment: float
    loan_term_months: int


class EligibilityInput(BaseModel):
    monthly_income: float = Field(gt=0)
    monthly_expenses: float = Field(ge=0)
    existing_emis: float = Field(default=0, ge=0)
    age: int = Field(ge=18, le=70)
    employment_type: EmploymentType = EmploymentType.SALARIED
    credit_score: int = Field(default=750, ge=300, le=900)
    loan_type: LoanType = LoanType.PERSONAL
    desired_tenure_years: int = Field(default=20, ge=1, le=30)


class EligibilityResult(BaseModel):
    eligible: bool
    max_loan_amount: float
    max_emi: float
    dti_ratio: float
    foi_ratio: float
    recommended_emi: float
    recommended_tenure_years: int
    loan_to_value_ratio: Optional[float] = None
    income_multiplier: float
    notes: List[str] = []


class ComparisonResult(BaseModel):
    options: List[LoanOption]
    best_overall: LoanOption
    lowest_emi: LoanOption
    lowest_total_interest: LoanOption
    comparison_table: List[dict]


class PrepaymentResult(BaseModel):
    original_schedule: AmortizationSchedule
    new_schedule: AmortizationSchedule
    interest_saved: float
    months_reduced: int
    prepayment_amount: float
    prepayment_month: int
    new_tenure_months: int
    effective_savings: float


class AffordabilityResult(BaseModel):
    max_principal: float
    recommended_emi: float
    comfortable_emi: float
    stretch_emi: float
    tenure_years: int
    interest_rate: float
    dti_at_recommended: float
    dti_at_stretch: float


class UserProfile(BaseModel):
    session_id: str
    name: Optional[str] = None
    monthly_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    existing_emis: Optional[float] = None
    age: Optional[int] = None
    employment_type: Optional[EmploymentType] = None
    credit_score: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationTurn(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    user_input: str
    plan: Optional[str] = None
    tool_calls: List[dict] = []
    tool_results: List[dict] = []
    response: str
    metadata: dict = {}


class ConversationMemory(BaseModel):
    session_id: str
    user_profile: Optional[UserProfile] = None
    turns: List[ConversationTurn] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ExportData(BaseModel):
    session_id: str
    export_type: Literal["pdf", "excel", "both"]
    loan_calculations: List[dict] = []
    amortization_schedules: List[dict] = []
    comparisons: List[dict] = []
    eligibility_assessments: List[dict] = []
    prepayment_analyses: List[dict] = []
    generated_at: datetime = Field(default_factory=datetime.now)


INDIAN_LOAN_RULES = {
    LoanType.HOME: {
        "max_ltv": 0.90,
        "min_ltv": 0.75,
        "max_tenure_years": 30,
        "min_income_multiple": 5,
        "max_income_multiple": 7,
        "typical_rate_range": (8.0, 11.0),
        "processing_fee_pct": 0.005,
        "prepayment_charges_pct": 0.0,
        "min_credit_score": 650,
    },
    LoanType.PERSONAL: {
        "max_ltv": 1.0,
        "min_ltv": 0.0,
        "max_tenure_years": 7,
        "min_income_multiple": 10,
        "max_income_multiple": 25,
        "typical_rate_range": (10.0, 24.0),
        "processing_fee_pct": 0.02,
        "prepayment_charges_pct": 0.02,
        "min_credit_score": 700,
    },
    LoanType.CAR: {
        "max_ltv": 0.90,
        "min_ltv": 0.70,
        "max_tenure_years": 7,
        "min_income_multiple": 3,
        "max_income_multiple": 5,
        "typical_rate_range": (7.5, 12.0),
        "processing_fee_pct": 0.01,
        "prepayment_charges_pct": 0.02,
        "min_credit_score": 650,
    },
    LoanType.EDUCATION: {
        "max_ltv": 1.0,
        "min_ltv": 0.0,
        "max_tenure_years": 15,
        "min_income_multiple": 0,
        "max_income_multiple": 0,
        "typical_rate_range": (8.0, 13.0),
        "processing_fee_pct": 0.01,
        "prepayment_charges_pct": 0.0,
        "min_credit_score": 600,
    },
    LoanType.GOLD: {
        "max_ltv": 0.75,
        "min_ltv": 0.0,
        "max_tenure_years": 3,
        "min_income_multiple": 0,
        "max_income_multiple": 0,
        "typical_rate_range": (7.0, 12.0),
        "processing_fee_pct": 0.005,
        "prepayment_charges_pct": 0.0,
        "min_credit_score": 500,
    },
    LoanType.PROPERTY: {
        "max_ltv": 0.65,
        "min_ltv": 0.50,
        "max_tenure_years": 15,
        "min_income_multiple": 4,
        "max_income_multiple": 6,
        "typical_rate_range": (9.0, 13.0),
        "processing_fee_pct": 0.01,
        "prepayment_charges_pct": 0.02,
        "min_credit_score": 700,
    },
    LoanType.TWO_WHEELER: {
        "max_ltv": 0.85,
        "min_ltv": 0.70,
        "max_tenure_years": 5,
        "min_income_multiple": 2,
        "max_income_multiple": 4,
        "typical_rate_range": (8.0, 15.0),
        "processing_fee_pct": 0.01,
        "prepayment_charges_pct": 0.02,
        "min_credit_score": 600,
    },
    LoanType.CONSUMER_DURABLE: {
        "max_ltv": 1.0,
        "min_ltv": 0.0,
        "max_tenure_years": 3,
        "min_income_multiple": 0,
        "max_income_multiple": 0,
        "typical_rate_range": (0.0, 18.0),
        "processing_fee_pct": 0.0,
        "prepayment_charges_pct": 0.0,
        "min_credit_score": 600,
    },
}


def get_loan_rules(loan_type: LoanType) -> dict:
    return INDIAN_LOAN_RULES.get(loan_type, INDIAN_LOAN_RULES[LoanType.PERSONAL])


def calculate_max_loan_from_income(
    monthly_income: float,
    loan_type: LoanType,
    existing_emis: float = 0,
    foi_limit: float = 0.5
) -> float:
    rules = get_loan_rules(loan_type)
    max_foi_emi = monthly_income * foi_limit - existing_emis
    if max_foi_emi <= 0:
        return 0
    
    if rules["max_income_multiple"] > 0:
        income_based_max = monthly_income * 12 * rules["max_income_multiple"]
        return min(max_foi_emi * 100, income_based_max)
    
    return max_foi_emi * 100