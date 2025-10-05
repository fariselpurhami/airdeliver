// In apps/web/app/legal/terms-of-service/page.tsx

import { FileText } from "lucide-react";

export default function TermsOfServicePage() {
  return (
    <>
      {/* 1️⃣ Hero Section */}
      <section className="relative flex items-center justify-center py-20 px-4 text-center text-white bg-gradient-to-r from-gray-900 via-gray-800 to-blue-900 dark:from-black dark:to-blue-950">
        <div className="z-10">
          <FileText size={48} className="mx-auto mb-4" />
          <h1 className="text-5xl font-extrabold tracking-tight md:text-6xl">Terms of Service</h1>
          <p className="mt-4 text-lg text-gray-300">Last updated: October 3, 2025</p>
        </div>
      </section>

      {/* 2️⃣ Content Section */}
      <section className="px-4 py-16 md:py-24 bg-white dark:bg-gray-900">
        {/* The 'prose' classes apply the beautiful typography styles */}
        <div className="container mx-auto max-w-4xl prose prose-lg dark:prose-invert">
          
          <h2>1. Introduction</h2>
          <p>
            Welcome to airdeliver ("Company", "we", "our", "us")! These Terms of Service ("Terms") govern your use of our website located at airdeliver.com (together or individually "Service") operated by airdeliver. Our Privacy Policy also governs your use of our Service and explains how we collect, safeguard, and disclose information that results from your use of our web pages.
          </p>

          <h2>2. Using Our Service</h2>
          <p>
            You agree to use the Service only for lawful purposes and in a way that does not infringe the rights of, restrict, or inhibit anyone else's use and enjoyment of the Service. Prohibited behavior includes harassing or causing distress or inconvenience to any other user, transmitting obscene or offensive content, or disrupting the normal flow of dialogue within our Service.
          </p>
          
          <h2>3. AI Ordering and Drone Delivery</h2>
          <p>
            Our Service includes an AI-powered ordering system and an autonomous drone delivery network. By placing an order, you agree to provide accurate and complete information. All deliveries are subject to weather conditions, airspace regulations, and operational capacity. We reserve the right to cancel or delay any delivery for safety or regulatory reasons.
          </p>
          
          <h2>4. Accounts</h2>
          <p>
            When you create an account with us, you guarantee that you are above the age of 18 and that the information you provide us is accurate, complete, and current at all times. Inaccurate, incomplete, or obsolete information may result in the immediate termination of your account on our Service.
          </p>

          <h2>5. Limitation of Liability</h2>
          <p>
            In no event shall airdeliver, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your access to or use of or inability to access or use the Service.
          </p>

          <h2>6. Changes to Terms</h2>
          <p>
            We reserve the right, at our sole discretion, to modify or replace these Terms at any time. If a revision is material we will provide at least 30 days' notice prior to any new terms taking effect. What constitutes a material change will be determined at our sole discretion.
          </p>

          <h2>7. Contact Us</h2>
          <p>
            If you have any questions about these Terms, please contact us at: support@airdeliver.com.
          </p>
          
        </div>
      </section>
    </>
  );
}
