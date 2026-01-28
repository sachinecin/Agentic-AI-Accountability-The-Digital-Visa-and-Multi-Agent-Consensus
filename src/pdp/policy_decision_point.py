"""
Policy Decision Point (PDP) Service

This service evaluates policy decisions using OPA/Rego-compatible logic
and mints Agentic-JWT (A-JWT) tokens for approved requests.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import AgenticJWTHandler, ReasoningHasher, get_metrics_collector
from agent_registry.registry import AgentRegistry


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""
    allow: bool
    reason: str
    requires_approval: bool = False
    requires_consensus: bool = False
    constraints: Dict[str, Any] = None
    policy_version: str = "1.0.0"
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}


class PolicyEngine:
    """
    Policy evaluation engine compatible with OPA/Rego-style rules.
    
    Implements governance-as-code policies for Digital Visa issuance.
    """
    
    def __init__(self):
        """Initialize policy engine."""
        self.policies = []
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default policy rules."""
        self.policies = [
            self._policy_low_value_refund,
            self._policy_high_value_refund,
            self._policy_critical_operations,
            self._policy_reputation_check,
            self._policy_rate_limiting
        ]
    
    def _policy_low_value_refund(self, input_data: Dict[str, Any]) -> Optional[PolicyDecision]:
        """Allow low-value refunds without approval."""
        if input_data.get('action') == 'refund':
            amount = input_data.get('amount', 0)
            agent_reputation = input_data.get('agent_reputation', 0)
            
            if amount <= 100 and agent_reputation >= 0.8:
                return PolicyDecision(
                    allow=True,
                    reason="Low-value refund approved automatically",
                    requires_approval=False,
                    requires_consensus=False,
                    constraints={
                        'max_amount': 100,
                        'currency': input_data.get('currency', 'USD'),
                        'allowed_operations': ['refund']
                    }
                )
        return None
    
    def _policy_high_value_refund(self, input_data: Dict[str, Any]) -> Optional[PolicyDecision]:
        """Require approval for high-value refunds."""
        if input_data.get('action') == 'refund':
            amount = input_data.get('amount', 0)
            supervisor_approved = input_data.get('supervisor_approved', False)
            
            if 100 < amount <= 1000:
                if supervisor_approved:
                    return PolicyDecision(
                        allow=True,
                        reason="High-value refund approved by supervisor",
                        requires_approval=True,
                        requires_consensus=False,
                        constraints={
                            'max_amount': amount,
                            'currency': input_data.get('currency', 'USD'),
                            'approver': input_data.get('approver'),
                            'allowed_operations': ['refund']
                        }
                    )
                else:
                    return PolicyDecision(
                        allow=False,
                        reason="Supervisor approval required for refunds > $100",
                        requires_approval=True,
                        requires_consensus=False
                    )
        return None
    
    def _policy_critical_operations(self, input_data: Dict[str, Any]) -> Optional[PolicyDecision]:
        """Require Byzantine consensus for critical operations."""
        action = input_data.get('action')
        critical_actions = ['wire_transfer', 'account_closure', 'large_payment']
        
        if action in critical_actions:
            consensus_achieved = input_data.get('consensus_achieved', False)
            consensus_ratio = input_data.get('consensus_ratio', 0)
            
            if consensus_achieved and consensus_ratio >= 0.67:
                return PolicyDecision(
                    allow=True,
                    reason=f"Critical operation '{action}' approved via Byzantine consensus",
                    requires_approval=True,
                    requires_consensus=True,
                    constraints={
                        'consensus_required': True,
                        'min_consensus_ratio': 0.67,
                        'allowed_operations': [action]
                    }
                )
            else:
                return PolicyDecision(
                    allow=False,
                    reason=f"Byzantine consensus (2/3) required for '{action}'",
                    requires_approval=True,
                    requires_consensus=True
                )
        return None
    
    def _policy_reputation_check(self, input_data: Dict[str, Any]) -> Optional[PolicyDecision]:
        """Block agents with low reputation."""
        agent_reputation = input_data.get('agent_reputation', 0)
        
        if agent_reputation < 0.5:
            return PolicyDecision(
                allow=False,
                reason=f"Agent reputation too low: {agent_reputation:.2f} < 0.5",
                requires_approval=True,
                requires_consensus=False
            )
        return None
    
    def _policy_rate_limiting(self, input_data: Dict[str, Any]) -> Optional[PolicyDecision]:
        """Check rate limiting constraints."""
        # In production, this would check actual rate limit storage
        # For now, we just add rate limit constraints to approved requests
        return None
    
    def evaluate(self, input_data: Dict[str, Any]) -> PolicyDecision:
        """
        Evaluate all policies against input data.
        
        Args:
            input_data: Policy evaluation input
            
        Returns:
            PolicyDecision with aggregated result
        """
        # Check each policy in order
        for policy in self.policies:
            decision = policy(input_data)
            if decision is not None:
                if decision.allow or not decision.allow:
                    # Return first matching policy (allow or deny)
                    return decision
        
        # Default deny if no policy matched
        return PolicyDecision(
            allow=False,
            reason="No policy matched - default deny",
            requires_approval=True,
            requires_consensus=False
        )


class PolicyDecisionPoint:
    """
    Policy Decision Point (PDP) service.
    
    Evaluates visa requests against policies and mints A-JWT tokens.
    """
    
    def __init__(self, agent_registry: AgentRegistry, jwt_handler: AgenticJWTHandler):
        """
        Initialize PDP service.
        
        Args:
            agent_registry: Agent registry for reputation lookups
            jwt_handler: JWT handler for token minting
        """
        self.agent_registry = agent_registry
        self.jwt_handler = jwt_handler
        self.policy_engine = PolicyEngine()
        self.metrics = get_metrics_collector()
    
    def evaluate_visa_request(
        self,
        agent_id: str,
        task_hash: str,
        scopes: List[str],
        reasoning_trace: Dict[str, Any],
        parent_token: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """
        Evaluate a Digital Visa request.
        
        Args:
            agent_id: Agent's DID
            task_hash: Hash of reasoning trace
            scopes: Requested permission scopes
            reasoning_trace: Agent's reasoning chain
            parent_token: Parent delegation token (optional)
            context: Additional context for policy evaluation
            
        Returns:
            Tuple of (PolicyDecision, visa_token_string or None)
        """
        start_time = datetime.utcnow()
        self.metrics.increment('visa_requests_total')
        
        # Validate reasoning trace hash
        if not ReasoningHasher.validate_hash(task_hash, reasoning_trace):
            decision = PolicyDecision(
                allow=False,
                reason="Reasoning trace hash validation failed"
            )
            self.metrics.increment('visa_denials_total')
            return decision, None
        
        # Get agent information
        agent = self.agent_registry.get_agent(agent_id)
        if not agent:
            decision = PolicyDecision(
                allow=False,
                reason=f"Agent {agent_id} not found in registry"
            )
            self.metrics.increment('visa_denials_total')
            return decision, None
        
        if not agent.is_active:
            decision = PolicyDecision(
                allow=False,
                reason=f"Agent {agent_id} is not active"
            )
            self.metrics.increment('visa_denials_total')
            return decision, None
        
        # Build policy evaluation input
        context = context or {}
        policy_input = {
            'agent_id': agent_id,
            'agent_reputation': agent.reputation_score,
            'action': reasoning_trace.get('intent', '').lower().split()[0] if reasoning_trace.get('intent') else '',
            'scopes': scopes,
            'reasoning_trace': reasoning_trace,
            'task_hash': task_hash,
            **context
        }
        
        # Evaluate policies
        decision = self.policy_engine.evaluate(policy_input)
        
        # Record intent
        if reasoning_trace.get('intent'):
            self.agent_registry.record_intent(agent_id, reasoning_trace['intent'])
        
        # Mint token if approved
        visa_token = None
        if decision.allow:
            visa_token = self.jwt_handler.create_visa_token(
                agent_id=agent_id,
                intent_hash=task_hash,
                scopes=scopes,
                constraints=decision.constraints,
                ttl_seconds=60
            )
            self.metrics.increment('visa_approvals_total')
        else:
            self.metrics.increment('visa_denials_total')
        
        # Record latency
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.metrics.record_latency('policy_evaluation_latency_ms', latency_ms)
        
        return decision, visa_token
    
    def add_custom_policy(self, policy_func) -> None:
        """
        Add a custom policy function.
        
        Args:
            policy_func: Function that takes input_data and returns Optional[PolicyDecision]
        """
        self.policy_engine.policies.insert(0, policy_func)
    
    def get_active_policies(self) -> List[str]:
        """Get list of active policy names."""
        return [p.__name__ for p in self.policy_engine.policies]
