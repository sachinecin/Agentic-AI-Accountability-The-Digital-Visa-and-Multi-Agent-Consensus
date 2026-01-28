import {
  mintAJWT,
  decodeAJWT,
  verifyAJWT,
  generateIntentHash,
  TransactionData
} from '../src/digitalVisa';

/**
 * Example 1: Minting a basic A-JWT for a read operation
 */
function example1_BasicReadToken() {
  console.log('\n=== Example 1: Basic Read Token ===');

  const transactionData: TransactionData = {
    action: 'read',
    scope: 'data',
    timestamp: Date.now(),
    parameters: {
      resource: '/api/users/123'
    }
  };

  const token = mintAJWT({
    scope: 'data',
    visa_ttl: 30,
    transactionData,
    secret: 'my-secret-key'
  });

  console.log('Token:', token);

  const decoded = decodeAJWT(token);
  console.log('Decoded payload:', JSON.stringify(decoded, null, 2));
}

/**
 * Example 2: Minting a billing token with constraints
 */
function example2_BillingToken() {
  console.log('\n=== Example 2: Billing Token with Constraints ===');

  const transactionData: TransactionData = {
    action: 'charge',
    scope: 'billing',
    timestamp: Date.now(),
    parameters: {
      userId: 'user123',
      amount: 100,
      currency: 'USD'
    }
  };

  const token = mintAJWT({
    scope: 'billing',
    visa_ttl: 45,
    constraints: {
      max_amount: 150
    },
    transactionData,
    secret: 'my-secret-key'
  });

  console.log('Billing Token:', token);

  const decoded = decodeAJWT(token);
  console.log('Decoded payload:', JSON.stringify(decoded, null, 2));
  console.log(`Max amount constraint: ${decoded?.constraints?.max_amount}`);
}

/**
 * Example 3: Verifying a token
 */
function example3_VerifyToken() {
  console.log('\n=== Example 3: Verify Token ===');

  const transactionData: TransactionData = {
    action: 'write',
    scope: 'data',
    timestamp: Date.now()
  };

  const secret = 'my-secret-key';
  const token = mintAJWT({
    scope: 'data',
    transactionData,
    secret
  });

  try {
    const verified = verifyAJWT(token, secret);
    console.log('Token verified successfully!');
    console.log('Intent hash:', verified.intent_hash);
    console.log('Nonce:', verified.nonce);
    console.log('TTL:', verified.visa_ttl, 'seconds');
  } catch (error) {
    console.error('Verification failed:', error);
  }
}

/**
 * Example 4: Preparing input for OPA policy validation
 */
function example4_OPAPolicyInput() {
  console.log('\n=== Example 4: OPA Policy Input ===');

  const transactionData: TransactionData = {
    action: 'charge',
    scope: 'billing',
    timestamp: Date.now(),
    parameters: {
      amount: 100
    }
  };

  const token = mintAJWT({
    scope: 'billing',
    visa_ttl: 30,
    constraints: {
      max_amount: 150
    },
    transactionData,
    secret: 'my-secret-key'
  });

  const decoded = decodeAJWT(token);
  
  // Calculate current state hash (should match intent_hash for valid request)
  const currentStateHash = generateIntentHash(transactionData);

  const opaInput = {
    token: {
      intent_hash: decoded?.intent_hash,
      visa_ttl: decoded?.visa_ttl,
      scope: decoded?.scope,
      constraints: decoded?.constraints
    },
    request: {
      current_state_hash: currentStateHash
    }
  };

  console.log('OPA Policy Input:');
  console.log(JSON.stringify(opaInput, null, 2));
  console.log('\nIntent hash matches:', decoded?.intent_hash === currentStateHash);
  console.log('TTL < 60:', decoded?.visa_ttl! < 60);
  console.log('Max amount <= 150:', decoded?.constraints?.max_amount! <= 150);
}

/**
 * Example 5: Token with different transaction (intent_hash mismatch)
 */
function example5_IntentHashMismatch() {
  console.log('\n=== Example 5: Intent Hash Mismatch ===');

  const originalTransaction: TransactionData = {
    action: 'charge',
    scope: 'billing',
    timestamp: Date.now(),
    parameters: { amount: 100 }
  };

  const token = mintAJWT({
    scope: 'billing',
    visa_ttl: 30,
    constraints: { max_amount: 150 },
    transactionData: originalTransaction,
    secret: 'my-secret-key'
  });

  const decoded = decodeAJWT(token);

  // Different transaction with modified amount
  const modifiedTransaction: TransactionData = {
    action: 'charge',
    scope: 'billing',
    timestamp: Date.now(),
    parameters: { amount: 200 } // Changed!
  };

  const currentStateHash = generateIntentHash(modifiedTransaction);

  console.log('Token intent_hash:', decoded?.intent_hash);
  console.log('Current state hash:', currentStateHash);
  console.log('Hashes match:', decoded?.intent_hash === currentStateHash);
  console.log('\n⚠️  This token would be REJECTED by OPA policy due to hash mismatch');
}

/**
 * Example 6: Multiple tokens for different scopes
 */
function example6_MultipleScopes() {
  console.log('\n=== Example 6: Multiple Scopes ===');

  const scopes = ['read', 'write', 'billing'];
  const secret = 'my-secret-key';

  scopes.forEach(scope => {
    const transactionData: TransactionData = {
      action: scope === 'billing' ? 'charge' : scope,
      scope,
      timestamp: Date.now()
    };

    const options: any = {
      scope,
      visa_ttl: 30,
      transactionData,
      secret
    };

    if (scope === 'billing') {
      options.constraints = { max_amount: 100 };
    }

    const token = mintAJWT(options);
    const decoded = decodeAJWT(token);

    console.log(`\nScope: ${scope}`);
    console.log(`  TTL: ${decoded?.visa_ttl}s`);
    console.log(`  Has constraints: ${!!decoded?.constraints}`);
    if (decoded?.constraints) {
      console.log(`  Max amount: ${decoded.constraints.max_amount}`);
    }
  });
}

// Run all examples
console.log('╔═══════════════════════════════════════════════════════╗');
console.log('║     Digital Visa Protocol - Usage Examples          ║');
console.log('╚═══════════════════════════════════════════════════════╝');

example1_BasicReadToken();
example2_BillingToken();
example3_VerifyToken();
example4_OPAPolicyInput();
example5_IntentHashMismatch();
example6_MultipleScopes();

console.log('\n✅ All examples completed!\n');
