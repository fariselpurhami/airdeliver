// In apps/web/app/(main)/profile/page.tsx

"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import { Bot, LogOut, User } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

// --- Login Form Component ---
const LoginForm = () => {
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    // You can add more providers like "google"
    signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      callbackUrl: '/profile' // Redirect back to profile after login
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-md p-8 space-y-6 bg-gray-50 dark:bg-gray-900/50 rounded-lg shadow-xl border border-gray-200 dark:border-gray-800"
    >
      <div className="text-center">
        <h1 className="text-3xl font-bold">Sign In</h1>
        <p className="text-gray-500 dark:text-gray-400">Access your airdeliver dashboard</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            className="mt-1 block w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="mt-1 block w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
          />
        </div>
        <button
          type="submit"
          className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-bold text-white bg-black hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black dark:focus:ring-white transition-transform duration-300 hover:scale-105"
        >
          Sign In
        </button>
      </form>
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        Don't have an account?{' '}
        <Link href="/signup" className="font-medium text-primary hover:underline">
          Sign Up
        </Link>
      </p>
    </motion.div>
  );
};

// --- User Dashboard Component ---
const UserDashboard = ({ user }: { user: any }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-4xl"
    >
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold md:text-5xl">Welcome Back, {user.name || 'User'}</h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 mt-2">{user.email}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Order History Card */}
        <div className="p-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800">
          <h2 className="text-2xl font-bold mb-4">Your Orders</h2>
          <div className="text-center py-8 text-gray-500">
            <p>You have no recent orders.</p>
            <Link href="/products" className="mt-4 inline-block text-primary font-semibold hover:underline">
              Start Shopping
            </Link>
          </div>
        </div>

        {/* Profile Settings Card */}
        <div className="p-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800">
          <h2 className="text-2xl font-bold mb-4">Account</h2>
          <ul className="space-y-4">
            <li><Link href="/profile/settings" className="hover:text-primary transition-colors">Profile Settings</Link></li>
            <li><Link href="/profile/payment-methods" className="hover:text-primary transition-colors">Payment Methods</Link></li>
            <li>
              <button
                onClick={() => signOut()}
                className="flex items-center text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors font-semibold"
              >
                <LogOut size={18} className="mr-2" /> Sign Out
              </button>
            </li>
          </ul>
        </div>
      </div>
    </motion.div>
  );
};


// --- Main Profile Page ---
export default function ProfilePage() {
  const { data: session, status } = useSession();

  // Loading State
  if (status === "loading") {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // User is logged in
  if (session) {
    return (
      <div className="flex items-center justify-center py-12 md:py-24 px-4">
        <UserDashboard user={session.user} />
      </div>
    );
  }

  // User is not logged in
  return (
    <div className="flex items-center justify-center py-12 md:py-24 px-4">
      <LoginForm />
    </div>
  );
}
