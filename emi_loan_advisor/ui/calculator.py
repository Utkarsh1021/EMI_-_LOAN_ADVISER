import streamlit as st
from typing import Optional
import pandas as pd

from agent.core import LoanAdvisorAgent
from agent.tools import tool_registry
from agent.models import LoanType, EmploymentType


def render_calculator_tab(agent: LoanAdvisorAgent):
    st.subheader("🧮 Loan Calculators")
    
    calc_type = st.selectbox(
        "Select Calculator",
        ["EMI Calculator", "Eligibility Checker", "Loan Comparison", "Prepayment Impact", "Affordability Calculator"]
    )
    
    if calc_type == "EMI Calculator":
        render_emi_calculator(agent)
    elif calc_type == "Eligibility Checker":
        render_eligibility_calculator(agent)
    elif calc_type == "Loan Comparison":
        render_comparison_calculator(agent)
    elif calc_type == "Prepayment Impact":
        render_prepayment_calculator(agent)
    elif calc_type == "Affordability Calculator":
        render_affordability_calculator(agent)


def render_emi_calculator(agent: LoanAdvisorAgent):
    st.markdown("### EMI Calculator")
    
    col1, col2 = st.columns(2)
    with col1:
        loan_type = st.selectbox("Loan Type", [lt.value for lt in LoanType], index=0)
        principal = st.number_input("Loan Amount (₹)", min_value=10000, max_value=100000000, value=5000000, step=100000)
        annual_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.1, max_value=30.0, value=9.0, step=0.1)
    with col2:
        tenure_years = st.number_input("Tenure (Years)", min_value=1, max_value=30, value=20)
        processing_fee = st.number_input("Processing Fee (₹)", min_value=0, value=0, step=1000)
    
    if st.button("Calculate EMI", type="primary"):
        with st.spinner("Calculating..."):
            result = tool_registry.execute("calculate_emi", {
                "principal": principal,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years,
                "processing_fee": processing_fee
            })
        
        if result.success:
            data = result.data
            col1, col2, col3 = st.columns(3)
            col1.metric("Monthly EMI", f"₹{data.monthly_emi:,.2f}")
            col2.metric("Total Interest", f"₹{data.total_interest:,.2f}")
            col3.metric("Total Payment", f"₹{data.total_payment:,.2f}")
            
            st.info(f"Effective Annual Rate: {data.effective_rate:.2f}% | Processing Fee: ₹{data.processing_fee:,.2f}")
            
            schedule = tool_registry.execute("generate_amortization", {
                "principal": principal,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years
            })
            if schedule.success:
                render_amortization_chart(schedule.data)


def render_eligibility_calculator(agent: LoanAdvisorAgent):
    st.markdown("### Eligibility Checker")
    
    col1, col2 = st.columns(2)
    with col1:
        loan_type = st.selectbox("Loan Type", [lt.value for lt in LoanType], index=0)
        monthly_income = st.number_input("Monthly Income (₹)", min_value=10000, value=100000, step=5000)
        monthly_expenses = st.number_input("Monthly Expenses (₹)", min_value=0, value=40000, step=5000)
        existing_emis = st.number_input("Existing EMIs (₹)", min_value=0, value=0, step=1000)
    with col2:
        age = st.number_input("Age", min_value=18, max_value=70, value=35)
        employment_type = st.selectbox("Employment Type", [et.value for et in EmploymentType], index=0)
        credit_score = st.number_input("Credit Score", min_value=300, max_value=900, value=750)
        desired_tenure = st.number_input("Desired Tenure (Years)", min_value=1, max_value=30, value=20)
    
    if st.button("Check Eligibility", type="primary"):
        with st.spinner("Checking eligibility..."):
            result = tool_registry.execute("check_eligibility", {
                "monthly_income": monthly_income,
                "monthly_expenses": monthly_expenses,
                "existing_emis": existing_emis,
                "age": age,
                "employment_type": employment_type,
                "credit_score": credit_score,
                "loan_type": loan_type,
                "desired_tenure_years": desired_tenure
            })
        
        if result.success:
            data = result.data
            status = "✅ ELIGIBLE" if data.eligible else "❌ NOT ELIGIBLE"
            st.markdown(f"### {status}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Max Loan Amount", f"₹{data.max_loan_amount:,.0f}")
            col2.metric("Max Affordable EMI", f"₹{data.max_emi:,.0f}")
            col3.metric("Recommended EMI", f"₹{data.recommended_emi:,.0f}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("DTI Ratio", f"{data.dti_ratio:.1f}%")
            col2.metric("FOI Ratio", f"{data.foi_ratio:.1f}%")
            col3.metric("Income Multiplier", f"{data.income_multiplier:.1f}x")
            
            if data.loan_to_value_ratio:
                st.metric("Loan-to-Value", f"{data.loan_to_value_ratio:.1f}%")
            
            if data.notes:
                st.warning("**Notes:**")
                for note in data.notes:
                    st.write(f"⚠️ {note}")


def render_comparison_calculator(agent: LoanAdvisorAgent):
    st.markdown("### Loan Comparison")
    
    num_options = st.number_input("Number of Options to Compare", min_value=2, max_value=5, value=2)
    
    options = []
    for i in range(num_options):
        st.markdown(f"#### Option {i+1}")
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(f"Name", value=f"Option {i+1}", key=f"name_{i}")
            principal = st.number_input(f"Principal (₹)", min_value=10000, value=5000000, step=100000, key=f"principal_{i}")
        with col2:
            rate = st.number_input(f"Rate (% p.a.)", min_value=0.1, max_value=30.0, value=9.0 - i*0.25, step=0.1, key=f"rate_{i}")
            tenure = st.number_input(f"Tenure (Years)", min_value=1, max_value=30, value=20, key=f"tenure_{i}")
        with col3:
            fee = st.number_input(f"Processing Fee (₹)", min_value=0, value=0, step=1000, key=f"fee_{i}")
            lender = st.text_input(f"Lender", value="", key=f"lender_{i}")
        
        options.append({
            "name": name,
            "principal": principal,
            "annual_rate": rate,
            "tenure_years": tenure,
            "processing_fee": fee,
            "lender": lender
        })
    
    if st.button("Compare Loans", type="primary"):
        with st.spinner("Comparing..."):
            result = tool_registry.execute("compare_loans", {"options": options})
        
        if result.success:
            data = result.data
            
            df = pd.DataFrame(data.comparison_table)
            st.dataframe(df[['name', 'lender', 'principal', 'annual_rate', 'tenure_years', 'monthly_emi', 'total_interest', 'total_payment']], use_container_width=True)
            
            st.markdown("### Summary")
            col1, col2, col3 = st.columns(3)
            col1.success(f"**Best Overall:** {data.best_overall.name}")
            col2.info(f"**Lowest EMI:** {data.lowest_emi.name} (₹{data.lowest_emi.monthly_emi:,.0f})")
            col3.warning(f"**Lowest Interest:** {data.lowest_total_interest.name} (₹{data.lowest_total_interest.total_interest:,.0f})")


def render_prepayment_calculator(agent: LoanAdvisorAgent):
    st.markdown("### Prepayment Impact Calculator")
    
    col1, col2 = st.columns(2)
    with col1:
        principal = st.number_input("Original Loan Amount (₹)", min_value=10000, value=5000000, step=100000)
        annual_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.1, max_value=30.0, value=9.0, step=0.1)
        tenure_years = st.number_input("Original Tenure (Years)", min_value=1, max_value=30, value=20)
    with col2:
        prepayment_amount = st.number_input("Prepayment Amount (₹)", min_value=1000, value=500000, step=10000)
        prepayment_month = st.number_input("Prepayment at Month", min_value=1, max_value=360, value=24)
    
    if st.button("Calculate Impact", type="primary"):
        with st.spinner("Calculating..."):
            result = tool_registry.execute("calculate_prepayment_impact", {
                "principal": principal,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years,
                "prepayment_amount": prepayment_amount,
                "prepayment_month": prepayment_month
            })
        
        if result.success:
            data = result.data
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Interest Saved", f"₹{data.interest_saved:,.0f}")
            col2.metric("Months Reduced", data.months_reduced)
            col3.metric("New Tenure", f"{data.new_tenure_months} months")
            col4.metric("Effective Savings", f"₹{data.effective_savings:,.0f}")
            
            st.markdown("### Comparison")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Original Total Interest", f"₹{data.original_schedule.total_interest:,.0f}")
                st.metric("Original Tenure", f"{data.original_schedule.loan_term_months} months")
            with col2:
                st.metric("New Total Interest", f"₹{data.new_schedule.total_interest:,.0f}")
                st.metric("New Tenure", f"{data.new_tenure_months} months")


def render_affordability_calculator(agent: LoanAdvisorAgent):
    st.markdown("### Affordability Calculator")
    
    col1, col2 = st.columns(2)
    with col1:
        monthly_income = st.number_input("Monthly Income (₹)", min_value=10000, value=150000, step=5000)
        monthly_expenses = st.number_input("Monthly Expenses (₹)", min_value=0, value=60000, step=5000)
        existing_emis = st.number_input("Existing EMIs (₹)", min_value=0, value=0, step=1000)
    with col2:
        annual_rate = st.number_input("Expected Rate (% p.a.)", min_value=0.1, max_value=30.0, value=9.0, step=0.1)
        tenure_years = st.number_input("Preferred Tenure (Years)", min_value=1, max_value=30, value=20)
    
    if st.button("Calculate Affordability", type="primary"):
        with st.spinner("Calculating..."):
            result = tool_registry.execute("calculate_affordability", {
                "monthly_income": monthly_income,
                "monthly_expenses": monthly_expenses,
                "existing_emis": existing_emis,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years
            })
        
        if result.success:
            data = result.data
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Max Affordable Loan", f"₹{data.max_principal:,.0f}")
            col2.metric("Recommended EMI", f"₹{data.recommended_emi:,.0f}")
            col3.metric("Comfortable EMI", f"₹{data.comfortable_emi:,.0f}")
            
            st.metric("Stretch EMI (Max)", f"₹{data.stretch_emi:,.0f}")
            
            col1, col2 = st.columns(2)
            col1.metric("DTI at Recommended", f"{data.dti_at_recommended:.1f}%")
            col2.metric("DTI at Stretch", f"{data.dti_at_stretch:.1f}%")


def render_amortization_chart(schedule_data):
    import plotly.graph_objects as go
    
    rows = schedule_data.rows
    months = [r.month for r in rows]
    principal_paid = [r.principal_paid for r in rows]
    interest_paid = [r.interest_paid for r in rows]
    balance = [r.closing_balance for r in rows]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Principal', x=months, y=principal_paid, marker_color='#2E86C1'))
    fig.add_trace(go.Bar(name='Interest', x=months, y=interest_paid, marker_color='#E74C3C'))
    fig.update_layout(
        barmode='stack',
        title='Monthly Principal vs Interest Payment',
        xaxis_title='Month',
        yaxis_title='Amount (₹)',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=months, y=balance, mode='lines', name='Outstanding Balance', line=dict(color='#27AE60', width=2)))
    fig2.update_layout(
        title='Outstanding Balance Over Time',
        xaxis_title='Month',
        yaxis_title='Balance (₹)',
        height=300
    )
    st.plotly_chart(fig2, use_container_width=True)