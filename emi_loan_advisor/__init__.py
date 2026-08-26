from .agent import (
    LoanAdvisorAgent,
    create_agent,
    tool_registry,
    memory_manager,
    LoanType,
    EmploymentType,
    LoanOption,
    EMIResult,
    EligibilityResult,
    ComparisonResult,
    PrepaymentResult,
    AffordabilityResult,
)

__version__ = "1.0.0"
__all__ = [
    "LoanAdvisorAgent",
    "create_agent",
    "tool_registry",
    "memory_manager",
    "LoanType",
    "EmploymentType",
    "LoanOption",
    "EMIResult",
    "EligibilityResult",
    "ComparisonResult",
    "PrepaymentResult",
    "AffordabilityResult",
]