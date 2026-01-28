import * as crypto from 'crypto';
import * as jwt from 'jsonwebtoken';

/**
 * Interface for A-JWT (Agentic JWT) payload
 */
export interface AJWTPayload {
  intent_hash: string;
  visa_ttl: number;
  scope: string;
  nonce: string;
  constraints?: {
    max_amount?: number;
    [key: string]: any;
  };
  iat: number;
  exp: number;
}

/**
 * Interface for transaction data used to generate intent hash
 */
export interface TransactionData {
  action: string;
  scope: string;
  timestamp: number;
  parameters?: Record<string, any>;
}

/**
 * Options for minting an A-JWT
 */
export interface MintOptions {
  scope: string;
  visa_ttl?: number; // TTL in seconds, defaults to 30
  constraints?: {
    max_amount?: number;
    [key: string]: any;
  };
  transactionData: TransactionData;
  secret: string; // Secret key for signing JWT
}

/**
 * Generates a SHA-256 hash of the transaction data to create intent_hash
 * @param data Transaction data to hash
 * @returns SHA-256 hash as hex string
 */
export function generateIntentHash(data: TransactionData): string {
  const dataString = JSON.stringify(data);
  const hash = crypto.createHash('sha256');
  hash.update(dataString);
  return hash.digest('hex');
}

/**
 * Generates a short-lived nonce using random bytes and timestamp
 * @returns Nonce as hex string
 */
export function generateNonce(): string {
  const randomBytes = crypto.randomBytes(16);
  const timestamp = Date.now();
  const nonce = crypto.createHash('sha256')
    .update(randomBytes)
    .update(timestamp.toString())
    .digest('hex')
    .substring(0, 16); // Short nonce
  return nonce;
}

/**
 * Mints a transaction-bound A-JWT (Agentic JWT) with intent hash and nonce
 * @param options Minting options including scope, TTL, constraints, and transaction data
 * @returns Signed JWT token string
 */
export function mintAJWT(options: MintOptions): string {
  const {
    scope,
    visa_ttl = 30, // Default 30 seconds
    constraints,
    transactionData,
    secret
  } = options;

  // Generate intent hash from transaction data
  const intent_hash = generateIntentHash(transactionData);

  // Generate short-lived nonce
  const nonce = generateNonce();

  // Current timestamp
  const now = Math.floor(Date.now() / 1000);

  // Build payload
  const payload: AJWTPayload = {
    intent_hash,
    visa_ttl,
    scope,
    nonce,
    iat: now,
    exp: now + visa_ttl
  };

  // Add constraints if provided
  if (constraints) {
    payload.constraints = constraints;
  }

  // Sign and return JWT
  const token = jwt.sign(payload, secret, {
    algorithm: 'HS256'
  });

  return token;
}

/**
 * Decodes an A-JWT without verification (for inspection purposes)
 * @param token JWT token string
 * @returns Decoded payload or null if invalid
 */
export function decodeAJWT(token: string): AJWTPayload | null {
  try {
    const decoded = jwt.decode(token) as AJWTPayload;
    return decoded;
  } catch (error) {
    return null;
  }
}

/**
 * Verifies and decodes an A-JWT
 * @param token JWT token string
 * @param secret Secret key used for signing
 * @returns Decoded and verified payload
 * @throws Error if verification fails
 */
export function verifyAJWT(token: string, secret: string): AJWTPayload {
  try {
    const decoded = jwt.verify(token, secret, {
      algorithms: ['HS256']
    }) as AJWTPayload;
    return decoded;
  } catch (error) {
    throw new Error(`JWT verification failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}
