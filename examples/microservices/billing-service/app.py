"""
Example Billing Service with Digital Visa integration.

This microservice demonstrates how to integrate the Digital Visa Protocol
for secure, bounded agent authorization.
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from common.utils import AgenticJWTHandler
from pep.policy_enforcement_point import PolicyEnforcementPoint

app = Flask(__name__)

# Initialize PEP for token verification
jwt_handler = AgenticJWTHandler()
pep = PolicyEnforcementPoint(jwt_handler, service_name="billing-service")

# Mock database
transactions = []
customers = {
    "customer_123": {
        "name": "John Doe",
        "balance": 1000.00,
        "orders": [
            {"order_id": "order_456", "amount": 125.00, "date": "2024-12-15"}
        ]
    }
}


def verify_digital_visa():
    """Middleware to verify Digital Visa token."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return {'error': 'Missing or invalid Authorization header'}, 401
    
    token = auth_header.split(' ')[1]
    
    # Extract request context for constraint validation
    request_context = {
        'method': request.method,
        'path': request.path,
        'operation': request.json.get('operation') if request.json else None,
        'amount': request.json.get('amount') if request.json else None,
        'currency': request.json.get('currency', 'USD') if request.json else None,
        'customer_id': request.json.get('customer_id') if request.json else None
    }
    
    # Verify token
    result = pep.verify_visa_token(
        token=token,
        request_context=request_context
    )
    
    if not result.valid:
        return {'error': result.error_message}, 403
    
    return result, None


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'billing-service'})


@app.route('/api/billing/refund', methods=['POST'])
def process_refund():
    """
    Process a refund with Digital Visa authorization.
    
    Required headers:
    - Authorization: Bearer <digital-visa-token>
    
    Request body:
    {
        "customer_id": "customer_123",
        "order_id": "order_456",
        "amount": 125.00,
        "currency": "USD",
        "reason": "Customer request",
        "operation": "refund"
    }
    """
    # Verify Digital Visa
    verification_result, error = verify_digital_visa()
    if error:
        return jsonify(verification_result), error[1]
    
    # Extract request data
    data = request.json
    customer_id = data.get('customer_id')
    order_id = data.get('order_id')
    amount = data.get('amount')
    currency = data.get('currency', 'USD')
    reason = data.get('reason', '')
    
    # Validate customer exists
    if customer_id not in customers:
        return jsonify({'error': 'Customer not found'}), 404
    
    # Process refund
    transaction_id = f"txn_{len(transactions) + 1}"
    transaction = {
        'transaction_id': transaction_id,
        'customer_id': customer_id,
        'order_id': order_id,
        'amount': amount,
        'currency': currency,
        'type': 'refund',
        'reason': reason,
        'agent_id': verification_result.agent_id,
        'visa_transaction_id': verification_result.transaction_id,
        'trace_id': verification_result.trace_id,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'completed'
    }
    
    transactions.append(transaction)
    
    # Update customer balance
    customers[customer_id]['balance'] += amount
    
    return jsonify({
        'success': True,
        'transaction_id': transaction_id,
        'amount': amount,
        'currency': currency,
        'new_balance': customers[customer_id]['balance'],
        'trace_id': verification_result.trace_id
    }), 200


@app.route('/api/billing/transactions', methods=['GET'])
def list_transactions():
    """
    List recent transactions.
    
    Required headers:
    - Authorization: Bearer <digital-visa-token>
    """
    # Verify Digital Visa
    verification_result, error = verify_digital_visa()
    if error:
        return jsonify(verification_result), error[1]
    
    return jsonify({
        'transactions': transactions[-10:],  # Last 10 transactions
        'count': len(transactions)
    }), 200


@app.route('/api/billing/customer/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    """
    Get customer information.
    
    Required headers:
    - Authorization: Bearer <digital-visa-token>
    """
    # Verify Digital Visa
    verification_result, error = verify_digital_visa()
    if error:
        return jsonify(verification_result), error[1]
    
    if customer_id not in customers:
        return jsonify({'error': 'Customer not found'}), 404
    
    return jsonify(customers[customer_id]), 200


if __name__ == '__main__':
    print("Starting Billing Service with Digital Visa Protocol...")
    print("Service: billing-service")
    print("Port: 5001")
    print("\nAll requests require valid Digital Visa (A-JWT) token in Authorization header")
    print("Example: Authorization: Bearer <token>\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
