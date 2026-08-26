# EMI & Loan Advisor Agent

An AI agent for Indian loan calculations with plan-act loop, tool calling, and persistent memory.

## Architecture

- **Agent Core** (`agent/core.py`): Plan-act loop that decides which tools to call based on user intent
- **Tools** (`agent/tools.py`): 6 calculation functions (EMI, comparison, eligibility, amortization, prepayment, affordability)
- **Memory** (`agent/memory.py`): File-based JSON persistence per session
- **Frontend** (`app.py`): Streamlit with 3 tabs (Chat, Calculators, Dashboard)

## Two Key Tools

1. **`calculate_emi`** - Computes monthly EMI, total interest, and effective rate given principal, rate, tenure
2. **`check_eligibility`** - Assesses loan eligibility using Indian lending rules (FOI/DTI ratios, income multiples, LTV limits per loan type)

## Memory

ConversationMemory stores each turn (user input, plan, tool calls, results, response) in `data/{session_id}.json`. Survives restarts. Loads user profile (income, expenses, age, credit score) to pre-fill calculations.

## Honest Failure & Fix

**Problem**: The planner initially used keyword matching which failed on "What if I pay 5L extra after 2 years?" - it didn't recognize "pay extra" as prepayment.

**Fix**: Added synonym mapping in `_plan_prepayment()` for "lump sum", "part payment", "extra payment", "pay extra". Also added fallback to reuse last EMI/amortization context when parameters are missing. Now handles "prepay 5L after 24 months" and "what if I pay 5L extra in 2 years" correctly.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Loan Types Supported

Home, Personal, Car, Education, Gold, Property (LAP), Two Wheeler, Consumer Durable - each with RBI-aligned LTV, tenure, rate ranges, and income multipliers.