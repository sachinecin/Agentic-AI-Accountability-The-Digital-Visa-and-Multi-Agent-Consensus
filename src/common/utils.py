"""
Common utilities for the Digital Visa Protocol implementation.
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class DIDGenerator:
    """Generator for Decentralized Identifiers (DID) for agents."""
    
    @staticmethod
    def generate(prefix: str = "agent") -> str:
        """Generate a new DID in the format: did:agent:{unique_id}"""
        unique_id = str(uuid.uuid4()).replace('-', '')[:12]
        return f"did:{prefix}:{unique_id}"
    
    @staticmethod
    def validate(did: str) -> bool:
        """Validate DID format."""
        parts = did.split(':')
        return len(parts) == 3 and parts[0] == 'did'


class ReasoningHasher:
    """Utilities for creating and validating reasoning trace hashes."""
    
    @staticmethod
    def compute_hash(reasoning_trace: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of reasoning trace.
        
        Args:
            reasoning_trace: Dictionary containing reasoning chain and intent
            
        Returns:
            Hexadecimal hash string
        """
        # Create deterministic JSON representation
        canonical_json = json.dumps(reasoning_trace, sort_keys=True, separators=(',', ':'))
        
        # Compute SHA-256 hash
        hash_obj = hashlib.sha256(canonical_json.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def validate_hash(expected_hash: str, reasoning_trace: Dict[str, Any]) -> bool:
        """
        Validate that the reasoning trace matches the expected hash.
        
        Args:
            expected_hash: Expected hash value
            reasoning_trace: Reasoning trace to validate
            
        Returns:
            True if hash matches, False otherwise
        """
        computed_hash = ReasoningHasher.compute_hash(reasoning_trace)
        return computed_hash == expected_hash


class AgenticJWTHandler:
    """Handler for Agentic-JWT (A-JWT) token operations."""
    
    def __init__(self, private_key: Optional[bytes] = None, public_key: Optional[bytes] = None):
        """
        Initialize JWT handler.
        
        Args:
            private_key: RSA private key in PEM format (for signing)
            public_key: RSA public key in PEM format (for verification)
        """
        self.private_key = private_key
        self.public_key = public_key
        
        # Generate keys if not provided (for development/testing only)
        if private_key is None:
            self.private_key_obj = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.private_key = self.private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            self.public_key = self.private_key_obj.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
    
    def create_visa_token(
        self,
        agent_id: str,
        intent_hash: str,
        scopes: List[str],
        constraints: Dict[str, Any],
        ttl_seconds: int = 60,
        audience: str = "digital-visa-services"
    ) -> str:
        """
        Create an Agentic-JWT (A-JWT) visa token.
        
        Args:
            agent_id: DID of the agent
            intent_hash: Hash of the reasoning trace
            scopes: List of permission scopes
            constraints: Dictionary of constraints (max_amount, currency, etc.)
            ttl_seconds: Time-to-live in seconds (default: 60)
            audience: Token audience
            
        Returns:
            Signed JWT token string
        """
        now = datetime.utcnow()
        transaction_id = str(uuid.uuid4())
        
        payload = {
            'sub': agent_id,
            'iss': 'digital-visa-idp',
            'aud': audience,
            'exp': now + timedelta(seconds=ttl_seconds),
            'iat': now,
            'nbf': now,
            'jti': transaction_id,
            'intent_hash': intent_hash,
            'scope': scopes,
            'visa_ttl': f'{ttl_seconds}s',
            'constraints': constraints,
            'visa_version': '1.0.0'
        }
        
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm='RS256',
            headers={'kid': 'digital-visa-key-2026-01'}
        )
        
        return token
    
    def verify_visa_token(
        self,
        token: str,
        expected_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify and decode an A-JWT token.
        
        Args:
            token: JWT token string
            expected_audience: Expected audience value (optional)
            
        Returns:
            Decoded token payload
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        options = {
            'verify_signature': True,
            'verify_exp': True,
            'verify_nbf': True,
            'verify_iat': True,
            'verify_aud': expected_audience is not None
        }
        
        decoded = jwt.decode(
            token,
            self.public_key,
            algorithms=['RS256'],
            audience=expected_audience,
            options=options
        )
        
        return decoded
    
    def extract_transaction_id(self, token: str) -> str:
        """Extract transaction ID (jti) from token without full verification."""
        unverified = jwt.decode(token, options={'verify_signature': False})
        return unverified.get('jti', '')


class TransactionTracker:
    """Track used transaction IDs to prevent replay attacks."""
    
    def __init__(self):
        """Initialize transaction tracker with in-memory storage."""
        self._used_transactions = set()
    
    def is_used(self, transaction_id: str) -> bool:
        """Check if transaction ID has been used."""
        return transaction_id in self._used_transactions
    
    def mark_used(self, transaction_id: str) -> None:
        """Mark transaction ID as used."""
        self._used_transactions.add(transaction_id)
    
    def cleanup_expired(self, max_age_seconds: int = 300) -> None:
        """
        Clean up old transaction IDs (would be implemented with timestamps in production).
        
        Args:
            max_age_seconds: Maximum age before cleanup
        """
        # In production, this would use a time-based data structure
        # For now, we keep all transactions in memory
        pass


class MetricsCollector:
    """Collector for Digital Visa Protocol metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            'visa_requests_total': 0,
            'visa_approvals_total': 0,
            'visa_denials_total': 0,
            'consensus_requests_total': 0,
            'consensus_achieved_total': 0,
            'consensus_failed_total': 0,
            'token_verifications_total': 0,
            'token_verification_failures_total': 0,
            'reasoning_trace_saves_total': 0
        }
        self.latencies = {
            'visa_request_latency_ms': [],
            'policy_evaluation_latency_ms': [],
            'token_minting_latency_ms': [],
            'token_verification_latency_ms': []
        }
    
    def increment(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
    
    def record_latency(self, metric_name: str, latency_ms: float) -> None:
        """Record a latency measurement."""
        if metric_name in self.latencies:
            self.latencies[metric_name].append(latency_ms)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        result = dict(self.metrics)
        
        # Calculate latency percentiles
        for latency_name, values in self.latencies.items():
            if values:
                sorted_values = sorted(values)
                n = len(sorted_values)
                result[f'{latency_name}_p50'] = sorted_values[int(n * 0.5)]
                result[f'{latency_name}_p95'] = sorted_values[int(n * 0.95)]
                result[f'{latency_name}_p99'] = sorted_values[int(n * 0.99)]
        
        return result


# Singleton instances for shared use
_metrics_collector = MetricsCollector()
_transaction_tracker = TransactionTracker()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def get_transaction_tracker() -> TransactionTracker:
    """Get the global transaction tracker instance."""
    return _transaction_tracker
