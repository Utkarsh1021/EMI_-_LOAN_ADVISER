import streamlit as st
from typing import Optional
import json

from agent.core import LoanAdvisorAgent


def render_chat_tab(agent: LoanAdvisorAgent):
    st.subheader("💬 Chat with Loan Advisor")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_tool_details" not in st.session_state:
        st.session_state.show_tool_details = {}
    
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message["role"] == "assistant" and "tool_calls" in message:
                with st.expander("🔧 View Tool Calls", expanded=False):
                    for tc in message["tool_calls"]:
                        st.json(tc)
    
    if prompt := st.chat_input("Ask about EMI, eligibility, loan comparison, prepayment..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = agent.run(prompt)
            
            tool_calls = []
            if hasattr(agent.context, 'memory') and agent.context.memory.turns:
                last_turn = agent.context.memory.turns[-1]
                tool_calls = last_turn.tool_calls
            
            st.markdown(response)
            
            if tool_calls:
                with st.expander("🔧 View Tool Calls", expanded=False):
                    for tc in tool_calls:
                        st.json(tc)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "tool_calls": tool_calls
        })
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()


def render_sidebar(agent: LoanAdvisorAgent):
    with st.sidebar:
        st.title("🏦 EMI & Loan Advisor")
        
        st.divider()
        
        st.subheader("👤 Your Profile")
        profile = agent.memory.user_profile
        
        if profile:
            if profile.monthly_income:
                st.metric("Monthly Income", f"₹{profile.monthly_income:,.0f}")
            if profile.monthly_expenses:
                st.metric("Monthly Expenses", f"₹{profile.monthly_expenses:,.0f}")
            if profile.existing_emis:
                st.metric("Existing EMIs", f"₹{profile.existing_emis:,.0f}")
            if profile.age:
                st.metric("Age", profile.age)
            if profile.employment_type:
                st.metric("Employment", profile.employment_type.value.title())
            if profile.credit_score:
                st.metric("Credit Score", profile.credit_score)
        else:
            st.info("No profile set. Tell the agent your details!")
        
        st.divider()
        
        st.subheader("📊 Session Info")
        st.caption(f"Session ID: `{agent.session_id}`")
        st.caption(f"Turns: {len(agent.memory.turns)}")
        
        st.divider()
        
        st.subheader("💾 Export Data")
        export_format = st.selectbox("Format", ["PDF", "Excel", "Both"])
        
        if st.button("📥 Generate Report"):
            export_data = agent.export_data()
            
            from agent.export import generate_reports
            
            formats = []
            if export_format in ["PDF", "Both"]:
                formats.append("pdf")
            if export_format in ["Excel", "Both"]:
                formats.append("excel")
            
            reports = generate_reports(export_data, formats)
            
            for fmt, data in reports.items():
                ext = "pdf" if fmt == "pdf" else "xlsx"
                mime = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                st.download_button(
                    f"⬇️ Download {fmt.upper()}",
                    data=data,
                    file_name=f"loan_report_{agent.session_id}.{ext}",
                    mime=mime
                )
        
        st.divider()
        
        if st.button("🔄 New Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.caption("💡 Try: 'My income is 1.2L, expenses 50K, age 30. Can I get a 50L home loan?'")