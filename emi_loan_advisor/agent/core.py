import re
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .tools import tool_registry, ToolResult
from .memory import ConversationContext, memory_manager
from .models import (
    LoanOption, EligibilityInput, LoanType, EmploymentType,
    ConversationMemory
)


@dataclass
class PlanStep:
    tool: str
    args: dict
    reason: str


@dataclass
class AgentPlan:
    steps: List[PlanStep]
    reasoning: str


class LoanAdvisorAgent:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or memory_manager.create_session()
        self.memory = memory_manager.load(self.session_id)
        self.context = ConversationContext(self.memory)
        self.tools = tool_registry
    
    def run(self, user_input: str) -> str:
        plan = self._plan(user_input)
        
        tool_results = []
        tool_calls = []
        
        for step in plan.steps:
            result = self.tools.execute(step.tool, step.args)
            tool_results.append(result.model_dump())
            tool_calls.append({
                'tool': step.tool,
                'args': step.args,
                'reason': step.reason
            })
            
            if not result.success:
                break
        
        response = self._respond(user_input, plan, tool_results)
        
        self.context.add_turn(
            user_input=user_input,
            plan=plan.reasoning,
            tool_calls=tool_calls,
            tool_results=tool_results,
            response=response
        )
        
        memory_manager.save(self.memory)
        
        return response
    
    def _plan(self, user_input: str) -> AgentPlan:
        user_lower = user_input.lower()
        profile = self.memory.user_profile
        
        if any(kw in user_lower for kw in ['emi', 'monthly payment', 'installment']):
            return self._plan_emi_calculation(user_input, profile)
        
        if any(kw in user_lower for kw in ['compare', 'comparison', 'vs', 'versus', 'which is better']):
            return self._plan_comparison(user_input, profile)
        
        if any(kw in user_lower for kw in ['eligible', 'eligibility', 'can i get', 'qualify', 'afford']):
            return self._plan_eligibility(user_input, profile)
        
        if any(kw in user_lower for kw in ['amortization', 'schedule', 'breakdown', 'yearly', 'monthly breakup']):
            return self._plan_amortization(user_input, profile)
        
        if any(kw in user_lower for kw in ['prepay', 'prepayment', 'early payment', 'lump sum', 'part payment']):
            return self._plan_prepayment(user_input, profile)
        
        if any(kw in user_lower for kw in ['afford', 'budget', 'how much can i borrow', 'max loan']):
            return self._plan_affordability(user_input, profile)
        
        if any(kw in user_lower for kw in ['profile', 'my details', 'my income', 'update']):
            return self._plan_profile_update(user_input)
        
        return self._plan_general_advice(user_input, profile)
    
    def _extract_numbers(self, text: str) -> List[float]:
        numbers = []
        text_lower = text.lower()
        
        # Handle Cr (crores), L (lakhs), K (thousands) - remove them from text after extracting
        working_text = text_lower
        
        crore_matches = re.findall(r'(\d+\.?\d*)\s*cr', working_text)
        for m in crore_matches:
            numbers.append(float(m) * 10000000)
        working_text = re.sub(r'(\d+\.?\d*)\s*cr', '', working_text)
        
        lakh_matches = re.findall(r'(\d+\.?\d*)\s*lakh', working_text)
        for m in lakh_matches:
            numbers.append(float(m) * 100000)
        working_text = re.sub(r'(\d+\.?\d*)\s*lakh', '', working_text)
        
        # Also handle "L" as lakhs (but not as part of words like "at 8.5%")
        l_matches = re.findall(r'(\d+\.?\d*)\s*l\b', working_text)
        for m in l_matches:
            numbers.append(float(m) * 100000)
        working_text = re.sub(r'(\d+\.?\d*)\s*l\b', '', working_text)
        
        k_matches = re.findall(r'(\d+\.?\d*)\s*k(?![a-z])', working_text)
        for m in k_matches:
            numbers.append(float(m) * 1000)
        working_text = re.sub(r'(\d+\.?\d*)\s*k(?![a-z])', '', working_text)
        
        # Handle regular numbers with commas (including decimals)
        regular_matches = re.findall(r'\d+\.?\d*', working_text)
        for m in regular_matches:
            val = float(m)
            if val not in numbers:
                numbers.append(val)
        
        return numbers
    
    def _extract_loan_type(self, text: str) -> LoanType:
        text_lower = text.lower()
        if 'home' in text_lower or 'housing' in text_lower:
            return LoanType.HOME
        if 'personal' in text_lower:
            return LoanType.PERSONAL
        if 'car' in text_lower or 'auto' in text_lower:
            return LoanType.CAR
        if 'education' in text_lower or 'student' in text_lower:
            return LoanType.EDUCATION
        if 'gold' in text_lower:
            return LoanType.GOLD
        if 'property' in text_lower or 'mortgage' in text_lower or 'lap' in text_lower:
            return LoanType.PROPERTY
        if 'two wheeler' in text_lower or 'bike' in text_lower or 'scooter' in text_lower:
            return LoanType.TWO_WHEELER
        if 'consumer' in text_lower or 'durable' in text_lower or 'mobile' in text_lower or 'tv' in text_lower:
            return LoanType.CONSUMER_DURABLE
        return LoanType.PERSONAL
    
    def _plan_emi_calculation(self, user_input: str, profile) -> AgentPlan:
        numbers = self._extract_numbers(user_input)
        loan_type = self._extract_loan_type(user_input)
        
        principal = numbers[0] if numbers else (profile.monthly_income * 12 * 5 if profile and profile.monthly_income else 5000000)
        rate = numbers[1] if len(numbers) > 1 else 9.0
        tenure = int(numbers[2]) if len(numbers) > 2 else 20
        
        args = {
            'principal': principal,
            'annual_rate': rate,
            'tenure_years': tenure,
            'processing_fee': principal * 0.005 if loan_type == LoanType.HOME else principal * 0.02
        }
        
        return AgentPlan(
            steps=[PlanStep('calculate_emi', args, f"Calculate EMI for ₹{principal:,.0f} at {rate}% for {tenure} years")],
            reasoning=f"User wants EMI calculation for {loan_type.value} loan"
        )
    
    def _plan_comparison(self, user_input: str, profile) -> AgentPlan:
        numbers = self._extract_numbers(user_input)
        
        # Detect pattern: two large similar numbers = two principals
        if len(numbers) >= 5 and numbers[0] > 100000 and numbers[1] > 100000 and abs(numbers[0] - numbers[1]) / max(numbers[0], numbers[1]) < 0.1:
            # Pattern: principal1, principal2, rate1, rate2, tenure
            options = [
                {'name': 'Option 1', 'principal': numbers[0], 'annual_rate': numbers[2], 'tenure_years': int(numbers[4])},
                {'name': 'Option 2', 'principal': numbers[1], 'annual_rate': numbers[3], 'tenure_years': int(numbers[4])},
            ]
        elif len(numbers) >= 5:
            # Try to parse as: principal1, rate1, principal2, rate2, tenure
            options = [
                {'name': 'Option 1', 'principal': numbers[0], 'annual_rate': numbers[1], 'tenure_years': int(numbers[4])},
                {'name': 'Option 2', 'principal': numbers[2], 'annual_rate': numbers[3], 'tenure_years': int(numbers[4])},
            ]
        elif len(numbers) >= 4:
            # principal, rate1, rate2, tenure
            options = [
                {'name': 'Option 1', 'principal': numbers[0], 'annual_rate': numbers[1], 'tenure_years': int(numbers[3])},
                {'name': 'Option 2', 'principal': numbers[0], 'annual_rate': numbers[2], 'tenure_years': int(numbers[3])},
            ]
        elif len(numbers) >= 3:
            # principal, rate1, rate2 (same tenure)
            principal = numbers[0]
            options = [
                {'name': 'Option 1', 'principal': principal, 'annual_rate': numbers[1], 'tenure_years': 20},
                {'name': 'Option 2', 'principal': principal, 'annual_rate': numbers[2], 'tenure_years': 20},
            ]
        else:
            principal = numbers[0] if numbers else 5000000
            options = [
                {'name': 'Current Offer', 'principal': principal, 'annual_rate': 9.0, 'tenure_years': 20},
                {'name': 'Alternative', 'principal': principal, 'annual_rate': 8.5, 'tenure_years': 20},
            ]
        
        return AgentPlan(
            steps=[PlanStep('compare_loans', {'options': options}, "Compare loan options side by side")],
            reasoning="User wants to compare multiple loan offers"
        )
    
    def _plan_eligibility(self, user_input: str, profile) -> AgentPlan:
        loan_type = self._extract_loan_type(user_input)
        
        income = profile.monthly_income if profile and profile.monthly_income else 100000
        expenses = profile.monthly_expenses if profile and profile.monthly_expenses else income * 0.4
        existing_emis = profile.existing_emis if profile and profile.existing_emis else 0
        age = profile.age if profile and profile.age else 35
        employment = profile.employment_type if profile and profile.employment_type else EmploymentType.SALARIED
        credit_score = profile.credit_score if profile and profile.credit_score else 750
        
        args = {
            'monthly_income': income,
            'monthly_expenses': expenses,
            'existing_emis': existing_emis,
            'age': age,
            'employment_type': employment.value,
            'credit_score': credit_score,
            'loan_type': loan_type.value,
            'desired_tenure_years': 20
        }
        
        return AgentPlan(
            steps=[PlanStep('check_eligibility', args, f"Check {loan_type.value} loan eligibility")],
            reasoning=f"User wants to check eligibility for {loan_type.value} loan"
        )
    
    def _plan_amortization(self, user_input: str, profile) -> AgentPlan:
        numbers = self._extract_numbers(user_input)
        principal = numbers[0] if numbers else 5000000
        rate = numbers[1] if len(numbers) > 1 else 9.0
        tenure = int(numbers[2]) if len(numbers) > 2 else 20
        
        args = {'principal': principal, 'annual_rate': rate, 'tenure_years': tenure}
        
        return AgentPlan(
            steps=[PlanStep('generate_amortization', args, "Generate full amortization schedule")],
            reasoning="User wants detailed amortization breakdown"
        )
    
    def _plan_prepayment(self, user_input: str, profile) -> AgentPlan:
        numbers = self._extract_numbers(user_input)
        
        if len(numbers) >= 5:
            principal, rate, tenure, prepay_amt, prepay_month = numbers[:5]
        else:
            last_emi = self.context.get_last_tool_result('calculate_emi')
            last_amort = self.context.get_last_tool_result('generate_amortization')
            
            if last_emi:
                principal = last_emi.get('principal', 5000000)
                rate = 9.0
                tenure = 20
            elif last_amort:
                principal = last_amort.get('total_principal', 5000000)
                rate = 9.0
                tenure = 20
            else:
                principal, rate, tenure = 5000000, 9.0, 20
            
            prepay_amt = numbers[0] if numbers else principal * 0.1
            prepay_month = int(numbers[1]) if len(numbers) > 1 else 24
        
        args = {
            'principal': principal,
            'annual_rate': rate,
            'tenure_years': tenure,
            'prepayment_amount': prepay_amt,
            'prepayment_month': prepay_month
        }
        
        return AgentPlan(
            steps=[PlanStep('calculate_prepayment_impact', args, "Calculate prepayment impact")],
            reasoning="User wants to know impact of prepayment"
        )
    
    def _plan_affordability(self, user_input: str, profile) -> AgentPlan:
        income = profile.monthly_income if profile and profile.monthly_income else 100000
        expenses = profile.monthly_expenses if profile and profile.monthly_expenses else income * 0.4
        existing_emis = profile.existing_emis if profile and profile.existing_emis else 0
        rate = 9.0
        tenure = 20
        
        args = {
            'monthly_income': income,
            'monthly_expenses': expenses,
            'existing_emis': existing_emis,
            'annual_rate': rate,
            'tenure_years': tenure
        }
        
        return AgentPlan(
            steps=[PlanStep('calculate_affordability', args, "Calculate loan affordability")],
            reasoning="User wants to know how much loan they can afford"
        )
    
    def _plan_profile_update(self, user_input: str) -> AgentPlan:
        numbers = self._extract_numbers(user_input)
        updates = {}
        
        if 'income' in user_input.lower() and numbers:
            updates['monthly_income'] = numbers[0]
        if 'expense' in user_input.lower() and len(numbers) > 1:
            updates['monthly_expenses'] = numbers[1]
        if 'emi' in user_input.lower() and 'existing' in user_input.lower() and numbers:
            updates['existing_emis'] = numbers[0]
        if 'age' in user_input.lower() and numbers:
            updates['age'] = int(numbers[0])
        
        self.context.update_profile(**updates)
        memory_manager.save(self.memory)
        
        return AgentPlan(
            steps=[],
            reasoning="Updated user profile"
        )
    
    def _plan_general_advice(self, user_input: str, profile) -> AgentPlan:
        return AgentPlan(
            steps=[],
            reasoning="General loan advice query"
        )
    
    def _respond(self, user_input: str, plan: AgentPlan, tool_results: List[Dict]) -> str:
        if not tool_results:
            return self._generate_general_response(user_input)
        
        successful_results = [r for r in tool_results if r.get('success')]
        if not successful_results:
            return "I encountered an error processing your request. Please try again with more details."
        
        responses = []
        for result in successful_results:
            tool_name = result.get('tool_name')
            data = result.get('data')
            
            if tool_name == 'calculate_emi':
                responses.append(self._format_emi_response(data))
            elif tool_name == 'compare_loans':
                responses.append(self._format_comparison_response(data))
            elif tool_name == 'check_eligibility':
                responses.append(self._format_eligibility_response(data))
            elif tool_name == 'generate_amortization':
                responses.append(self._format_amortization_response(data))
            elif tool_name == 'calculate_prepayment_impact':
                responses.append(self._format_prepayment_response(data))
            elif tool_name == 'calculate_affordability':
                responses.append(self._format_affordability_response(data))
        
        return "\n\n".join(responses)
    
    def _format_emi_response(self, data: Dict) -> str:
        return f"""**EMI Calculation Result**
- **Monthly EMI:** ₹{data['monthly_emi']:,.2f}
- **Total Interest:** ₹{data['total_interest']:,.2f}
- **Total Payment (incl. fees):** ₹{data['total_payment']:,.2f}
- **Principal:** ₹{data['principal']:,.2f}
- **Processing Fee:** ₹{data['processing_fee']:,.2f}
- **Effective Annual Rate:** {data['effective_rate']:.2f}%"""
    
    def _format_comparison_response(self, data: Dict) -> str:
        lines = ["**Loan Comparison**\n"]
        lines.append("| Option | Principal | Rate | Tenure | EMI | Total Interest | Total Cost |")
        lines.append("|--------|-----------|------|--------|-----|----------------|------------|")
        
        for opt in data['comparison_table']:
            lines.append(
                f"| {opt['name']} | ₹{opt['principal']:,.0f} | {opt['annual_rate']}% | "
                f"{opt['tenure_years']}yr | ₹{opt['monthly_emi']:,.0f} | "
                f"₹{opt['total_interest']:,.0f} | ₹{opt['total_payment']:,.0f} |"
            )
        
        # Find calculated values for best options from comparison_table
        table = {opt['name']: opt for opt in data['comparison_table']}
        
        def get_calc(name, key):
            return table.get(name, {}).get(key, 0)
        
        best_name = data['best_overall'].name if hasattr(data['best_overall'], 'name') else data['best_overall'].get('name')
        lowest_emi_name = data['lowest_emi'].name if hasattr(data['lowest_emi'], 'name') else data['lowest_emi'].get('name')
        lowest_int_name = data['lowest_total_interest'].name if hasattr(data['lowest_total_interest'], 'name') else data['lowest_total_interest'].get('name')
        
        lines.append(f"\n**Best Overall:** {best_name} (Lowest total cost: ₹{get_calc(best_name, 'total_payment'):,.0f})")
        lines.append(f"**Lowest EMI:** {lowest_emi_name} (₹{get_calc(lowest_emi_name, 'monthly_emi'):,.0f}/month)")
        lines.append(f"**Lowest Interest:** {lowest_int_name} (₹{get_calc(lowest_int_name, 'total_interest'):,.0f})")
        
        return "\n".join(lines)
    
    def _format_eligibility_response(self, data: Dict) -> str:
        status = "✅ **ELIGIBLE**" if data['eligible'] else "❌ **NOT ELIGIBLE**"
        
        lines = [f"**Loan Eligibility Assessment** - {status}\n"]
        lines.append(f"- **Max Loan Amount:** ₹{data['max_loan_amount']:,.0f}")
        lines.append(f"- **Max EMI You Can Afford:** ₹{data['max_emi']:,.0f}/month")
        lines.append(f"- **Recommended EMI:** ₹{data['recommended_emi']:,.0f}/month")
        lines.append(f"- **Recommended Tenure:** {data['recommended_tenure_years']} years")
        lines.append(f"- **DTI Ratio:** {data['dti_ratio']:.1f}%")
        lines.append(f"- **FOI Ratio:** {data['foi_ratio']:.1f}%")
        lines.append(f"- **Income Multiplier:** {data['income_multiplier']:.1f}x")
        
        if data.get('loan_to_value_ratio'):
            lines.append(f"- **Loan-to-Value:** {data['loan_to_value_ratio']:.1f}%")
        
        if data['notes']:
            lines.append("\n**Notes:**")
            for note in data['notes']:
                lines.append(f"  ⚠️ {note}")
        
        return "\n".join(lines)
    
    def _format_amortization_response(self, data: Dict) -> str:
        rows = data.get('rows', [])
        if not rows:
            return "Amortization schedule generated."
        
        lines = ["**Amortization Schedule (First 12 months)**\n"]
        lines.append("| Month | Opening Bal | EMI | Principal | Interest | Closing Bal |")
        lines.append("|-------|-------------|-----|-----------|----------|-------------|")
        
        for row in rows[:12]:
            lines.append(
                f"| {row['month']} | ₹{row['opening_balance']:,.0f} | "
                f"₹{row['emi']:,.0f} | ₹{row['principal_paid']:,.0f} | "
                f"₹{row['interest_paid']:,.0f} | ₹{row['closing_balance']:,.0f} |"
            )
        
        if len(rows) > 12:
            lines.append(f"\n... and {len(rows) - 12} more months")
        
        lines.append(f"\n**Summary:**")
        lines.append(f"- Total Principal: ₹{data['total_principal']:,.0f}")
        lines.append(f"- Total Interest: ₹{data['total_interest']:,.0f}")
        lines.append(f"- Total Payment: ₹{data['total_payment']:,.0f}")
        lines.append(f"- Loan Term: {data['loan_term_months']} months")
        
        return "\n".join(lines)
    
    def _format_prepayment_response(self, data: Dict) -> str:
        lines = ["**Prepayment Impact Analysis**\n"]
        lines.append(f"- **Prepayment Amount:** ₹{data['prepayment_amount']:,.0f} (Month {data['prepayment_month']})")
        lines.append(f"- **Interest Saved:** ₹{data['interest_saved']:,.0f}")
        lines.append(f"- **Tenure Reduced:** {data['months_reduced']} months")
        lines.append(f"- **New Tenure:** {data['new_tenure_months']} months ({data['new_tenure_months']/12:.1f} years)")
        lines.append(f"- **Effective Savings (after charges):** ₹{data['effective_savings']:,.0f}")
        
        orig = data['original_schedule']
        new = data['new_schedule']
        lines.append(f"\n**Original Total Interest:** ₹{orig['total_interest']:,.0f}")
        lines.append(f"**New Total Interest:** ₹{new['total_interest']:,.0f}")
        
        return "\n".join(lines)
    
    def _format_affordability_response(self, data: Dict) -> str:
        lines = ["**Loan Affordability Assessment**\n"]
        lines.append(f"- **Maximum Loan You Can Afford:** ₹{data['max_principal']:,.0f}")
        lines.append(f"- **Recommended EMI:** ₹{data['recommended_emi']:,.0f}/month (DTI: {data['dti_at_recommended']:.1f}%)")
        lines.append(f"- **Comfortable EMI:** ₹{data['comfortable_emi']:,.0f}/month")
        lines.append(f"- **Stretch EMI (Max):** ₹{data['stretch_emi']:,.0f}/month (DTI: {data['dti_at_stretch']:.1f}%)")
        lines.append(f"- **Assumed Rate:** {data['interest_rate']}% for {data['tenure_years']} years")
        
        return "\n".join(lines)
    
    def _generate_general_response(self, user_input: str) -> str:
        return """I can help you with various loan calculations:

1. **EMI Calculation** - "Calculate EMI for ₹50L at 9% for 20 years"
2. **Loan Comparison** - "Compare 9% vs 8.5% for ₹50L home loan"
3. **Eligibility Check** - "Am I eligible for a home loan with ₹1L income?"
4. **Amortization Schedule** - "Show amortization for ₹50L at 9% for 20 years"
5. **Prepayment Impact** - "What if I prepay ₹5L after 2 years?"
6. **Affordability** - "How much home loan can I afford with ₹1.5L income?"

You can also set your profile: "My income is ₹1.2L, expenses ₹50K, age 32"

What would you like to calculate?"""
    
    def get_session_id(self) -> str:
        return self.session_id
    
    def export_data(self) -> Dict:
        return {
            'session_id': self.session_id,
            'profile': self.memory.user_profile.model_dump(mode='json') if self.memory.user_profile else None,
            'calculations': self.context.get_all_calculations()
        }


def create_agent(session_id: Optional[str] = None) -> LoanAdvisorAgent:
    return LoanAdvisorAgent(session_id)