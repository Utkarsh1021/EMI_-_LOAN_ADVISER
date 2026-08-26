import streamlit as st

from agent.core import create_agent, LoanAdvisorAgent
from ui.chat import render_chat_tab, render_sidebar
from ui.calculator import render_calculator_tab
from ui.dashboard import render_dashboard_tab


def main():
    st.set_page_config(
        page_title="EMI & Loan Advisor",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if "agent" not in st.session_state:
        st.session_state.agent = create_agent()
    
    agent: LoanAdvisorAgent = st.session_state.agent
    
    render_sidebar(agent)
    
    tab1, tab2, tab3 = st.tabs(["💬 Chat Advisor", "🧮 Calculators", "📊 Dashboard"])
    
    with tab1:
        render_chat_tab(agent)
    
    with tab2:
        render_calculator_tab(agent)
    
    with tab3:
        render_dashboard_tab(agent)


if __name__ == "__main__":
    main()