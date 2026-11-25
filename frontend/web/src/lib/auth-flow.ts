import { api } from '@/lib/api';

export async function registerAccount(input: { email: string; password: string; fullName: string }): Promise<void> {
  if (!input.email.trim() || input.password.length < 8 || input.password.length > 128 || input.fullName.trim().length > 100) throw new Error('Invalid registration details');
  await api.post('/users/', { email: input.email.trim(), password: input.password, full_name: input.fullName.trim() || null });
}

export function safeCallbackPath(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f]/.test(value)) return '/';
  try {
    const url = new URL(value, 'https://local.invalid');
    return url.origin === 'https://local.invalid' ? url.pathname + url.search + url.hash : '/';
  } catch { return '/'; }
}
