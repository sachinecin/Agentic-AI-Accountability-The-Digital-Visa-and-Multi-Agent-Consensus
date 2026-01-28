"""
Agent Registry Service - DID-based lifecycle and intent catalog management.

This service manages the registration, lifecycle, and reputation tracking of
AI agents within the Digital Visa Protocol framework.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
from enum import Enum


class RiskProfile(Enum):
    """Risk profile classification for agents."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentMetadata:
    """Metadata associated with an agent."""
    organization: str
    department: str
    supervisor: str
    environment: str = "production"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class AgentRegistration:
    """Complete agent registration information."""
    did: str
    public_key: str
    model: str
    version: str
    created_at: datetime
    reputation_score: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    consensus_participation: int
    last_active: datetime
    capabilities: List[str]
    risk_profile: RiskProfile
    metadata: AgentMetadata
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['last_active'] = self.last_active.isoformat()
        result['risk_profile'] = self.risk_profile.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentRegistration':
        """Create from dictionary representation."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_active'] = datetime.fromisoformat(data['last_active'])
        data['risk_profile'] = RiskProfile(data['risk_profile'])
        data['metadata'] = AgentMetadata(**data['metadata'])
        return cls(**data)


class AgentRegistry:
    """
    Agent Registry Service for managing agent lifecycle and reputation.
    
    Implements DID-based identity management with reputation tracking
    and capability cataloging.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, AgentRegistration] = {}
        self._intent_catalog: Dict[str, List[str]] = {}  # DID -> list of intents
    
    def register_agent(
        self,
        did: str,
        public_key: str,
        model: str,
        version: str,
        capabilities: List[str],
        metadata: AgentMetadata,
        initial_risk_profile: RiskProfile = RiskProfile.MEDIUM
    ) -> AgentRegistration:
        """
        Register a new agent in the registry.
        
        Args:
            did: Decentralized identifier for the agent
            public_key: Public key in PEM format
            model: AI model type (e.g., "gpt-4", "gemini")
            version: Model version
            capabilities: List of capability domains
            metadata: Agent metadata
            initial_risk_profile: Initial risk classification
            
        Returns:
            AgentRegistration object
            
        Raises:
            ValueError: If agent already registered
        """
        if did in self._agents:
            raise ValueError(f"Agent {did} is already registered")
        
        now = datetime.utcnow()
        registration = AgentRegistration(
            did=did,
            public_key=public_key,
            model=model,
            version=version,
            created_at=now,
            reputation_score=0.5,  # Start with neutral reputation
            total_operations=0,
            successful_operations=0,
            failed_operations=0,
            consensus_participation=0,
            last_active=now,
            capabilities=capabilities,
            risk_profile=initial_risk_profile,
            metadata=metadata,
            is_active=True
        )
        
        self._agents[did] = registration
        self._intent_catalog[did] = []
        
        return registration
    
    def get_agent(self, did: str) -> Optional[AgentRegistration]:
        """
        Retrieve agent registration by DID.
        
        Args:
            did: Agent's decentralized identifier
            
        Returns:
            AgentRegistration if found, None otherwise
        """
        return self._agents.get(did)
    
    def update_reputation(
        self,
        did: str,
        operation_successful: bool,
        consensus_participated: bool = False
    ) -> float:
        """
        Update agent reputation based on operation outcome.
        
        Args:
            did: Agent's decentralized identifier
            operation_successful: Whether the operation succeeded
            consensus_participated: Whether agent participated in consensus
            
        Returns:
            Updated reputation score
            
        Raises:
            ValueError: If agent not found
        """
        agent = self._agents.get(did)
        if not agent:
            raise ValueError(f"Agent {did} not found")
        
        # Update operation counters
        agent.total_operations += 1
        if operation_successful:
            agent.successful_operations += 1
        else:
            agent.failed_operations += 1
        
        if consensus_participated:
            agent.consensus_participation += 1
        
        # Calculate new reputation score (weighted average)
        # Success rate: 70%, Consensus participation: 30%
        success_rate = agent.successful_operations / agent.total_operations
        consensus_factor = min(agent.consensus_participation / max(agent.total_operations, 1), 1.0)
        
        agent.reputation_score = (0.7 * success_rate) + (0.3 * consensus_factor)
        agent.last_active = datetime.utcnow()
        
        # Adjust risk profile based on reputation
        if agent.reputation_score >= 0.9:
            agent.risk_profile = RiskProfile.LOW
        elif agent.reputation_score >= 0.7:
            agent.risk_profile = RiskProfile.MEDIUM
        elif agent.reputation_score >= 0.5:
            agent.risk_profile = RiskProfile.HIGH
        else:
            agent.risk_profile = RiskProfile.CRITICAL
        
        return agent.reputation_score
    
    def deactivate_agent(self, did: str) -> bool:
        """
        Deactivate an agent (soft delete).
        
        Args:
            did: Agent's decentralized identifier
            
        Returns:
            True if deactivated, False if not found
        """
        agent = self._agents.get(did)
        if agent:
            agent.is_active = False
            return True
        return False
    
    def list_agents(
        self,
        active_only: bool = True,
        capability: Optional[str] = None,
        min_reputation: float = 0.0
    ) -> List[AgentRegistration]:
        """
        List agents with optional filtering.
        
        Args:
            active_only: Only return active agents
            capability: Filter by capability
            min_reputation: Minimum reputation score
            
        Returns:
            List of matching agent registrations
        """
        agents = list(self._agents.values())
        
        if active_only:
            agents = [a for a in agents if a.is_active]
        
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        
        if min_reputation > 0.0:
            agents = [a for a in agents if a.reputation_score >= min_reputation]
        
        return agents
    
    def record_intent(self, did: str, intent: str) -> None:
        """
        Record an intent in the agent's intent catalog.
        
        Args:
            did: Agent's decentralized identifier
            intent: Intent description
        """
        if did in self._intent_catalog:
            self._intent_catalog[did].append(intent)
    
    def get_intent_history(self, did: str, limit: int = 100) -> List[str]:
        """
        Get recent intent history for an agent.
        
        Args:
            did: Agent's decentralized identifier
            limit: Maximum number of intents to return
            
        Returns:
            List of recent intents
        """
        intents = self._intent_catalog.get(did, [])
        return intents[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary of statistics
        """
        active_agents = [a for a in self._agents.values() if a.is_active]
        
        return {
            'total_agents': len(self._agents),
            'active_agents': len(active_agents),
            'inactive_agents': len(self._agents) - len(active_agents),
            'average_reputation': sum(a.reputation_score for a in active_agents) / len(active_agents) if active_agents else 0,
            'total_operations': sum(a.total_operations for a in active_agents),
            'risk_profile_distribution': {
                'low': len([a for a in active_agents if a.risk_profile == RiskProfile.LOW]),
                'medium': len([a for a in active_agents if a.risk_profile == RiskProfile.MEDIUM]),
                'high': len([a for a in active_agents if a.risk_profile == RiskProfile.HIGH]),
                'critical': len([a for a in active_agents if a.risk_profile == RiskProfile.CRITICAL])
            }
        }
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save registry to JSON file.
        
        Args:
            filepath: Path to save file
        """
        data = {
            'agents': {did: agent.to_dict() for did, agent in self._agents.items()},
            'intent_catalog': self._intent_catalog
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load registry from JSON file.
        
        Args:
            filepath: Path to load file
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self._agents = {
            did: AgentRegistration.from_dict(agent_data)
            for did, agent_data in data['agents'].items()
        }
        self._intent_catalog = data['intent_catalog']
