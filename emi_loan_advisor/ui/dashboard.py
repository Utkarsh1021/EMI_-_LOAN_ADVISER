import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from agent.core import LoanAdvisorAgent
from agent.tools import tool_registry
from agent.models import LoanType


def render_dashboard_tab(agent: LoanAdvisorAgent):
    st.subheader("📊 Dashboard & Visualizations")
    
    viz_type = st.selectbox(
        "Select Visualization",
        ["Amortization Charts", "Loan Comparison", "Prepayment Analysis", "Affordability Gauge", "Scenario Analysis"]
    )
    
    if viz_type == "Amortization Charts":
        render_amortization_dashboard(agent)
    elif viz_type == "Loan Comparison":
        render_comparison_dashboard(agent)
    elif viz_type == "Prepayment Analysis":
        render_prepayment_dashboard(agent)
    elif viz_type == "Affordability Gauge":
        render_affordability_dashboard(agent)
    elif viz_type == "Scenario Analysis":
        render_scenario_dashboard(agent)


def render_amortization_dashboard(agent: LoanAdvisorAgent):
    st.markdown("### Amortization Visualization")
    
    col1, col2 = st.columns(2)
    with col1:
        principal = st.number_input("Loan Amount (₹)", min_value=100000, value=5000000, step=100000, key="dash_principal")
        annual_rate = st.number_input("Interest Rate (% p.a.)", min_value=1.0, max_value=30.0, value=9.0, step=0.1, key="dash_rate")
    with col2:
        tenure_years = st.number_input("Tenure (Years)", min_value=1, max_value=30, value=20, key="dash_tenure")
        view_type = st.radio("View", ["Monthly", "Yearly Summary"], horizontal=True)
    
    if st.button("Generate Charts", type="primary"):
        with st.spinner("Generating..."):
            result = tool_registry.execute("generate_amortization", {
                "principal": principal,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years
            })
        
        if result.success:
            schedule = result.data
            rows = schedule.rows
            
            months = [r.month for r in rows]
            principal_paid = [r.principal_paid for r in rows]
            interest_paid = [r.interest_paid for r in rows]
            balance = [r.closing_balance for r in rows]
            cum_principal = [r.cumulative_principal for r in rows]
            cum_interest = [r.cumulative_interest for r in rows]
            
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(name='Principal', x=months, y=principal_paid, marker_color='#2E86C1'))
            fig1.add_trace(go.Bar(name='Interest', x=months, y=interest_paid, marker_color='#E74C3C'))
            fig1.update_layout(
                barmode='stack',
                title='Monthly Principal vs Interest',
                xaxis_title='Month',
                yaxis_title='Amount (₹)',
                height=400
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=months, y=balance, mode='lines', name='Outstanding', line=dict(color='#27AE60', width=2), fill='tozeroy'))
            fig2.add_trace(go.Scatter(x=months, y=cum_principal, mode='lines', name='Cumulative Principal Paid', line=dict(color='#2E86C1', width=2)))
            fig2.add_trace(go.Scatter(x=months, y=cum_interest, mode='lines', name='Cumulative Interest Paid', line=dict(color='#E74C3C', width=2)))
            fig2.update_layout(
                title='Balance & Cumulative Payments',
                xaxis_title='Month',
                yaxis_title='Amount (₹)',
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            if view_type == "Yearly Summary":
                yearly_data = {}
                for r in rows:
                    yr = r.year
                    if yr not in yearly_data:
                        yearly_data[yr] = {'principal': 0, 'interest': 0, 'payment': 0}
                    yearly_data[yr]['principal'] += r.principal_paid
                    yearly_data[yr]['interest'] += r.interest_paid
                    yearly_data[yr]['payment'] += r.emi
                
                years = sorted(yearly_data.keys())
                y_principal = [yearly_data[y]['principal'] for y in years]
                y_interest = [yearly_data[y]['interest'] for y in years]
                y_payment = [yearly_data[y]['payment'] for y in years]
                
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(name='Principal', x=[f'Year {y}' for y in years], y=y_principal, marker_color='#2E86C1'))
                fig3.add_trace(go.Bar(name='Interest', x=[f'Year {y}' for y in years], y=y_interest, marker_color='#E74C3C'))
                fig3.update_layout(barmode='stack', title='Yearly Payment Breakdown', height=350)
                st.plotly_chart(fig3, use_container_width=True)
                
                df_yearly = pd.DataFrame({
                    'Year': years,
                    'Principal Paid': y_principal,
                    'Interest Paid': y_interest,
                    'Total Payment': y_payment
                })
                st.dataframe(df_yearly.style.format({'Principal Paid': '₹{:,.0f}', 'Interest Paid': '₹{:,.0f}', 'Total Payment': '₹{:,.0f}'}), use_container_width=True)


def render_comparison_dashboard(agent: LoanAdvisorAgent):
    st.markdown("### Loan Comparison Dashboard")
    
    num_loans = st.number_input("Number of Loans", min_value=2, max_value=6, value=3)
    
    loans = []
    for i in range(num_loans):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(f"Loan {i+1} Name", value=f"Option {i+1}", key=f"cmp_name_{i}")
            principal = st.number_input(f"Amount (₹)", min_value=100000, value=5000000, step=100000, key=f"cmp_principal_{i}")
        with col2:
            rate = st.number_input(f"Rate (%)", min_value=1.0, max_value=30.0, value=9.0 - i*0.3, step=0.1, key=f"cmp_rate_{i}")
            tenure = st.number_input(f"Tenure (Yrs)", min_value=1, max_value=30, value=20, key=f"cmp_tenure_{i}")
        with col3:
            fee = st.number_input(f"Fee (₹)", min_value=0, value=0, step=1000, key=f"cmp_fee_{i}")
            lender = st.text_input(f"Lender", value="", key=f"cmp_lender_{i}")
        
        loans.append({
            "name": name,
            "lender": lender,
            "principal": principal,
            "annual_rate": rate,
            "tenure_years": tenure,
            "processing_fee": fee
        })
    
    if st.button("Compare & Visualize", type="primary"):
        with st.spinner("Comparing..."):
            result = tool_registry.execute("compare_loans", {"options": loans})
        
        if result.success:
            data = result.data
            df = pd.DataFrame(data.comparison_table)
            
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                name='Monthly EMI',
                x=df['name'],
                y=df['monthly_emi'],
                marker_color='#3498DB',
                text=[f'₹{v:,.0f}' for v in df['monthly_emi']],
                textposition='auto'
            ))
            fig1.update_layout(title='Monthly EMI Comparison', yaxis_title='EMI (₹)', height=350)
            st.plotly_chart(fig1, use_container_width=True)
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name='Total Interest',
                x=df['name'],
                y=df['total_interest'],
                marker_color='#E74C3C',
                text=[f'₹{v:,.0f}' for v in df['total_interest']],
                textposition='auto'
            ))
            fig2.add_trace(go.Bar(
                name='Processing Fee',
                x=df['name'],
                y=df['processing_fee'],
                marker_color='#F39C12',
                text=[f'₹{v:,.0f}' for v in df['processing_fee']],
                textposition='auto'
            ))
            fig2.update_layout(
                title='Total Cost Comparison',
                yaxis_title='Amount (₹)',
                barmode='stack',
                height=350
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            fig3 = px.scatter(
                df, x='annual_rate', y='monthly_emi', size='principal',
                color='name', hover_data=['tenure_years', 'total_payment'],
                title='Rate vs EMI (bubble size = principal)',
                labels={'annual_rate': 'Interest Rate (%)', 'monthly_emi': 'Monthly EMI (₹)'}
            )
            fig3.update_layout(height=350)
            st.plotly_chart(fig3, use_container_width=True)
            
            st.dataframe(df[['name', 'lender', 'principal', 'annual_rate', 'tenure_years', 'monthly_emi', 'total_interest', 'total_payment']], use_container_width=True)


def render_prepayment_dashboard(agent: LoanAdvisorAgent):
    st.markdown("### Prepayment Impact Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        principal = st.number_input("Loan Amount (₹)", min_value=100000, value=5000000, step=100000, key="prepay_principal")
        annual_rate = st.number_input("Rate (% p.a.)", min_value=1.0, max_value=30.0, value=9.0, step=0.1, key="prepay_rate")
        tenure_years = st.number_input("Tenure (Years)", min_value=1, max_value=30, value=20, key="prepay_tenure")
    with col2:
        prepay_amount = st.number_input("Prepayment Amount (₹)", min_value=10000, value=500000, step=10000, key="prepay_amt")
        prepay_month = st.number_input("Prepay at Month", min_value=1, max_value=360, value=24, key="prepay_month")
    
    if st.button("Analyze Prepayment", type="primary"):
        with st.spinner("Analyzing..."):
            result = tool_registry.execute("calculate_prepayment_impact", {
                "principal": principal,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years,
                "prepayment_amount": prepay_amount,
                "prepayment_month": prepay_month
            })
        
        if result.success:
            data = result.data
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Interest Saved", f"₹{data.interest_saved:,.0f}")
            col2.metric("Months Saved", data.months_reduced)
            col3.metric("New Tenure", f"{data.new_tenure_months} months")
            col4.metric("Net Savings", f"₹{data.effective_savings:,.0f}")
            
            orig_schedule = data.original_schedule
            new_schedule = data.new_schedule
            
            orig_months = [r.month for r in orig_schedule.rows]
            orig_balance = [r.closing_balance for r in orig_schedule.rows]
            new_months = [r.month for r in new_schedule.rows]
            new_balance = [r.closing_balance for r in new_schedule.rows]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=orig_months, y=orig_balance, mode='lines', name='Original Schedule', line=dict(color='#E74C3C', width=2)))
            fig.add_trace(go.Scatter(x=new_months, y=new_balance, mode='lines', name='After Prepayment', line=dict(color='#27AE60', width=2)))
            fig.add_vline(x=prepay_month, line_dash="dash", line_color="orange", annotation_text="Prepayment")
            fig.update_layout(
                title='Outstanding Balance: Original vs After Prepayment',
                xaxis_title='Month',
                yaxis_title='Balance (₹)',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            orig_cum_int = [r.cumulative_interest for r in orig_schedule.rows]
            new_cum_int = [r.cumulative_interest for r in new_schedule.rows]
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=orig_months, y=orig_cum_int, mode='lines', name='Original Cumulative Interest', line=dict(color='#E74C3C', width=2)))
            fig2.add_trace(go.Scatter(x=new_months, y=new_cum_int, mode='lines', name='New Cumulative Interest', line=dict(color='#27AE60', width=2)))
            fig2.add_vline(x=prepay_month, line_dash="dash", line_color="orange", annotation_text="Prepayment")
            fig2.update_layout(
                title='Cumulative Interest Paid Over Time',
                xaxis_title='Month',
                yaxis_title='Cumulative Interest (₹)',
                height=350
            )
            st.plotly_chart(fig2, use_container_width=True)


def render_affordability_dashboard(agent: LoanAdvisorAgent):
    st.markdown("### Affordability Gauge & Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        income = st.number_input("Monthly Income (₹)", min_value=10000, value=150000, step=5000, key="aff_income")
        expenses = st.number_input("Monthly Expenses (₹)", min_value=0, value=60000, step=5000, key="aff_expenses")
        existing_emis = st.number_input("Existing EMIs (₹)", min_value=0, value=0, step=1000, key="aff_existing")
    with col2:
        rate = st.number_input("Rate (% p.a.)", min_value=1.0, max_value=30.0, value=9.0, step=0.1, key="aff_rate")
        tenure = st.number_input("Tenure (Years)", min_value=1, max_value=30, value=20, key="aff_tenure")
    
    if st.button("Analyze Affordability", type="primary"):
        with st.spinner("Analyzing..."):
            result = tool_registry.execute("calculate_affordability", {
                "monthly_income": income,
                "monthly_expenses": expenses,
                "existing_emis": existing_emis,
                "annual_rate": rate,
                "tenure_years": tenure
            })
        
        if result.success:
            data = result.data
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=data.dti_at_recommended,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "DTI Ratio at Recommended EMI (%)"},
                delta={'reference': 40},
                gauge={
                    'axis': {'range': [0, 60]},
                    'bar': {'color': "#2E86C1"},
                    'steps': [
                        {'range': [0, 30], 'color': "#2ECC71"},
                        {'range': [30, 40], 'color': "#F39C12"},
                        {'range': [40, 50], 'color': "#E67E22"},
                        {'range': [50, 60], 'color': "#E74C3C"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 50
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Max Loan", f"₹{data.max_principal:,.0f}")
            col2.metric("Recommended EMI", f"₹{data.recommended_emi:,.0f}")
            col3.metric("Stretch EMI", f"₹{data.stretch_emi:,.0f}")
            
            categories = ['Expenses', 'Existing EMIs', 'Recommended EMI', 'Stretch EMI', 'Disposable']
            values = [expenses, existing_emis, data.recommended_emi, data.stretch_emi, max(0, income - expenses - existing_emis - data.stretch_emi)]
            
            fig2 = go.Figure(go.Bar(
                x=categories,
                y=values,
                marker_color=['#95A5A6', '#E74C3C', '#2E86C1', '#F39C12', '#27AE60'],
                text=[f'₹{v:,.0f}' for v in values],
                textposition='auto'
            ))
            fig2.update_layout(title='Monthly Cash Flow Breakdown', yaxis_title='Amount (₹)', height=350)
            st.plotly_chart(fig2, use_container_width=True)


def render_scenario_dashboard(agent: LoanAdvisorAgent):
    st.markdown("### Scenario Analysis")
    
    st.markdown("Compare multiple scenarios side by side")
    
    num_scenarios = st.number_input("Scenarios", min_value=2, max_value=5, value=3)
    
    scenarios = []
    for i in range(num_scenarios):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(f"Scenario {i+1}", value=f"Scenario {i+1}", key=f"scen_name_{i}")
            principal = st.number_input(f"Amount", min_value=100000, value=5000000 + i*500000, step=100000, key=f"scen_principal_{i}")
        with col2:
            rate = st.number_input(f"Rate", min_value=1.0, max_value=30.0, value=9.0 - i*0.2, step=0.1, key=f"scen_rate_{i}")
            tenure = st.number_input(f"Tenure", min_value=1, max_value=30, value=20, key=f"scen_tenure_{i}")
        with col3:
            prepay = st.number_input(f"Prepay (₹)", min_value=0, value=i*200000, step=50000, key=f"scen_prepay_{i}")
            prepay_month = st.number_input(f"At Month", min_value=1, max_value=360, value=24, key=f"scen_month_{i}")
        
        scenarios.append({
            "name": name,
            "principal": principal,
            "rate": rate,
            "tenure": tenure,
            "prepay": prepay,
            "prepay_month": prepay_month
        })
    
    if st.button("Run Scenarios", type="primary"):
        results = []
        for s in scenarios:
            emi = tool_registry.execute("calculate_emi", {
                "principal": s["principal"],
                "annual_rate": s["rate"],
                "tenure_years": s["tenure"]
            })
            
            if s["prepay"] > 0:
                prepay = tool_registry.execute("calculate_prepayment_impact", {
                    "principal": s["principal"],
                    "annual_rate": s["rate"],
                    "tenure_years": s["tenure"],
                    "prepayment_amount": s["prepay"],
                    "prepayment_month": s["prepay_month"]
                })
                if prepay.success:
                    total_interest = prepay.data.new_schedule.total_interest
                    months = prepay.data.new_tenure_months
                else:
                    total_interest = emi.data.total_interest if emi.success else 0
                    months = s["tenure"] * 12
            else:
                total_interest = emi.data.total_interest if emi.success else 0
                months = s["tenure"] * 12
            
            if emi.success:
                results.append({
                    "Scenario": s["name"],
                    "Principal": s["principal"],
                    "Rate": s["rate"],
                    "Tenure": s["tenure"],
                    "Monthly EMI": emi.data.monthly_emi,
                    "Total Interest": total_interest,
                    "Total Cost": emi.data.monthly_emi * months,
                    "Loan Term (Months)": months
                })
        
        if results:
            df = pd.DataFrame(results)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Monthly EMI', x=df['Scenario'], y=df['Monthly EMI'], marker_color='#3498DB'))
            fig.add_trace(go.Bar(name='Total Interest', x=df['Scenario'], y=df['Total Interest'], marker_color='#E74C3C'))
            fig.update_layout(barmode='group', title='Scenario Comparison', height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df.style.format({
                'Principal': '₹{:,.0f}',
                'Monthly EMI': '₹{:,.0f}',
                'Total Interest': '₹{:,.0f}',
                'Total Cost': '₹{:,.0f}'
            }), use_container_width=True)