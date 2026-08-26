import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import (
    ConversationMemory, ConversationTurn, UserProfile,
    LoanType, EmploymentType
)


class MemoryManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent / "data"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]
        path = self._get_session_path(session_id)
        if not path.exists():
            memory = ConversationMemory(session_id=session_id)
            self._save(memory)
        return session_id
    
    def load(self, session_id: str) -> ConversationMemory:
        path = self._get_session_path(session_id)
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
            return ConversationMemory(**data)
        return ConversationMemory(session_id=session_id)
    
    def save(self, memory: ConversationMemory) -> None:
        memory.updated_at = datetime.now()
        self._save(memory)
    
    def _save(self, memory: ConversationMemory) -> None:
        path = self._get_session_path(memory.session_id)
        with open(path, 'w') as f:
            json.dump(memory.model_dump(mode='json'), f, indent=2, default=str)
    
    def delete_session(self, session_id: str) -> bool:
        path = self._get_session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        sessions = []
        for path in self.storage_dir.glob("*.json"):
            sessions.append(path.stem)
        return sorted(sessions)


class ConversationContext:
    def __init__(self, memory: ConversationMemory):
        self.memory = memory
    
    def add_turn(
        self,
        user_input: str,
        plan: Optional[str],
        tool_calls: List[Dict],
        tool_results: List[Dict],
        response: str,
        metadata: Optional[Dict] = None
    ) -> None:
        turn = ConversationTurn(
            user_input=user_input,
            plan=plan,
            tool_calls=tool_calls,
            tool_results=tool_results,
            response=response,
            metadata=metadata or {}
        )
        self.memory.turns.append(turn)
        self.memory.updated_at = datetime.now()
    
    def get_recent_turns(self, n: int = 10) -> List[ConversationTurn]:
        return self.memory.turns[-n:]
    
    def get_context_string(self, max_turns: int = 8) -> str:
        turns = self.get_recent_turns(max_turns)
        if not turns:
            return "No previous conversation."
        
        context_parts = ["Previous conversation:"]
        for turn in turns:
            context_parts.append(f"User: {turn.user_input}")
            if turn.tool_calls:
                tools_str = ", ".join([tc.get('tool', 'unknown') for tc in turn.tool_calls])
                context_parts.append(f"  [Tools used: {tools_str}]")
            context_parts.append(f"Assistant: {turn.response[:200]}...")
        return "\n".join(context_parts)
    
    def get_user_profile_summary(self) -> str:
        profile = self.memory.user_profile
        if not profile:
            return "No user profile set."
        
        parts = []
        if profile.monthly_income:
            parts.append(f"Income: ₹{profile.monthly_income:,.0f}/month")
        if profile.monthly_expenses:
            parts.append(f"Expenses: ₹{profile.monthly_expenses:,.0f}/month")
        if profile.existing_emis:
            parts.append(f"Existing EMIs: ₹{profile.existing_emis:,.0f}/month")
        if profile.age:
            parts.append(f"Age: {profile.age}")
        if profile.employment_type:
            parts.append(f"Employment: {profile.employment_type.value}")
        if profile.credit_score:
            parts.append(f"Credit Score: {profile.credit_score}")
        return "; ".join(parts) if parts else "Incomplete profile"
    
    def update_profile(self, **kwargs) -> None:
        if self.memory.user_profile is None:
            self.memory.user_profile = UserProfile(session_id=self.memory.session_id)
        
        for key, value in kwargs.items():
            if hasattr(self.memory.user_profile, key) and value is not None:
                setattr(self.memory.user_profile, key, value)
        self.memory.user_profile.updated_at = datetime.now()
    
    def get_last_tool_result(self, tool_name: str) -> Optional[Dict]:
        for turn in reversed(self.memory.turns):
            for result in turn.tool_results:
                if result.get('tool_name') == tool_name and result.get('success'):
                    return result.get('data')
        return None
    
    def get_all_calculations(self) -> List[Dict]:
        calculations = []
        for turn in self.memory.turns:
            for result in turn.tool_results:
                if result.get('success') and result.get('data'):
                    calculations.append({
                        'tool': result.get('tool_name'),
                        'data': result.get('data'),
                        'timestamp': turn.timestamp.isoformat()
                    })
        return calculations


memory_manager = MemoryManager()