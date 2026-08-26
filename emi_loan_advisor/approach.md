# EMI & Loan Advisor Agent - Technical Approach

## Overview

A single-user AI agent for Indian loan calculations with a plan-act loop, tool calling, and persistent file-based memory. Built with Python, Streamlit, and Pydantic.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                        │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │ Chat Tab     │  │ Calculator Tab │  │ Dashboard Tab      │  │
│  │ (Conversation)│  │ (5 Forms)      │  │ (Plotly Charts)    │  │
│  └──────┬───────┘  └───────┬────────┘  └─────────┬──────────┘  │
│         │                  │                      │             │
│         └──────────────────┼──────────────────────┘             │
│                            ▼                                    │
│              ┌─────────────────────────┐                        │
│              │      Agent Core          │                        │
│              │  (Plan-Act Loop)         │                        │
│              └───────────┬─────────────┘                        │
│                          │                                       │
│        ┌─────────────────┼─────────────────┐                    │
│        ▼                 ▼                 ▼                    │
│  ┌───────────┐    ┌──────────────┐  ┌────────────┐             │
│  │ Tools     │    │ Memory       │  │ Models     │             │
│  │ (6 fns)   │    │ (JSON file)  │  │ (Pydantic) │             │
│  └───────────┘    └──────────────┘  └────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Agent Core (`agent/core.py`)

**Plan-Act Loop Pattern:**
```python
def run(self, user_input: str) -> str:
    plan = self._plan(user_input)           # PLAN: Decide tools
    for step in plan.steps:
        result = self.tools.execute(...)    # ACT: Run tools
    response = self._respond(...)           # OBSERVE: Format output
    self.context.add_turn(...)              # REMEMBER: Save to memory
```

**Intent Router (`_plan`):**
- Keyword-based classification (EMI, eligibility, comparison, prepayment, amortization, affordability, profile)
- Extracts numbers with Indian notation (L=lakhs, Cr=crores, K=thousands)
- Falls back to conversation context when parameters missing

### 2. Tools (`agent/tools.py`)

Six pure Python functions, no external dependencies:

| Tool | Purpose | Key Formula |
|------|---------|-------------|
| `calculate_emi` | Monthly payment | P × r × (1+r)ⁿ / ((1+r)ⁿ - 1) |
| `compare_loans` | Side-by-side | Runs EMI calc for each option |
| `check_eligibility` | Loan qualification | FOI/DTI ratios + income multiples + LTV |
| `generate_amortization` | Full schedule | Iterative principal/interest split |
| `calculate_prepayment_impact` | Early payment effect | Recalculate from prepayment month |
| `calculate_affordability` | Max borrowable | Reverse EMI formula at safe FOI |

### 3. Memory (`agent/memory.py`)

**File-based persistence:**
- One JSON file per session: `data/{session_id}.json`
- Stores: user profile, conversation turns, tool results
- Loads on agent creation, saves after each turn
- Survives process restarts

**ConversationTurn schema:**
```python
{
    "timestamp": "2026-08-26T10:30:00",
    "user_input": "Calculate EMI for 50L...",
    "plan": "User wants EMI calculation for home loan",
    "tool_calls": [{"tool": "calculate_emi", "args": {...}, "reason": "..."}],
    "tool_results": [{"tool_name": "calculate_emi", "success": true, "data": {...}}],
    "response": "**EMI Calculation Result**\n- Monthly EMI: ₹44,986..."
}
```

### 4. Models (`agent/models.py`)

Pydantic models for type safety:
- **8 Indian loan types**: Home, Personal, Car, Education, Gold, Property (LAP), Two Wheeler, Consumer Durable
- **Loan rules per type**: LTV limits, tenure caps, income multipliers, rate ranges, fee structures
- **Structured outputs**: EMIResult, EligibilityResult, ComparisonResult, PrepaymentResult, AmortizationSchedule

### 5. Export (`agent/export.py`)

- **PDF**: fpdf2 with custom formatting (tables, sections, gauges)
- **Excel**: openpyxl with multiple sheets (summary + detailed schedules)
- Both generated from memory's calculation history

---

## Indian Loan Rules Implementation

Each loan type has RBI-aligned parameters:

```python
INDIAN_LOAN_RULES = {
    LoanType.HOME: {
        "max_ltv": 0.90,
        "max_tenure_years": 30,
        "max_income_multiple": 7,
        "typical_rate_range": (8.0, 11.0),
        "min_credit_score": 650,
    },
    LoanType.PERSONAL: {
        "max_ltv": 1.0,
        "max_tenure_years": 7,
        "max_income_multiple": 25,
        "typical_rate_range": (10.0, 24.0),
        "min_credit_score": 700,
    },
    # ... 6 more types
}
```

Eligibility uses:
- **FOI (Fixed Obligation to Income)**: ≤55% for salaried, ≤50% self-employed
- **DTI (Debt to Income)**: Expenses + EMIs / Income
- **Income multiplier**: Max loan = Monthly Income × 12 × multiplier
- **Age cap**: Max tenure = 70 - current_age

---

## Frontend (Streamlit)

Three tabs sharing single agent instance:

1. **Chat Advisor** - Natural language, streaming responses, expandable tool traces
2. **Calculators** - 5 structured forms (EMI, Eligibility, Comparison, Prepayment, Affordability)
3. **Dashboard** - Plotly charts (amortization waterfall, balance decay, comparison bars, affordability gauge, scenario analysis)

---

## Number Parsing

Handles Indian notation:
- "50 lakhs" → 5,000,000
- "1.5 cr" → 15,000,000  
- "50K" → 50,000
- "50L at 9%" → extracts [5000000, 9.0]

Regex removes matched units before parsing remaining numbers to avoid duplicates.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pure Python tools | No LLM dependency for calculations; deterministic, testable |
| Keyword router | Simple, fast, no API costs; sufficient for domain-specific intents |
| JSON file memory | Zero infrastructure; portable; survives restarts |
| Pydantic models | Runtime validation; self-documenting; IDE support |
| Streamlit | Python-native; no separate frontend build; great for data apps |
| Plotly | Interactive charts; works in Streamlit without config |
| fpdf2 + openpyxl | Mature libraries; PDF for reading, Excel for analysis |

---

## Failure Handling

**Problem**: Initial keyword planner failed on "What if I pay 5L extra after 2 years?" — didn't recognize "pay extra" as prepayment.

**Fix**: 
- Added synonym mapping in `_plan_prepayment()`: "lump sum", "part payment", "extra payment", "pay extra"
- Added context fallback: reuses last EMI/amortization loan params when user omits them
- Now handles both "prepay 5L after 24 months" and "what if I pay 5L extra in 2 years"

---

## Running the Project

```bash
cd emi_loan_advisor
pip install -r requirements.txt
streamlit run app.py
```

**Demo notebook** (`demo.ipynb`) shows multi-step traces with plan/tool/result logging for 5 example goals.

---

## Extensibility Points

- Add new loan types in `models.py` → `INDIAN_LOAN_RULES`
- Add new tools in `tools.py` → register in `ToolRegistry`
- Add new UI tabs in `ui/` → wire in `app.py`
- Swap keyword router for LLM planner in `core.py` → `_plan()`