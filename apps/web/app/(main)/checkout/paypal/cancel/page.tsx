import Link from 'next/link';
export default function PayPalCancel() {
  return <section className="mx-auto max-w-xl px-6 py-16 text-white">
    <h1 className="text-3xl mb-5">PayPal approval canceled</h1>
    <p className="mb-5 text-slate-300">No payment was requested by this return page. An existing order is not automatically canceled. Check your orders before trying another checkout.</p>
    <Link href="/profile" className="text-cyan-300 underline">Review orders in your profile</Link>
  </section>;
}
