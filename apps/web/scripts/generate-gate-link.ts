import dotenv from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHmac } from 'node:crypto';

const currentFilePath = fileURLToPath(import.meta.url);
const currentDirectoryPath = path.dirname(currentFilePath);
const webRootPath = path.resolve(currentDirectoryPath, '..');
const monorepoRootPath = path.resolve(currentDirectoryPath, '..', '..', '..');

dotenv.config({ path: path.join(monorepoRootPath, '.env') });
dotenv.config({ path: path.join(monorepoRootPath, '.env.local') });
dotenv.config({ path: path.join(webRootPath, '.env') });
dotenv.config({ path: path.join(webRootPath, '.env.local') });

type GateKind = 'user' | 'admin';

type GatePayload = {
  sub: string;
  exp: number;
  kind: GateKind;
};

function getRequiredEnv(name: string): string {
  const value = process.env[name];

  if (!value || value.trim().length === 0) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value.trim();
}

function getPositiveInteger(rawValue: string, fieldName: string): number {
  const parsedValue = Number(rawValue);

  if (!Number.isInteger(parsedValue) || parsedValue <= 0) {
    throw new Error(`Invalid ${fieldName}`);
  }

  return parsedValue;
}

function parseGateKind(rawValue: string): GateKind {
  if (rawValue === 'user' || rawValue === 'admin') {
    return rawValue;
  }

  throw new Error('GATEKEEPER_KIND must be either "user" or "admin"');
}

function base64UrlEncodeUtf8(value: string): string {
  return Buffer.from(value, 'utf8').toString('base64url');
}

function signValue(payloadEncoded: string, secret: string): string {
  return createHmac('sha256', secret).update(payloadEncoded).digest('base64url');
}

function buildSignedToken(payload: GatePayload, secret: string): string {
  const payloadEncoded = base64UrlEncodeUtf8(JSON.stringify(payload));
  const signature = signValue(payloadEncoded, secret);

  return `${payloadEncoded}.${signature}`;
}

function getEntryPath(kind: GateKind): string {
  return kind === 'admin' ? '/admin-enter' : '/enter';
}

function getDefaultSubject(kind: GateKind): string {
  return kind === 'admin' ? 'owner-admin' : 'visitor-access';
}

function getDefaultTtlSeconds(kind: GateKind): number {
  return kind === 'admin' ? 900 : 3600;
}

function main(): void {
  const secret = getRequiredEnv('GATEKEEPER_SECRET');
  const baseUrl = process.env.GATEKEEPER_BASE_URL?.trim() || 'https://airdeliver.vercel.app';
  const kind = parseGateKind(getRequiredEnv('GATEKEEPER_KIND'));

  const subject = process.env.GATEKEEPER_SUBJECT?.trim() || getDefaultSubject(kind);
  const ttlSeconds = getPositiveInteger(
    process.env.GATEKEEPER_TTL_SECONDS?.trim() ?? String(getDefaultTtlSeconds(kind)),
    'GATEKEEPER_TTL_SECONDS',
  );

  const expiresAtEpochSeconds = Math.floor(Date.now() / 1000) + ttlSeconds;

  const token = buildSignedToken(
    {
      sub: subject,
      exp: expiresAtEpochSeconds,
      kind,
    },
    secret,
  );

  const url = new URL(getEntryPath(kind), baseUrl);
  url.searchParams.set('token', token);

  process.stdout.write(`${url.toString()}\n`);
}

main();
