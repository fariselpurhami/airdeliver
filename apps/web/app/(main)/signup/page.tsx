// In apps/web/app/(main)/signup/page.tsx

"use client";

import { signIn } from "next-auth/react";
import Link from "next/link";
import { motion } from "framer-motion";
import { UserPlus } from "lucide-react";

export default function SignUpPage() {
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    // --- TODO: Implement your sign-up API call here ---
    // This is a placeholder. You'll need to create an API endpoint
    // that creates a new user and then signs them in.
    console.log("Submitting sign-up form...");
    console.log("Full Name:", formData.get("fullName"));
    console.log("Email:", formData.get("email"));

    // For now, we'll just log the data.
    // In a real app, you would POST to '/api/v1/users/' or similar,
    // then call signIn() upon success.
  };

  return (
    <div className="flex items-center justify-center py-12 md:py-24 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md p-8 space-y-6 bg-gray-50 dark:bg-gray-900/50 rounded-lg shadow-xl border border-gray-200 dark:border-gray-800"
      >
        <div className="text-center">
          <UserPlus size={40} className="mx-auto mb-4 text-primary" />
          <h1 className="text-3xl font-bold">Create an Account</h1>
          <p className="text-gray-500 dark:text-gray-400">Join Us</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Full Name
            </label>
            <input
              id="fullName"
              name="fullName"
              type="text"
              autoComplete="name"
              required
              className="mt-1 block w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
            />
          </div>
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
              autoComplete="new-password"
              required
              className="mt-1 block w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
            />
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-bold text-white bg-black hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black dark:focus:ring-white transition-transform duration-300 hover:scale-105"
          >
            Sign Up
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 dark:text-gray-400">
          Already have an account?{' '}
          <Link href="/profile" className="font-medium text-primary hover:underline">
            Sign In
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
