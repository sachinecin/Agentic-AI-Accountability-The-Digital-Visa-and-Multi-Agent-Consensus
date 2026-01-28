"""
Policy Enforcement Point (PEP) Service

This service verifies Digital Visa tokens and enforces policy constraints
at the service mesh layer.
"""

from datetime import datetime
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
import sys
import os
import jwt as pyjwt

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import AgenticJWTHandler, get_transaction_tracker, get_metrics_collector


@dataclass
class VerificationResult:
    """Result of A-JWT token verification."""
    valid: bool
    agent_id: Optional[str] = None
    transaction_id: Optional[str] = None
    constraints_met: bool = False
    reasoning_hash_valid: bool = False
    not_expired: bool = False
    not_replayed: bool = False
    audience_match: bool = False
    error_message: Optional[str] = None
    trace_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'valid': self.valid,
            'agent_id': self.agent_id,
            'transaction_id': self.transaction_id,
            'constraints_met': self.constraints_met,
            'reasoning_hash_valid': self.reasoning_hash_valid,
            'not_expired': self.not_expired,
            'not_replayed': self.not_replayed,
            'audience_match': self.audience_match,
            'error_message': self.error_message,
            'trace_id': self.trace_id
        }


class PolicyEnforcementPoint:
    """
    Policy Enforcement Point (PEP) service.
    
    Verifies A-JWT tokens and validates policy constraints at runtime.
    """
    
    def __init__(self, jwt_handler: AgenticJWTHandler, service_name: str = "digital-visa-services"):
        """
        Initialize PEP service.
        
        Args:
            jwt_handler: JWT handler for token verification
            service_name: Name of this service for audience validation
        """
        self.jwt_handler = jwt_handler
        self.service_name = service_name
        self.transaction_tracker = get_transaction_tracker()
        self.metrics = get_metrics_collector()
    
    def verify_visa_token(
        self,
        token: str,
        current_reasoning_hash: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        Verify an A-JWT Digital Visa token.
        
        Args:
            token: JWT token string
            current_reasoning_hash: Current reasoning state hash (optional)
            request_context: Current request details for constraint validation
            
        Returns:
            VerificationResult with detailed validation status
        """
        start_time = datetime.utcnow()
        self.metrics.increment('token_verifications_total')
        
        result = VerificationResult(valid=False)
        
        try:
            # Decode and verify token
            try:
                payload = self.jwt_handler.verify_visa_token(
                    token,
                    expected_audience=self.service_name
                )
                result.not_expired = True
                result.audience_match = True
            except pyjwt.ExpiredSignatureError:
                result.error_message = "Token has expired"
                self.metrics.increment('token_verification_failures_total')
                return result
            except pyjwt.InvalidAudienceError:
                result.error_message = "Token audience mismatch"
                result.not_expired = True
                self.metrics.increment('token_verification_failures_total')
                return result
            except pyjwt.InvalidTokenError as e:
                result.error_message = f"Invalid token: {str(e)}"
                self.metrics.increment('token_verification_failures_total')
                return result
            
            # Extract key fields
            result.agent_id = payload.get('sub')
            result.transaction_id = payload.get('jti')
            intent_hash = payload.get('intent_hash')
            constraints = payload.get('constraints', {})
            
            # Check for replay attack
            if self.transaction_tracker.is_used(result.transaction_id):
                result.error_message = "Token has already been used (replay attack detected)"
                self.metrics.increment('token_verification_failures_total')
                return result
            
            result.not_replayed = True
            
            # Validate reasoning hash if provided
            if current_reasoning_hash:
                if current_reasoning_hash == intent_hash:
                    result.reasoning_hash_valid = True
                else:
                    result.error_message = "Reasoning state has drifted from visa issuance"
                    self.metrics.increment('token_verification_failures_total')
                    return result
            else:
                result.reasoning_hash_valid = True  # Not checked
            
            # Validate constraints against current request
            if request_context:
                constraints_valid, constraint_error = self._validate_constraints(
                    constraints, request_context
                )
                if not constraints_valid:
                    result.error_message = f"Constraint violation: {constraint_error}"
                    self.metrics.increment('token_verification_failures_total')
                    return result
                result.constraints_met = True
            else:
                result.constraints_met = True  # Not checked
            
            # Mark transaction as used
            self.transaction_tracker.mark_used(result.transaction_id)
            
            # Generate trace ID
            result.trace_id = f"trace_{result.transaction_id[:8]}"
            
            # All checks passed
            result.valid = True
            
        except Exception as e:
            result.error_message = f"Verification error: {str(e)}"
            self.metrics.increment('token_verification_failures_total')
        
        # Record latency
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.metrics.record_latency('token_verification_latency_ms', latency_ms)
        
        return result
    
    def _validate_constraints(
        self,
        constraints: Dict[str, Any],
        request_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate token constraints against request context.
        
        Args:
            constraints: Token constraints from A-JWT
            request_context: Current request details
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate maximum amount
        if 'max_amount' in constraints:
            request_amount = request_context.get('amount', 0)
            if request_amount > constraints['max_amount']:
                return False, f"Amount {request_amount} exceeds max {constraints['max_amount']}"
        
        # Validate currency
        if 'currency' in constraints:
            request_currency = request_context.get('currency', 'USD')
            if request_currency != constraints['currency']:
                return False, f"Currency {request_currency} doesn't match {constraints['currency']}"
        
        # Validate allowed operations
        if 'allowed_operations' in constraints:
            request_operation = request_context.get('operation')
            if request_operation and request_operation not in constraints['allowed_operations']:
                return False, f"Operation {request_operation} not allowed"
        
        # Validate allowed customers
        if 'allowed_customers' in constraints:
            request_customer = request_context.get('customer_id')
            if request_customer and request_customer not in constraints['allowed_customers']:
                return False, f"Customer {request_customer} not allowed"
        
        # Validate approver if specified
        if 'approver' in constraints:
            request_approver = request_context.get('approver')
            if not request_approver or request_approver != constraints['approver']:
                return False, "Approver validation failed"
        
        return True, None
    
    def validate_consensus_proof(
        self,
        token: str,
        consensus_tokens: list[str]
    ) -> Tuple[bool, str]:
        """
        Validate that multiple tokens form valid consensus proof.
        
        Args:
            token: Primary token to validate
            consensus_tokens: Additional tokens for consensus
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Verify primary token
            primary_result = self.verify_visa_token(token)
            if not primary_result.valid:
                return False, f"Primary token invalid: {primary_result.error_message}"
            
            # Verify all consensus tokens
            valid_count = 1  # Primary token
            total_count = 1 + len(consensus_tokens)
            
            for consensus_token in consensus_tokens:
                result = self.verify_visa_token(consensus_token)
                if result.valid:
                    valid_count += 1
            
            # Check if we have 2/3 consensus
            consensus_ratio = valid_count / total_count
            if consensus_ratio >= 0.67:
                self.metrics.increment('consensus_requests_total')
                return True, f"Consensus achieved: {valid_count}/{total_count}"
            else:
                return False, f"Insufficient consensus: {valid_count}/{total_count} (need 2/3)"
        
        except Exception as e:
            return False, f"Consensus validation error: {str(e)}"
    
    def get_token_metadata(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from token without full verification.
        
        Args:
            token: JWT token string
            
        Returns:
            Token metadata or None if invalid
        """
        try:
            unverified = pyjwt.decode(token, options={'verify_signature': False})
            return {
                'agent_id': unverified.get('sub'),
                'transaction_id': unverified.get('jti'),
                'intent_hash': unverified.get('intent_hash'),
                'scopes': unverified.get('scope', []),
                'expires_at': datetime.fromtimestamp(unverified.get('exp', 0)).isoformat()
            }
        except Exception:
            return None
