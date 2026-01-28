import {
  generateIntentHash,
  generateNonce,
  mintAJWT,
  decodeAJWT,
  verifyAJWT,
  TransactionData,
  MintOptions
} from './digitalVisa';

describe('Digital Visa - A-JWT Helper', () => {
  const testSecret = 'test-secret-key-for-jwt';

  describe('generateIntentHash', () => {
    it('should generate a SHA-256 hash from transaction data', () => {
      const transactionData: TransactionData = {
        action: 'transfer',
        scope: 'billing',
        timestamp: 1234567890,
        parameters: { amount: 100 }
      };

      const hash = generateIntentHash(transactionData);

      expect(hash).toBeDefined();
      expect(hash).toHaveLength(64); // SHA-256 produces 64 hex characters
      expect(typeof hash).toBe('string');
    });

    it('should generate same hash for identical data', () => {
      const transactionData: TransactionData = {
        action: 'transfer',
        scope: 'billing',
        timestamp: 1234567890
      };

      const hash1 = generateIntentHash(transactionData);
      const hash2 = generateIntentHash(transactionData);

      expect(hash1).toBe(hash2);
    });

    it('should generate different hashes for different data', () => {
      const data1: TransactionData = {
        action: 'transfer',
        scope: 'billing',
        timestamp: 1234567890
      };

      const data2: TransactionData = {
        action: 'transfer',
        scope: 'billing',
        timestamp: 1234567891
      };

      const hash1 = generateIntentHash(data1);
      const hash2 = generateIntentHash(data2);

      expect(hash1).not.toBe(hash2);
    });
  });

  describe('generateNonce', () => {
    it('should generate a nonce', () => {
      const nonce = generateNonce();

      expect(nonce).toBeDefined();
      expect(typeof nonce).toBe('string');
      expect(nonce).toHaveLength(16);
    });

    it('should generate unique nonces', () => {
      const nonce1 = generateNonce();
      const nonce2 = generateNonce();

      expect(nonce1).not.toBe(nonce2);
    });
  });

  describe('mintAJWT', () => {
    it('should mint a valid A-JWT with all required fields', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        visa_ttl: 30,
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);

      expect(token).toBeDefined();
      expect(typeof token).toBe('string');
      expect(token.split('.')).toHaveLength(3); // JWT has 3 parts
    });

    it('should mint A-JWT with default TTL of 30 seconds', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.visa_ttl).toBe(30);
    });

    it('should mint A-JWT with custom TTL', () => {
      const transactionData: TransactionData = {
        action: 'write',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        visa_ttl: 45,
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.visa_ttl).toBe(45);
    });

    it('should mint A-JWT with billing constraints', () => {
      const transactionData: TransactionData = {
        action: 'charge',
        scope: 'billing',
        timestamp: Date.now(),
        parameters: { amount: 100 }
      };

      const options: MintOptions = {
        scope: 'billing',
        visa_ttl: 30,
        constraints: {
          max_amount: 150
        },
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.scope).toBe('billing');
      expect(decoded!.constraints).toBeDefined();
      expect(decoded!.constraints!.max_amount).toBe(150);
    });

    it('should include intent_hash in the token', () => {
      const transactionData: TransactionData = {
        action: 'transfer',
        scope: 'billing',
        timestamp: Date.now()
      };

      const expectedHash = generateIntentHash(transactionData);

      const options: MintOptions = {
        scope: 'billing',
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.intent_hash).toBe(expectedHash);
    });

    it('should include nonce in the token', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.nonce).toBeDefined();
      expect(typeof decoded!.nonce).toBe('string');
    });

    it('should include iat and exp timestamps', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        visa_ttl: 30,
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.iat).toBeDefined();
      expect(decoded!.exp).toBeDefined();
      expect(decoded!.exp).toBe(decoded!.iat + 30);
    });
  });

  describe('decodeAJWT', () => {
    it('should decode a valid A-JWT', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.scope).toBe('data');
    });

    it('should return null for invalid token', () => {
      const decoded = decodeAJWT('invalid-token');
      expect(decoded).toBeNull();
    });
  });

  describe('verifyAJWT', () => {
    it('should verify and decode a valid A-JWT', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const verified = verifyAJWT(token, testSecret);

      expect(verified).toBeDefined();
      expect(verified.scope).toBe('data');
      expect(verified.intent_hash).toBeDefined();
      expect(verified.nonce).toBeDefined();
    });

    it('should throw error for token with wrong secret', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);

      expect(() => {
        verifyAJWT(token, 'wrong-secret');
      }).toThrow();
    });

    it('should throw error for invalid token', () => {
      expect(() => {
        verifyAJWT('invalid-token', testSecret);
      }).toThrow();
    });
  });

  describe('Integration with OPA Policy', () => {
    it('should create token that passes OPA validation (visa_ttl < 60)', () => {
      const transactionData: TransactionData = {
        action: 'read',
        scope: 'data',
        timestamp: Date.now()
      };

      const options: MintOptions = {
        scope: 'data',
        visa_ttl: 30, // Less than 60
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.visa_ttl).toBeLessThan(60);
    });

    it('should create billing token with valid max_amount constraint', () => {
      const transactionData: TransactionData = {
        action: 'charge',
        scope: 'billing',
        timestamp: Date.now(),
        parameters: { amount: 100 }
      };

      const options: MintOptions = {
        scope: 'billing',
        visa_ttl: 30,
        constraints: {
          max_amount: 100 // Less than or equal to 150
        },
        transactionData,
        secret: testSecret
      };

      const token = mintAJWT(options);
      const decoded = decodeAJWT(token);

      expect(decoded).not.toBeNull();
      expect(decoded!.scope).toBe('billing');
      expect(decoded!.constraints!.max_amount).toBeLessThanOrEqual(150);
    });
  });
});
