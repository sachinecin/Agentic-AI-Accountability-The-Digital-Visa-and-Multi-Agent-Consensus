"""
Byzantine Jury Consensus Engine

Implements multi-agent consensus mechanism for critical operations,
preventing single-model hallucinations through majority voting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sys
import os
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import get_metrics_collector


class AgentDecision(Enum):
    """Agent decision on an operation."""
    APPROVE = "approve"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass
class AgentResponse:
    """Response from a single agent in consensus."""
    agent_id: str
    decision: AgentDecision
    reasoning_hash: str
    signature: str
    timestamp: datetime
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusRequest:
    """Request for multi-agent consensus."""
    operation_id: str
    operation_type: str
    operation_details: Dict[str, Any]
    required_consensus: int  # Minimum number of approvals
    total_agents: int        # Total number of agents
    timeout_seconds: int = 30
    agents: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConsensusResult:
    """Result of consensus process."""
    operation_id: str
    consensus_achieved: bool
    agreements: int
    disagreements: int
    abstentions: int
    consensus_ratio: float
    agent_responses: List[AgentResponse]
    executed_at: datetime
    timeout_occurred: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'operation_id': self.operation_id,
            'consensus_achieved': self.consensus_achieved,
            'agreements': self.agreements,
            'disagreements': self.disagreements,
            'abstentions': self.abstentions,
            'consensus_ratio': self.consensus_ratio,
            'agent_responses': [
                {
                    'agent_id': r.agent_id,
                    'decision': r.decision.value,
                    'reasoning_hash': r.reasoning_hash,
                    'signature': r.signature,
                    'timestamp': r.timestamp.isoformat(),
                    'confidence_score': r.confidence_score
                }
                for r in self.agent_responses
            ],
            'executed_at': self.executed_at.isoformat(),
            'timeout_occurred': self.timeout_occurred,
            'error_message': self.error_message
        }


class ByzantineJuryEngine:
    """
    Byzantine Jury Consensus Engine.
    
    Orchestrates multi-agent consensus for critical operations using
    Byzantine fault-tolerant principles.
    """
    
    def __init__(self, default_threshold: float = 0.67):
        """
        Initialize consensus engine.
        
        Args:
            default_threshold: Default consensus threshold (2/3 = 0.67)
        """
        self.default_threshold = default_threshold
        self.pending_requests: Dict[str, ConsensusRequest] = {}
        self.completed_results: Dict[str, ConsensusResult] = {}
        self.agent_responses: Dict[str, List[AgentResponse]] = {}
        self.metrics = get_metrics_collector()
    
    def initiate_consensus(
        self,
        operation_type: str,
        operation_details: Dict[str, Any],
        agent_ids: List[str],
        required_consensus: Optional[int] = None,
        timeout_seconds: int = 30
    ) -> ConsensusRequest:
        """
        Initiate a new consensus request.
        
        Args:
            operation_type: Type of operation requiring consensus
            operation_details: Details of the operation
            agent_ids: List of agent DIDs to participate
            required_consensus: Minimum approvals needed (defaults to 2/3)
            timeout_seconds: Timeout for consensus
            
        Returns:
            ConsensusRequest object
        """
        operation_id = f"op_{uuid.uuid4().hex[:12]}"
        total_agents = len(agent_ids)
        
        if required_consensus is None:
            required_consensus = max(1, int(total_agents * self.default_threshold))
        
        request = ConsensusRequest(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_details=operation_details,
            required_consensus=required_consensus,
            total_agents=total_agents,
            timeout_seconds=timeout_seconds,
            agents=agent_ids
        )
        
        self.pending_requests[operation_id] = request
        self.agent_responses[operation_id] = []
        self.metrics.increment('consensus_requests_total')
        
        return request
    
    def submit_agent_response(
        self,
        operation_id: str,
        agent_id: str,
        decision: AgentDecision,
        reasoning_hash: str,
        signature: str,
        confidence_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Submit an agent's response to a consensus request.
        
        Args:
            operation_id: Consensus operation ID
            agent_id: Agent's DID
            decision: Agent's decision
            reasoning_hash: Hash of agent's reasoning
            signature: Cryptographic signature
            confidence_score: Agent's confidence (0.0 - 1.0)
            metadata: Additional metadata
            
        Returns:
            True if response accepted, False otherwise
        """
        if operation_id not in self.pending_requests:
            return False
        
        request = self.pending_requests[operation_id]
        
        # Check if agent is authorized
        if agent_id not in request.agents:
            return False
        
        # Check if agent already responded
        existing_responses = self.agent_responses.get(operation_id, [])
        if any(r.agent_id == agent_id for r in existing_responses):
            return False
        
        # Create response
        response = AgentResponse(
            agent_id=agent_id,
            decision=decision,
            reasoning_hash=reasoning_hash,
            signature=signature,
            timestamp=datetime.utcnow(),
            confidence_score=confidence_score,
            metadata=metadata or {}
        )
        
        self.agent_responses[operation_id].append(response)
        
        # Check if consensus can be determined
        self._check_consensus(operation_id)
        
        return True
    
    def _check_consensus(self, operation_id: str) -> None:
        """
        Check if consensus has been reached for an operation.
        
        Args:
            operation_id: Operation ID to check
        """
        if operation_id not in self.pending_requests:
            return
        
        request = self.pending_requests[operation_id]
        responses = self.agent_responses.get(operation_id, [])
        
        # Check timeout
        elapsed = datetime.utcnow() - request.created_at
        if elapsed > timedelta(seconds=request.timeout_seconds):
            self._finalize_consensus(operation_id, timeout=True)
            return
        
        # Count decisions
        approvals = sum(1 for r in responses if r.decision == AgentDecision.APPROVE)
        denials = sum(1 for r in responses if r.decision == AgentDecision.DENY)
        
        # Check if consensus achieved
        if approvals >= request.required_consensus:
            self._finalize_consensus(operation_id, timeout=False)
        
        # Check if consensus impossible (too many denials)
        remaining = request.total_agents - len(responses)
        if approvals + remaining < request.required_consensus:
            self._finalize_consensus(operation_id, timeout=False)
    
    def _finalize_consensus(self, operation_id: str, timeout: bool) -> None:
        """
        Finalize consensus decision.
        
        Args:
            operation_id: Operation ID
            timeout: Whether consensus timed out
        """
        if operation_id not in self.pending_requests:
            return
        
        request = self.pending_requests[operation_id]
        responses = self.agent_responses.get(operation_id, [])
        
        # Count decisions
        approvals = sum(1 for r in responses if r.decision == AgentDecision.APPROVE)
        denials = sum(1 for r in responses if r.decision == AgentDecision.DENY)
        abstentions = sum(1 for r in responses if r.decision == AgentDecision.ABSTAIN)
        
        # Calculate consensus ratio
        total_responses = len(responses)
        consensus_ratio = approvals / request.total_agents if request.total_agents > 0 else 0
        
        # Determine if consensus achieved
        consensus_achieved = approvals >= request.required_consensus and not timeout
        
        # Create result
        result = ConsensusResult(
            operation_id=operation_id,
            consensus_achieved=consensus_achieved,
            agreements=approvals,
            disagreements=denials,
            abstentions=abstentions,
            consensus_ratio=consensus_ratio,
            agent_responses=responses,
            executed_at=datetime.utcnow(),
            timeout_occurred=timeout
        )
        
        if timeout:
            result.error_message = f"Consensus timeout after {request.timeout_seconds}s"
        elif not consensus_achieved:
            result.error_message = f"Insufficient consensus: {approvals}/{request.required_consensus}"
        
        # Store result
        self.completed_results[operation_id] = result
        
        # Clean up
        del self.pending_requests[operation_id]
        
        # Update metrics
        if consensus_achieved:
            self.metrics.increment('consensus_achieved_total')
        else:
            self.metrics.increment('consensus_failed_total')
    
    def get_consensus_result(self, operation_id: str) -> Optional[ConsensusResult]:
        """
        Get consensus result for an operation.
        
        Args:
            operation_id: Operation ID
            
        Returns:
            ConsensusResult if available, None otherwise
        """
        return self.completed_results.get(operation_id)
    
    def get_pending_consensus(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of pending consensus.
        
        Args:
            operation_id: Operation ID
            
        Returns:
            Status dictionary or None
        """
        if operation_id not in self.pending_requests:
            return None
        
        request = self.pending_requests[operation_id]
        responses = self.agent_responses.get(operation_id, [])
        
        approvals = sum(1 for r in responses if r.decision == AgentDecision.APPROVE)
        denials = sum(1 for r in responses if r.decision == AgentDecision.DENY)
        
        return {
            'operation_id': operation_id,
            'operation_type': request.operation_type,
            'required_consensus': request.required_consensus,
            'total_agents': request.total_agents,
            'responses_received': len(responses),
            'approvals': approvals,
            'denials': denials,
            'pending_agents': [a for a in request.agents if not any(r.agent_id == a for r in responses)]
        }
    
    def validate_reasoning_diversity(
        self,
        operation_id: str,
        min_diversity_threshold: float = 0.3
    ) -> Tuple[bool, float]:
        """
        Validate that agent reasonings are diverse (prevent collusion).
        
        Args:
            operation_id: Operation ID
            min_diversity_threshold: Minimum required diversity
            
        Returns:
            Tuple of (is_diverse, diversity_score)
        """
        responses = self.agent_responses.get(operation_id, [])
        
        if len(responses) < 2:
            return True, 1.0
        
        # Get all reasoning hashes
        hashes = [r.reasoning_hash for r in responses]
        unique_hashes = set(hashes)
        
        # Calculate diversity score (percentage of unique reasoning)
        diversity_score = len(unique_hashes) / len(hashes)
        
        is_diverse = diversity_score >= min_diversity_threshold
        
        return is_diverse, diversity_score
    
    def cleanup_old_results(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old completed results.
        
        Args:
            max_age_seconds: Maximum age to keep results
            
        Returns:
            Number of results cleaned up
        """
        now = datetime.utcnow()
        old_ids = []
        
        for op_id, result in self.completed_results.items():
            age = (now - result.executed_at).total_seconds()
            if age > max_age_seconds:
                old_ids.append(op_id)
        
        for op_id in old_ids:
            del self.completed_results[op_id]
            if op_id in self.agent_responses:
                del self.agent_responses[op_id]
        
        return len(old_ids)
