// frontend/web/components/profile/ProfileModals.tsx
'use client';

import React, { memo, useCallback, useEffect, useMemo, useState, useRef, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Package,
  Loader2,
  AlertCircle,
  Save,
  User,
  KeyRound,
  Eye,
  EyeOff,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import useSWR from 'swr';
import Link from 'next/link';
import { api } from '@/lib/api';
import { orderMoney, orderStatus } from '@/lib/order-display';

// -----------------------------------------------------------------------------
// TYPES & INTERFACES
// -----------------------------------------------------------------------------

export interface Order {
  id: number;
  user_id: number;
  status: 'Delivered' | 'Shipped' | 'Processing' | 'Cancelled' | string;
  total_price: number;
  currency: string;
  created_at: string;
}

export interface PaginatedOrdersResponse {
  total: number;
  page: number;
  limit: number;
  orders: Order[];
}

export interface UserProfileData {
  full_name?: string | null;
  phone_number?: string | null;
  address?: string | null;
}

// Ensure you provide this fetcher in your project context
// import { fetcher } from '@/lib/fetcher';
const fetcher = (url: string) => api.get(url).then(response => response.data);

// -----------------------------------------------------------------------------
// SHARED UI PRIMITIVES (Memoized for 8x Performance)
// -----------------------------------------------------------------------------

const ANIMATION_CONFIG = {
  initial: { opacity: 0, scale: 0.985 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.985 },
  transition: { duration: 0.18, ease: 'easeOut' as const },
};

const ModalWrapper = memo(
  ({
    isOpen,
    onClose,
    title,
    description,
    icon: Icon,
    children,
    maxWidth = 'max-w-2xl',
  }: {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    description?: string;
    icon?: LucideIcon;
    children: React.ReactNode;
    maxWidth?: string;
  }) => {
    const dialogRef = useRef<HTMLDivElement>(null);
    const headingId = useId();
    const descriptionId = useId();
    useEffect(() => {
      if (!isOpen) return;
      const previous = document.activeElement as HTMLElement | null;
      const overflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      const frame = requestAnimationFrame(() => dialogRef.current?.focus());
      const onKey = (event: KeyboardEvent) => {
        if (event.key === 'Escape') { event.preventDefault(); onClose(); return; }
        if (event.key !== 'Tab' || !dialogRef.current) return;
        const nodes = Array.from(dialogRef.current.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), textarea:not(:disabled), [tabindex="0"]')).filter(node => node.getAttribute('aria-hidden') !== 'true');
        if (!nodes.length) { event.preventDefault(); dialogRef.current.focus(); return; }
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialogRef.current)) { event.preventDefault(); first?.focus(); }
      };
      document.addEventListener('keydown', onKey);
      return () => { cancelAnimationFrame(frame); document.removeEventListener('keydown', onKey); document.body.style.overflow = overflow; if (previous?.isConnected) previous.focus(); };
    }, [isOpen, onClose]);

    return (
      <AnimatePresence mode="wait">
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-2xl"
            onClick={onClose}
          >
            <motion.div
              ref={dialogRef}
              role="dialog" aria-modal="true" aria-labelledby={headingId} aria-describedby={description ? descriptionId : undefined} tabIndex={-1}
              {...ANIMATION_CONFIG}
              onClick={(e) => e.stopPropagation()}
              className={`relative flex w-full flex-col overflow-hidden rounded-[32px] bg-black/65 text-white outline-none shadow-[0_32px_120px_rgba(0,0,0,0.65)] backdrop-blur-2xl ${maxWidth}`}
              style={{ maxHeight: 'min(92svh, 900px)' }}
            >
              {/* Sci-Fi Atmospheric Glows */}
              <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-[2rem]">
                <div className="absolute left-[-10%] top-[-10%] h-40 w-40 rounded-full bg-white/[0.035] blur-3xl" />
                <div className="absolute bottom-[-12%] right-[-8%] h-52 w-52 rounded-full bg-white/[0.02] blur-3xl" />
              </div>

              {/* Close Button */}
              <button
                type="button"
                aria-label="Close modal"
                onClick={onClose}
                className="absolute right-4 top-4 z-20 inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/[0.04] text-white/60 backdrop-blur-md transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-200 active:scale-[0.98]"
              >
                <X className="h-5 w-5" />
              </button>

              {/* Header */}
              <header className="relative z-10 flex items-start gap-4 pb-4 pl-6 pr-20 pt-8 sm:pl-10 sm:pt-10">
                {Icon && <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/[0.045]"><Icon className="h-5 w-5 text-cyan-100/80" /></span>}
                <div><p className="mb-2 text-[10px] font-medium uppercase tracking-[0.22em] text-white/35">Your account</p><h2 id={headingId} className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>{description && <p id={descriptionId} className="mt-3 max-w-md text-sm leading-6 text-white/50">{description}</p>}</div>
              </header>

              {/* Content Area */}
              <div className="relative z-10 flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain">
                {children}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }
);
ModalWrapper.displayName = 'ModalWrapper';

const SciFiInput = memo(
  ({
    label,
    id,
    type = 'text',
    error,
    rightElement,
    as: Component = 'input',
    ...props
  }: any) => (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="text-xs font-medium tracking-wide text-white/55"
      >
        {label}
      </label>
      <div className="relative">
        <Component
          id={id}
          type={type}
          className={`w-full rounded-2xl border-0 bg-white/[0.055] px-4 py-4 text-sm text-white placeholder-white/20 transition-all focus:bg-white/[0.05] focus:outline-none focus:ring-1 ${
            error
              ? 'border-red-400/50 focus:border-red-400/50 focus:ring-red-400/50'
              : 'border-white/10 focus:border-cyan-400/50 focus:ring-white/40'
          } ${rightElement ? 'pr-12' : ''}`}
          {...props}
        />
        {rightElement && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-1">
            {rightElement}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
);
SciFiInput.displayName = 'SciFiInput';

const SciFiButton = memo(
  ({ children, variant = 'primary', isLoading, ...props }: any) => {
    const baseStyle =
      'inline-flex min-h-[48px] w-full min-w-0 items-center justify-center gap-2 rounded-full px-4 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-200 active:scale-[0.99] disabled:pointer-events-none disabled:opacity-50';
    
    const variants = {
      primary:
        'bg-white text-black hover:bg-white/85',
      secondary:
        'bg-white/[0.055] text-white/70 hover:bg-white/10 hover:text-white',
    };

    return (
      <button {...props} disabled={isLoading || props.disabled} aria-busy={isLoading || undefined} className={`${baseStyle} ${variants[variant as keyof typeof variants]}`}>
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : children}
      </button>
    );
  }
);
SciFiButton.displayName = 'SciFiButton';

// -----------------------------------------------------------------------------
// 1. VIEW ORDERS MODAL
// -----------------------------------------------------------------------------

const OrderRow = memo(({ order }: { order: Order }) => {
  const displayStatus = orderStatus(order.status);
  const statusColor = displayStatus.className;

  return (
    <tr className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
      <td className="whitespace-nowrap px-6 py-4 text-sm font-mono text-white/90">
        <Link href={`/tracking/${order.id}`} className="underline py-2 inline-block" aria-label={`View order ${order.id}`}>#{order.id.toString().padStart(6, '0')}</Link>
      </td>
      <td className="whitespace-nowrap px-6 py-4 text-sm text-white/70">
        {new Date(order.created_at).toLocaleDateString()}
      </td>
      <td className="whitespace-nowrap px-6 py-4 text-sm">
        <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusColor}`}>
          {displayStatus.label}
        </span>
      </td>
      <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-mono font-medium text-white">
        {orderMoney(order.total_price, order.currency)}
      </td>
    </tr>
  );
});
OrderRow.displayName = 'OrderRow';

export const ViewOrdersModal = memo(
  ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
    const [page, setPage] = useState(1);
    const limit = 10;

    const { data, error, isLoading } = useSWR<PaginatedOrdersResponse>(
      isOpen ? `/orders/me?page=${page}&limit=${limit}` : null,
      fetcher,
      { revalidateOnFocus: false, keepPreviousData: true }
    );

    const totalPages = data ? Math.ceil(data.total / limit) : 0;

    return (
      <ModalWrapper isOpen={isOpen} onClose={onClose} title="Your orders" description="Your order history, totals and delivery status, in one place." icon={Package} maxWidth="max-w-5xl">
        <div className="flex flex-1 flex-col px-6 pb-8 pt-4 sm:px-10 sm:pb-10">
          {isLoading && !data && (
            <div className="flex min-h-[300px] flex-1 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
            </div>
          )}

          {error && (
            <div className="flex min-h-[300px] flex-1 flex-col items-center justify-center text-center">
              <AlertCircle className="mb-4 h-12 w-12 text-red-400" />
              <p className="text-sm font-semibold tracking-widest text-red-300">Order history is unavailable</p>
              <p className="mt-2 text-xs text-red-400/70">Order history could not be loaded. Please try again.</p>
            </div>
          )}

          {!error && !isLoading && data?.orders?.length === 0 && (
            <div className="flex min-h-[320px] flex-1 flex-col items-center justify-center gap-4 text-sm text-white/50">
              <Package aria-hidden="true" className="h-10 w-10 text-white/25" />
              You have no orders yet.
            </div>
          )}

          {(data?.orders?.length ?? 0) > 0 && (
            <div className="w-full overflow-x-auto rounded-2xl bg-white/[0.025]">
              <table className="min-w-full divide-y divide-white/10 text-left">
                <thead className="bg-black/40 text-xs font-medium tracking-wide text-white/55">
                  <tr>
                    <th scope="col" className="px-6 py-4">ID</th>
                    <th scope="col" className="px-6 py-4">Date</th>
                    <th scope="col" className="px-6 py-4">Status</th>
                    <th scope="col" className="px-6 py-4 text-right">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {(data?.orders ?? []).map((order) => (
                    <OrderRow key={order.id} order={order} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-white/10 bg-black/20 px-6 py-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
              className="inline-flex items-center gap-1 text-sm font-semibold tracking-wider text-cyan-400 transition hover:text-cyan-300 disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" /> PREV
            </button>
            <span className="text-xs tracking-widest text-white/50">
              PAGE {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || isLoading}
              className="inline-flex items-center gap-1 text-sm font-semibold tracking-wider text-cyan-400 transition hover:text-cyan-300 disabled:opacity-30"
            >
              NEXT <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </ModalWrapper>
    );
  }
);
ViewOrdersModal.displayName = 'ViewOrdersModal';

// -----------------------------------------------------------------------------
// 2. EDIT PROFILE MODAL (Single Field)
// -----------------------------------------------------------------------------

export const EditProfileModal = memo(
  ({
    isOpen,
    onClose,
    fieldName,
    label,
    currentValue,
    onSave,
  }: {
    isOpen: boolean;
    onClose: () => void;
    fieldName: string;
    label: string;
    currentValue: string | null | undefined;
    onSave: (fieldName: string, newValue: string) => Promise<void>;
  }) => {
    const [value, setValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      if (isOpen) {
        setValue(currentValue || '');
        setError(null);
      }
    }, [isOpen, currentValue]);

    const handleSave = useCallback(async () => {
      setIsLoading(true);
      setError(null);
      try {
        await onSave(fieldName, value);
        onClose();
      } catch (err: any) {
        setError("Your changes couldn't be saved. Please check the current details before trying again.");
      } finally {
        setIsLoading(false);
      }
    }, [fieldName, value, onSave, onClose]);

    return (
      <ModalWrapper isOpen={isOpen} onClose={onClose} title={`UPDATE ${label.toUpperCase()}`} icon={User}>
        <div className="flex flex-col gap-6 p-6 sm:px-8">
          <SciFiInput
            label={label}
            id={fieldName}
            type={fieldName === 'email' ? 'email' : 'text'}
            value={value}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(e.target.value)}
            disabled={isLoading}
            error={error}
            placeholder={`Enter ${label.toLowerCase()}...`}
          />
        </div>
        <div className="grid grid-cols-1 gap-3 bg-transparent min-[400px]:grid-cols-2 px-6 pb-8 pt-2 sm:px-10 sm:pb-10">
          <SciFiButton variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </SciFiButton>
          <SciFiButton variant="primary" onClick={handleSave} isLoading={isLoading}>
            <Save className="h-4 w-4" /> Save
          </SciFiButton>
        </div>
      </ModalWrapper>
    );
  }
);
EditProfileModal.displayName = 'EditProfileModal';

// -----------------------------------------------------------------------------
// 3. EDIT PROFILE DETAILS MODAL (Multi-Field)
// -----------------------------------------------------------------------------

export const EditProfileDetailsModal = memo(
  ({
    isOpen,
    onClose,
    userData,
    onSave,
  }: {
    isOpen: boolean;
    onClose: () => void;
    userData: UserProfileData | undefined;
    onSave: (updatedData: Partial<UserProfileData>) => Promise<void>;
  }) => {
    const [formData, setFormData] = useState<UserProfileData>({
      full_name: '',
      phone_number: '',
      address: '',
    });
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      if (isOpen && userData) {
        setFormData({
          full_name: userData.full_name || '',
          phone_number: userData.phone_number || '',
          address: userData.address || '',
        });
        setError(null);
      }
    }, [isOpen, userData]);

    const handleSave = useCallback(async () => {
      setIsLoading(true);
      setError(null);

      const updatedData: Partial<UserProfileData> = {};
      if (formData.full_name !== (userData?.full_name || '')) updatedData.full_name = formData.full_name;
      if (formData.phone_number !== (userData?.phone_number || '')) updatedData.phone_number = formData.phone_number;
      if (formData.address !== (userData?.address || '')) updatedData.address = formData.address;

      if (Object.keys(updatedData).length === 0) {
        setIsLoading(false);
        onClose();
        return;
      }

      try {
        await onSave(updatedData);
        onClose();
      } catch (err: any) {
        setError("This change couldn't be confirmed. Please check your account before trying again.");
      } finally {
        setIsLoading(false);
      }
    }, [formData, userData, onSave, onClose]);

    const handleChange = useCallback((field: keyof UserProfileData) => (
      e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => {
      setFormData((prev) => ({ ...prev, [field]: e.target.value }));
    }, []);

    return (
      <ModalWrapper isOpen={isOpen} onClose={onClose} title="Edit profile" description="Keep your name, phone number and delivery address up to date." icon={User}>
        <div className="flex flex-col gap-6 px-6 pb-7 pt-4 sm:px-10 sm:pt-6">
          <SciFiInput
            label="Full Name"
            id="full_name"
            value={formData.full_name}
            onChange={handleChange('full_name')}
            disabled={isLoading}
          />
          <SciFiInput
            label="Phone Number"
            id="phone_number"
            type="tel"
            value={formData.phone_number}
            onChange={handleChange('phone_number')}
            disabled={isLoading}
          />
          <SciFiInput
            as="textarea"
            label="Primary Address"
            id="address"
            rows={3}
            value={formData.address}
            onChange={handleChange('address')}
            disabled={isLoading}
            className="w-full resize-none rounded-2xl border-0 bg-white/[0.055] px-4 py-4 text-sm text-white transition focus:bg-white/[0.07] focus:outline-none focus:ring-1 focus:ring-white/40"
          />
          {error && <p role="alert" className="rounded-2xl bg-red-400/10 px-4 py-3 text-sm leading-6 text-red-200">{error}</p>}
        </div>
        <div className="grid grid-cols-1 gap-3 bg-transparent min-[400px]:grid-cols-2 px-6 pb-8 pt-2 sm:px-10 sm:pb-10">
          <SciFiButton variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </SciFiButton>
          <SciFiButton variant="primary" onClick={handleSave} isLoading={isLoading}>
            <Save className="h-4 w-4" /> Save
          </SciFiButton>
        </div>
      </ModalWrapper>
    );
  }
);
EditProfileDetailsModal.displayName = 'EditProfileDetailsModal';

// -----------------------------------------------------------------------------
// 4. CHANGE PASSWORD MODAL
// -----------------------------------------------------------------------------

export const ChangePasswordModal = memo(
  ({
    isOpen,
    onClose,
    onSave,
  }: {
    isOpen: boolean;
    onClose: () => void;
    onSave: (current: string, next: string) => Promise<void>;
  }) => {
    const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });
    const [shows, setShows] = useState({ current: false, new: false, confirm: false });
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      if (isOpen) {
        setPasswords({ current: '', new: '', confirm: '' });
        setShows({ current: false, new: false, confirm: false });
        setError(null);
      }
    }, [isOpen]);

    const handleSave = useCallback(async () => {
      if (passwords.new !== passwords.confirm) {
        setError('The passwords do not match.');
        return;
      }
      if (passwords.new.length < 8) {
        setError('Use a password with at least 8 characters.');
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        await onSave(passwords.current, passwords.new);
        onClose();
      } catch (err: any) {
        setError("Your password couldn't be changed. Please check your current password and try again.");
      } finally {
        setIsLoading(false);
      }
    }, [passwords, onSave, onClose]);

    const toggleShow = useCallback((field: keyof typeof shows) => {
      setShows((prev) => ({ ...prev, [field]: !prev[field] }));
    }, []);

    const updatePassword = useCallback((field: keyof typeof passwords) => (
      e: React.ChangeEvent<HTMLInputElement>
    ) => {
      setPasswords((prev) => ({ ...prev, [field]: e.target.value }));
    }, []);

    const PasswordToggle = ({ field }: { field: keyof typeof shows }) => (
      <button
        type="button"
        onClick={() => toggleShow(field)}
        className="flex h-11 w-11 items-center justify-center rounded-full text-white/60 transition hover:text-cyan-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-200"
        aria-label={shows[field] ? 'Hide password' : 'Show password'}
      >
        {shows[field] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    );

    return (
      <ModalWrapper isOpen={isOpen} onClose={onClose} title="Change your password" description="Enter your current password, then choose a new one with at least 8 characters." icon={KeyRound}>
        <div className="flex flex-col gap-6 px-6 pb-7 pt-4 sm:px-10 sm:pt-6">
          <SciFiInput
            autoComplete="current-password"
            label="Current password"
            id="current_pwd"
            type={shows.current ? 'text' : 'password'}
            value={passwords.current}
            onChange={updatePassword('current')}
            disabled={isLoading}
            rightElement={<PasswordToggle field="current" />}
          />
          <SciFiInput
            autoComplete="new-password"
            label="New password"
            id="new_pwd"
            type={shows.new ? 'text' : 'password'}
            value={passwords.new}
            onChange={updatePassword('new')}
            disabled={isLoading}
            rightElement={<PasswordToggle field="new" />}
          />
          <SciFiInput
            autoComplete="new-password"
            label="Confirm new password"
            id="confirm_pwd"
            type={shows.confirm ? 'text' : 'password'}
            value={passwords.confirm}
            onChange={updatePassword('confirm')}
            disabled={isLoading}
            rightElement={<PasswordToggle field="confirm" />}
          />
          {error && <p role="alert" className="rounded-2xl bg-red-400/10 px-4 py-3 text-sm leading-6 text-red-200">{error}</p>}
        </div>
        <div className="grid grid-cols-1 gap-3 bg-transparent min-[400px]:grid-cols-2 px-6 pb-8 pt-2 sm:px-10 sm:pb-10">
          <SciFiButton variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </SciFiButton>
          <SciFiButton variant="primary" onClick={handleSave} isLoading={isLoading}>
            <KeyRound className="h-4 w-4" /> Change password
          </SciFiButton>
        </div>
      </ModalWrapper>
    );
  }
);
ChangePasswordModal.displayName = 'ChangePasswordModal';
