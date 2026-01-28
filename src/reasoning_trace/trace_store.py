"""
Reasoning Trace Service

Implements immutable reasoning trace logging with vector embeddings
for forensic analysis and compliance auditing.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json
import sys
import os
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import get_metrics_collector


@dataclass
class ReasoningStep:
    """A single step in the agent's reasoning chain."""
    step: int
    timestamp: datetime
    thought: str
    action: str
    observation: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class ExecutionResult:
    """Result of agent execution."""
    status: str  # "success", "failure", "partial"
    output: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Performance metrics for the reasoning trace."""
    total_latency_ms: float
    token_count: int
    api_calls: int
    memory_usage_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ModelMetadata:
    """Metadata about the AI model."""
    model: str
    temperature: float
    version: str
    provider: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for an agent operation."""
    trace_id: str
    agent_id: str
    operation_id: str
    timestamp: datetime
    reasoning_chain: List[ReasoningStep]
    final_intent: str
    intent_hash: str
    visa_issued: Optional[str] = None
    visa_constraints: Dict[str, Any] = field(default_factory=dict)
    execution_result: Optional[ExecutionResult] = None
    performance_metrics: Optional[PerformanceMetrics] = None
    vector_embedding: Optional[List[float]] = None
    attention_weights: Dict[str, Any] = field(default_factory=dict)
    model_metadata: Optional[ModelMetadata] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trace_id': self.trace_id,
            'agent_id': self.agent_id,
            'operation_id': self.operation_id,
            'timestamp': self.timestamp.isoformat(),
            'reasoning_chain': [step.to_dict() for step in self.reasoning_chain],
            'final_intent': self.final_intent,
            'intent_hash': self.intent_hash,
            'visa_issued': self.visa_issued,
            'visa_constraints': self.visa_constraints,
            'execution_result': self.execution_result.to_dict() if self.execution_result else None,
            'performance_metrics': self.performance_metrics.to_dict() if self.performance_metrics else None,
            'vector_embedding': self.vector_embedding,
            'attention_weights': self.attention_weights,
            'model_metadata': self.model_metadata.to_dict() if self.model_metadata else None,
            'tags': self.tags
        }


class ReasoningTraceStore:
    """
    Storage and retrieval system for reasoning traces.
    
    Provides immutable logging with optional vector embeddings for
    semantic search and forensic analysis.
    """
    
    def __init__(self, enable_vector_storage: bool = False):
        """
        Initialize reasoning trace store.
        
        Args:
            enable_vector_storage: Whether to enable vector embeddings
        """
        self.traces: Dict[str, ReasoningTrace] = {}
        self.agent_traces: Dict[str, List[str]] = {}  # agent_id -> trace_ids
        self.operation_traces: Dict[str, str] = {}  # operation_id -> trace_id
        self.enable_vector_storage = enable_vector_storage
        self.metrics = get_metrics_collector()
    
    def create_trace(
        self,
        agent_id: str,
        operation_id: str,
        reasoning_chain: List[Dict[str, Any]],
        final_intent: str,
        intent_hash: str,
        visa_issued: Optional[str] = None,
        visa_constraints: Optional[Dict[str, Any]] = None,
        model_metadata: Optional[Dict[str, Any]] = None
    ) -> ReasoningTrace:
        """
        Create a new reasoning trace.
        
        Args:
            agent_id: Agent's DID
            operation_id: Operation identifier
            reasoning_chain: List of reasoning steps
            final_intent: Final determined intent
            intent_hash: Hash of the reasoning
            visa_issued: Visa token ID if issued
            visa_constraints: Constraints from the visa
            model_metadata: Model information
            
        Returns:
            Created ReasoningTrace
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        
        # Convert reasoning chain to ReasoningStep objects
        steps = []
        for i, step_data in enumerate(reasoning_chain):
            step = ReasoningStep(
                step=i + 1,
                timestamp=datetime.fromisoformat(step_data.get('timestamp', datetime.utcnow().isoformat())),
                thought=step_data.get('thought', ''),
                action=step_data.get('action', ''),
                observation=step_data.get('observation', ''),
                tool_calls=step_data.get('tool_calls', []),
                latency_ms=step_data.get('latency_ms', 0.0)
            )
            steps.append(step)
        
        # Create model metadata if provided
        model_meta = None
        if model_metadata:
            model_meta = ModelMetadata(
                model=model_metadata.get('model', 'unknown'),
                temperature=model_metadata.get('temperature', 0.7),
                version=model_metadata.get('version', '1.0'),
                provider=model_metadata.get('provider', 'unknown')
            )
        
        # Create trace
        trace = ReasoningTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            operation_id=operation_id,
            timestamp=datetime.utcnow(),
            reasoning_chain=steps,
            final_intent=final_intent,
            intent_hash=intent_hash,
            visa_issued=visa_issued,
            visa_constraints=visa_constraints or {},
            model_metadata=model_meta
        )
        
        # Store trace
        self.traces[trace_id] = trace
        
        # Index by agent
        if agent_id not in self.agent_traces:
            self.agent_traces[agent_id] = []
        self.agent_traces[agent_id].append(trace_id)
        
        # Index by operation
        self.operation_traces[operation_id] = trace_id
        
        self.metrics.increment('reasoning_trace_saves_total')
        
        return trace
    
    def update_trace_execution(
        self,
        trace_id: str,
        status: str,
        output: Dict[str, Any],
        errors: Optional[List[str]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update trace with execution results.
        
        Args:
            trace_id: Trace identifier
            status: Execution status
            output: Execution output
            errors: List of errors if any
            performance_metrics: Performance data
            
        Returns:
            True if updated, False if trace not found
        """
        trace = self.traces.get(trace_id)
        if not trace:
            return False
        
        # Update execution result
        trace.execution_result = ExecutionResult(
            status=status,
            output=output,
            errors=errors or []
        )
        
        # Update performance metrics
        if performance_metrics:
            trace.performance_metrics = PerformanceMetrics(
                total_latency_ms=performance_metrics.get('total_latency_ms', 0),
                token_count=performance_metrics.get('token_count', 0),
                api_calls=performance_metrics.get('api_calls', 0),
                memory_usage_mb=performance_metrics.get('memory_usage_mb', 0)
            )
        
        return True
    
    def get_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """
        Retrieve a reasoning trace by ID.
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            ReasoningTrace if found, None otherwise
        """
        return self.traces.get(trace_id)
    
    def get_trace_by_operation(self, operation_id: str) -> Optional[ReasoningTrace]:
        """
        Retrieve reasoning trace by operation ID.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            ReasoningTrace if found, None otherwise
        """
        trace_id = self.operation_traces.get(operation_id)
        if trace_id:
            return self.traces.get(trace_id)
        return None
    
    def get_agent_traces(
        self,
        agent_id: str,
        limit: int = 100,
        status_filter: Optional[str] = None
    ) -> List[ReasoningTrace]:
        """
        Get reasoning traces for an agent.
        
        Args:
            agent_id: Agent's DID
            limit: Maximum number of traces to return
            status_filter: Filter by execution status
            
        Returns:
            List of reasoning traces
        """
        trace_ids = self.agent_traces.get(agent_id, [])
        traces = [self.traces[tid] for tid in trace_ids[-limit:] if tid in self.traces]
        
        if status_filter:
            traces = [
                t for t in traces
                if t.execution_result and t.execution_result.status == status_filter
            ]
        
        return traces
    
    def search_traces(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[ReasoningTrace]:
        """
        Search reasoning traces with filters.
        
        Args:
            query: Text search in intent/thoughts
            agent_id: Filter by agent
            start_time: Start of time range
            end_time: End of time range
            status: Filter by execution status
            tags: Filter by tags
            limit: Maximum results
            
        Returns:
            List of matching reasoning traces
        """
        results = list(self.traces.values())
        
        # Apply filters
        if agent_id:
            results = [t for t in results if t.agent_id == agent_id]
        
        if start_time:
            results = [t for t in results if t.timestamp >= start_time]
        
        if end_time:
            results = [t for t in results if t.timestamp <= end_time]
        
        if status:
            results = [
                t for t in results
                if t.execution_result and t.execution_result.status == status
            ]
        
        if tags:
            results = [t for t in results if any(tag in t.tags for tag in tags)]
        
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.final_intent.lower() or
                   any(query_lower in step.thought.lower() for step in t.reasoning_chain)
            ]
        
        # Sort by timestamp descending
        results.sort(key=lambda t: t.timestamp, reverse=True)
        
        return results[:limit]
    
    def export_trace(self, trace_id: str, format: str = 'json') -> Optional[str]:
        """
        Export a trace in specified format.
        
        Args:
            trace_id: Trace identifier
            format: Export format ('json', 'text')
            
        Returns:
            Formatted trace string or None
        """
        trace = self.traces.get(trace_id)
        if not trace:
            return None
        
        if format == 'json':
            return json.dumps(trace.to_dict(), indent=2)
        
        elif format == 'text':
            lines = [
                f"Reasoning Trace: {trace.trace_id}",
                f"Agent: {trace.agent_id}",
                f"Operation: {trace.operation_id}",
                f"Timestamp: {trace.timestamp.isoformat()}",
                f"Final Intent: {trace.final_intent}",
                f"\nReasoning Chain:",
            ]
            
            for step in trace.reasoning_chain:
                lines.extend([
                    f"\n  Step {step.step}:",
                    f"    Thought: {step.thought}",
                    f"    Action: {step.action}",
                    f"    Observation: {step.observation}"
                ])
            
            if trace.execution_result:
                lines.extend([
                    f"\nExecution Result:",
                    f"  Status: {trace.execution_result.status}",
                    f"  Output: {json.dumps(trace.execution_result.output, indent=4)}"
                ])
            
            return '\n'.join(lines)
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get trace storage statistics.
        
        Returns:
            Statistics dictionary
        """
        total_traces = len(self.traces)
        
        success_count = sum(
            1 for t in self.traces.values()
            if t.execution_result and t.execution_result.status == "success"
        )
        
        failure_count = sum(
            1 for t in self.traces.values()
            if t.execution_result and t.execution_result.status == "failure"
        )
        
        return {
            'total_traces': total_traces,
            'successful_executions': success_count,
            'failed_executions': failure_count,
            'unique_agents': len(self.agent_traces),
            'avg_reasoning_steps': sum(len(t.reasoning_chain) for t in self.traces.values()) / max(total_traces, 1)
        }
