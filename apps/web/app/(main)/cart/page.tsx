// In apps/web/app/(main)/cart/page.tsx

"use client";

import { useCartStore } from "@/hooks/useCartStore";
import Image from "next/image";
import Link from "next/link";
import { CreditCard, Minus, Plus, ShoppingCart, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function CartPage() {
  const { items, removeItem, updateItemQuantity, clearCart } = useCartStore();

  const subtotal = items.reduce((acc, item) => acc + item.price * item.quantity, 0);
  const shippingFee = subtotal > 0 ? 15.00 : 0; // Example shipping fee
  const total = subtotal + shippingFee;

  return (
    <>
      {/* 1️⃣ Hero Section */}
      <section className="py-20 px-4 text-center text-white bg-gradient-to-r from-gray-900 via-gray-800 to-blue-900 dark:from-black dark:to-blue-950">
        <ShoppingCart size={48} className="mx-auto mb-4" />
        <h1 className="text-5xl font-extrabold tracking-tight md:text-6xl">Your Cart</h1>
        <p className="mt-4 text-lg text-gray-300 max-w-2xl mx-auto">
          Review your items and proceed to checkout.
        </p>
      </section>

      {/* 2️⃣ Cart Content Section */}
      <section className="px-4 py-16 md:py-24 bg-white dark:bg-gray-900">
        <div className="container mx-auto max-w-6xl">
          <AnimatePresence>
            {items.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-16"
              >
                <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-300">Your cart is empty.</h2>
                <Link
                  href="/products"
                  className="inline-flex items-center justify-center px-6 py-3 mt-6 text-lg font-bold text-white bg-black rounded-full shadow-lg hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200 transition-transform duration-300 hover:scale-105"
                >
                  Start Shopping
                </Link>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 lg:grid-cols-3 gap-12"
              >
                {/* Cart Items List (Left Column) */}
                <div className="lg:col-span-2 space-y-6">
                  {items.map(item => (
                    <motion.div
                      layout
                      initial={{ opacity: 0, x: -50 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -50, transition: { duration: 0.3 } }}
                      key={item.id}
                      className="flex items-center gap-6 p-4 border border-gray-200 dark:border-gray-800 rounded-lg"
                    >
                      <Image src={item.image_url} alt={item.name} width={100} height={100} className="rounded-md object-cover aspect-square" />
                      <div className="flex-grow">
                        <h3 className="font-bold text-lg">{item.name}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">${item.price.toFixed(2)}</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <button onClick={() => updateItemQuantity(item.id, item.quantity - 1)} disabled={item.quantity <= 1} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50">
                          <Minus size={16} />
                        </button>
                        <span className="font-semibold w-8 text-center">{item.quantity}</span>
                        <button onClick={() => updateItemQuantity(item.id, item.quantity + 1)} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800">
                          <Plus size={16} />
                        </button>
                      </div>
                      <p className="font-bold w-24 text-right">${(item.price * item.quantity).toFixed(2)}</p>
                      <button onClick={() => removeItem(item.id)} className="p-2 text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition-colors">
                        <Trash2 size={20} />
                      </button>
                    </motion.div>
                  ))}
                </div>

                {/* Order Summary (Right Column) */}
                <div className="lg:col-span-1">
                  <div className="sticky top-28 p-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-800">
                    <h2 className="text-2xl font-bold mb-6 border-b pb-4 dark:border-gray-700">Order Summary</h2>
                    <div className="space-y-4">
                      <div className="flex justify-between">
                        <span>Subtotal</span>
                        <span>${subtotal.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Shipping Fee</span>
                        <span>${shippingFee.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-xl font-bold mt-4 pt-4 border-t dark:border-gray-700">
                        <span>Total</span>
                        <span>${total.toFixed(2)}</span>
                      </div>
                    </div>
                    <Link
                      href="/checkout"
                      className="mt-8 group w-full inline-flex items-center justify-center px-8 py-4 text-lg font-bold text-white bg-black rounded-full shadow-lg hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200 transition-transform duration-300 hover:scale-105"
                    >
                      Proceed to Checkout <CreditCard className="ml-3 h-6 w-6" />
                    </Link>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>
    </>
  );
}
