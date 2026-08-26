import math
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from pydantic import BaseModel

from .models import (
    LoanOption, EMIResult, AmortizationRow, AmortizationSchedule,
    EligibilityInput, EligibilityResult, ComparisonResult,
    PrepaymentResult, AffordabilityResult, LoanType,
    get_loan_rules, calculate_max_loan_from_income
)


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: str = ""


class ToolRegistry:
    def __init__(self):
        self.tools = {
            "calculate_emi": self.calculate_emi,
            "compare_loans": self.compare_loans,
            "check_eligibility": self.check_eligibility,
            "generate_amortization": self.generate_amortization,
            "calculate_prepayment_impact": self.calculate_prepayment_impact,
            "calculate_affordability": self.calculate_affordability,
        }
    
    def schema(self) -> List[dict]:
        return [
            {
                "name": "calculate_emi",
                "description": "Calculate EMI for a loan",
                "parameters": {
                    "principal": {"type": "number", "description": "Loan amount in INR"},
                    "annual_rate": {"type": "number", "description": "Annual interest rate %"},
                    "tenure_years": {"type": "integer", "description": "Loan tenure in years"},
                    "processing_fee": {"type": "number", "description": "Processing fee in INR", "default": 0},
                },
            },
            {
                "name": "compare_loans",
                "description": "Compare multiple loan options side by side",
                "parameters": {
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "principal": {"type": "number"},
                                "annual_rate": {"type": "number"},
                                "tenure_years": {"type": "integer"},
                                "processing_fee": {"type": "number", "default": 0},
                                "prepayment_charges": {"type": "number", "default": 0},
                                "loan_type": {"type": "string"},
                                "lender": {"type": "string", "default": ""},
                            },
                            "required": ["name", "principal", "annual_rate", "tenure_years"],
                        },
                    },
                },
            },
            {
                "name": "check_eligibility",
                "description": "Check loan eligibility based on income and profile",
                "parameters": {
                    "monthly_income": {"type": "number"},
                    "monthly_expenses": {"type": "number"},
                    "existing_emis": {"type": "number", "default": 0},
                    "age": {"type": "integer"},
                    "employment_type": {"type": "string", "default": "salaried"},
                    "credit_score": {"type": "integer", "default": 750},
                    "loan_type": {"type": "string", "default": "personal"},
                    "desired_tenure_years": {"type": "integer", "default": 20},
                },
            },
            {
                "name": "generate_amortization",
                "description": "Generate full amortization schedule",
                "parameters": {
                    "principal": {"type": "number"},
                    "annual_rate": {"type": "number"},
                    "tenure_years": {"type": "integer"},
                },
            },
            {
                "name": "calculate_prepayment_impact",
                "description": "Calculate impact of prepayment on loan",
                "parameters": {
                    "principal": {"type": "number"},
                    "annual_rate": {"type": "number"},
                    "tenure_years": {"type": "integer"},
                    "prepayment_amount": {"type": "number"},
                    "prepayment_month": {"type": "integer"},
                },
            },
            {
                "name": "calculate_affordability",
                "description": "Calculate how much loan you can afford",
                "parameters": {
                    "monthly_income": {"type": "number"},
                    "monthly_expenses": {"type": "number"},
                    "existing_emis": {"type": "number", "default": 0},
                    "annual_rate": {"type": "number"},
                    "tenure_years": {"type": "integer"},
                },
            },
        ]
    
    def execute(self, tool_name: str, args: dict) -> ToolResult:
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}", tool_name=tool_name)
        try:
            result = self.tools[tool_name](**args)
            return ToolResult(success=True, data=result, tool_name=tool_name)
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=tool_name)
    
    def calculate_emi(
        self,
        principal: float,
        annual_rate: float,
        tenure_years: int,
        processing_fee: float = 0
    ) -> EMIResult:
        monthly_rate = annual_rate / 12 / 100
        n_months = tenure_years * 12
        
        if monthly_rate == 0:
            emi = principal / n_months
        else:
            emi = principal * monthly_rate * (1 + monthly_rate) ** n_months / ((1 + monthly_rate) ** n_months - 1)
        
        total_payment = emi * n_months
        total_interest = total_payment - principal
        effective_rate = (total_interest / principal) * 100 / tenure_years if tenure_years > 0 else 0
        
        return EMIResult(
            monthly_emi=round(emi, 2),
            total_interest=round(total_interest, 2),
            total_payment=round(total_payment + processing_fee, 2),
            principal=principal,
            processing_fee=processing_fee,
            effective_rate=round(effective_rate, 2)
        )
    
    def compare_loans(self, options: List[dict]) -> ComparisonResult:
        loan_options = [LoanOption(**opt) for opt in options]
        results = []
        
        for opt in loan_options:
            emi_result = self.calculate_emi(
                opt.principal, opt.annual_rate, opt.tenure_years, opt.processing_fee
            )
            results.append({
                "name": opt.name,
                "lender": opt.lender,
                "principal": opt.principal,
                "annual_rate": opt.annual_rate,
                "tenure_years": opt.tenure_years,
                "monthly_emi": emi_result.monthly_emi,
                "total_interest": emi_result.total_interest,
                "total_payment": emi_result.total_payment,
                "processing_fee": opt.processing_fee,
                "prepayment_charges": opt.prepayment_charges,
                "effective_rate": emi_result.effective_rate,
            })
        
        best_overall = min(results, key=lambda x: x["total_payment"])
        lowest_emi = min(results, key=lambda x: x["monthly_emi"])
        lowest_interest = min(results, key=lambda x: x["total_interest"])
        
        return ComparisonResult(
            options=loan_options,
            best_overall=LoanOption(**best_overall),
            lowest_emi=LoanOption(**lowest_emi),
            lowest_total_interest=LoanOption(**lowest_interest),
            comparison_table=results
        )
    
    def check_eligibility(self, **kwargs) -> EligibilityResult:
        input_data = EligibilityInput(**kwargs)
        rules = get_loan_rules(input_data.loan_type)
        
        monthly_income = input_data.monthly_income
        monthly_expenses = input_data.monthly_expenses
        existing_emis = input_data.existing_emis
        age = input_data.age
        
        max_foi = 0.55 if input_data.employment_type == "salaried" else 0.50
        if input_data.credit_score >= 800:
            max_foi = min(max_foi + 0.05, 0.60)
        elif input_data.credit_score < 650:
            max_foi = max(max_foi - 0.10, 0.35)
        
        available_for_emi = monthly_income * max_foi - existing_emis
        available_for_emi = max(available_for_emi, 0)
        
        max_tenure = min(input_data.desired_tenure_years, rules["max_tenure_years"])
        max_tenure = min(max_tenure, 70 - age)
        
        if available_for_emi <= 0 or max_tenure <= 0:
            return EligibilityResult(
                eligible=False,
                max_loan_amount=0,
                max_emi=0,
                dti_ratio=(monthly_expenses + existing_emis) / monthly_income * 100,
                foi_ratio=(monthly_expenses + existing_emis) / monthly_income * 100,
                recommended_emi=0,
                recommended_tenure_years=0,
                income_multiplier=0,
                notes=["Insufficient income for new loan", "High existing obligations"]
            )
        
        rate = sum(rules["typical_rate_range"]) / 2
        monthly_rate = rate / 12 / 100
        n_months = max_tenure * 12
        
        if monthly_rate == 0:
            max_principal = available_for_emi * n_months
        else:
            max_principal = available_for_emi * ((1 + monthly_rate) ** n_months - 1) / (monthly_rate * (1 + monthly_rate) ** n_months)
        
        if rules["max_income_multiple"] > 0:
            income_based_max = monthly_income * 12 * rules["max_income_multiple"]
            max_principal = min(max_principal, income_based_max)
        
        recommended_emi = available_for_emi * 0.8
        
        if input_data.loan_type in [LoanType.HOME, LoanType.CAR, LoanType.PROPERTY]:
            ltv = rules["max_ltv"]
            property_value_estimate = max_principal / ltv
            loan_to_value = max_principal / property_value_estimate if property_value_estimate > 0 else None
        else:
            loan_to_value = None
        
        income_multiple = max_principal / (monthly_income * 12) if monthly_income > 0 else 0
        
        dti = (monthly_expenses + existing_emis) / monthly_income * 100
        foi = (monthly_expenses + existing_emis + recommended_emi) / monthly_income * 100
        
        notes = []
        if input_data.credit_score < rules["min_credit_score"]:
            notes.append(f"Credit score below minimum ({rules['min_credit_score']}) for {input_data.loan_type.value} loan")
        if foi > 55:
            notes.append("FOI ratio high - consider reducing loan amount")
        if age + max_tenure > 70:
            notes.append("Tenure limited by age - max age at maturity typically 70")
        
        eligible = (
            max_principal > 0 and
            input_data.credit_score >= rules["min_credit_score"] and
            foi <= 60 and
            max_tenure > 0
        )
        
        return EligibilityResult(
            eligible=eligible,
            max_loan_amount=round(max_principal, 2),
            max_emi=round(available_for_emi, 2),
            dti_ratio=round(dti, 2),
            foi_ratio=round(foi, 2),
            recommended_emi=round(recommended_emi, 2),
            recommended_tenure_years=max_tenure,
            loan_to_value_ratio=round(loan_to_value * 100, 2) if loan_to_value else None,
            income_multiplier=round(income_multiple, 2),
            notes=notes
        )
    
    def generate_amortization(
        self,
        principal: float,
        annual_rate: float,
        tenure_years: int
    ) -> AmortizationSchedule:
        monthly_rate = annual_rate / 12 / 100
        n_months = tenure_years * 12
        
        if monthly_rate == 0:
            emi = principal / n_months
        else:
            emi = principal * monthly_rate * (1 + monthly_rate) ** n_months / ((1 + monthly_rate) ** n_months - 1)
        
        rows = []
        balance = principal
        cum_principal = 0
        cum_interest = 0
        
        for month in range(1, n_months + 1):
            interest_paid = balance * monthly_rate
            principal_paid = emi - interest_paid
            
            if month == n_months:
                principal_paid = balance
                emi = principal_paid + interest_paid
            
            opening_balance = balance
            balance -= principal_paid
            cum_principal += principal_paid
            cum_interest += interest_paid
            
            rows.append(AmortizationRow(
                month=month,
                year=(month - 1) // 12 + 1,
                opening_balance=round(opening_balance, 2),
                emi=round(emi, 2),
                principal_paid=round(principal_paid, 2),
                interest_paid=round(interest_paid, 2),
                closing_balance=round(max(balance, 0), 2),
                cumulative_principal=round(cum_principal, 2),
                cumulative_interest=round(cum_interest, 2)
            ))
        
        total_principal = sum(r.principal_paid for r in rows)
        total_interest = sum(r.interest_paid for r in rows)
        total_payment = total_principal + total_interest
        
        return AmortizationSchedule(
            rows=rows,
            total_principal=round(total_principal, 2),
            total_interest=round(total_interest, 2),
            total_payment=round(total_payment, 2),
            loan_term_months=n_months
        )
    
    def calculate_prepayment_impact(
        self,
        principal: float,
        annual_rate: float,
        tenure_years: int,
        prepayment_amount: float,
        prepayment_month: int
    ) -> PrepaymentResult:
        original = self.generate_amortization(principal, annual_rate, tenure_years)
        
        if prepayment_month > original.loan_term_months:
            prepayment_month = original.loan_term_months
        
        balance_after_prepayment = original.rows[prepayment_month - 1].closing_balance - prepayment_amount
        balance_after_prepayment = max(balance_after_prepayment, 0)
        
        if balance_after_prepayment <= 0:
            new_schedule = AmortizationSchedule(
                rows=original.rows[:prepayment_month],
                total_principal=original.total_principal,
                total_interest=sum(r.interest_paid for r in original.rows[:prepayment_month]),
                total_payment=sum(r.emi for r in original.rows[:prepayment_month]),
                loan_term_months=prepayment_month
            )
        else:
            remaining_months = original.loan_term_months - prepayment_month
            monthly_rate = annual_rate / 12 / 100
            
            if monthly_rate == 0:
                new_emi = balance_after_prepayment / remaining_months
            else:
                new_emi = balance_after_prepayment * monthly_rate * (1 + monthly_rate) ** remaining_months / ((1 + monthly_rate) ** remaining_months - 1)
            
            new_rows = original.rows[:prepayment_month]
            balance = balance_after_prepayment
            cum_principal = sum(r.principal_paid for r in new_rows)
            cum_interest = sum(r.interest_paid for r in new_rows)
            
            for month in range(prepayment_month + 1, original.loan_term_months + 1):
                interest_paid = balance * monthly_rate
                principal_paid = new_emi - interest_paid
                
                if balance <= new_emi:
                    principal_paid = balance
                    new_emi = principal_paid + interest_paid
                
                opening_balance = balance
                balance -= principal_paid
                cum_principal += principal_paid
                cum_interest += interest_paid
                
                new_rows.append(AmortizationRow(
                    month=month,
                    year=(month - 1) // 12 + 1,
                    opening_balance=round(opening_balance, 2),
                    emi=round(new_emi, 2),
                    principal_paid=round(principal_paid, 2),
                    interest_paid=round(interest_paid, 2),
                    closing_balance=round(max(balance, 0), 2),
                    cumulative_principal=round(cum_principal, 2),
                    cumulative_interest=round(cum_interest, 2)
                ))
                
                if balance <= 0:
                    break
            
            new_schedule = AmortizationSchedule(
                rows=new_rows,
                total_principal=round(sum(r.principal_paid for r in new_rows), 2),
                total_interest=round(sum(r.interest_paid for r in new_rows), 2),
                total_payment=round(sum(r.emi for r in new_rows), 2),
                loan_term_months=len(new_rows)
            )
        
        interest_saved = original.total_interest - new_schedule.total_interest
        months_reduced = original.loan_term_months - new_schedule.loan_term_months
        effective_savings = interest_saved - prepayment_amount * 0.02
        
        return PrepaymentResult(
            original_schedule=original,
            new_schedule=new_schedule,
            interest_saved=round(interest_saved, 2),
            months_reduced=months_reduced,
            prepayment_amount=prepayment_amount,
            prepayment_month=prepayment_month,
            new_tenure_months=new_schedule.loan_term_months,
            effective_savings=round(effective_savings, 2)
        )
    
    def calculate_affordability(
        self,
        monthly_income: float,
        monthly_expenses: float,
        existing_emis: float,
        annual_rate: float,
        tenure_years: int
    ) -> AffordabilityResult:
        max_foi = 0.55
        available_for_emi = monthly_income * max_foi - existing_emis
        available_for_emi = max(available_for_emi, 0)
        
        comfortable_emi = monthly_income * 0.35 - existing_emis
        stretch_emi = monthly_income * 0.50 - existing_emis
        recommended_emi = available_for_emi * 0.8
        
        monthly_rate = annual_rate / 12 / 100
        n_months = tenure_years * 12
        
        if monthly_rate == 0:
            max_principal = available_for_emi * n_months
        else:
            max_principal = available_for_emi * ((1 + monthly_rate) ** n_months - 1) / (monthly_rate * (1 + monthly_rate) ** n_months)
        
        dti_recommended = (monthly_expenses + existing_emis + recommended_emi) / monthly_income * 100
        dti_stretch = (monthly_expenses + existing_emis + stretch_emi) / monthly_income * 100
        
        return AffordabilityResult(
            max_principal=round(max_principal, 2),
            recommended_emi=round(recommended_emi, 2),
            comfortable_emi=round(max(comfortable_emi, 0), 2),
            stretch_emi=round(max(stretch_emi, 0), 2),
            tenure_years=tenure_years,
            interest_rate=annual_rate,
            dti_at_recommended=round(dti_recommended, 2),
            dti_at_stretch=round(dti_stretch, 2)
        )


tool_registry = ToolRegistry()