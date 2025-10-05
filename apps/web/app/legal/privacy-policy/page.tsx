// In apps/web/app/legal/privacy-policy/page.tsx

import { ShieldCheck } from "lucide-react";

export default function PrivacyPolicyPage() {
  return (
    <>
      {/* 1️⃣ Hero Section */}
      <section className="relative flex items-center justify-center py-20 px-4 text-center text-white bg-gradient-to-r from-gray-900 via-gray-800 to-blue-900 dark:from-black dark:to-blue-950">
        <div className="z-10">
          <ShieldCheck size={48} className="mx-auto mb-4" />
          <h1 className="text-5xl font-extrabold tracking-tight md:text-6xl">Privacy Policy</h1>
          <p className="mt-4 text-lg text-gray-300">Your privacy is important to us.</p>
        </div>
      </section>

      {/* 2️⃣ Content Section */}
      <section className="px-4 py-16 md:py-24 bg-white dark:bg-gray-900">
        <div className="container mx-auto max-w-4xl prose prose-lg dark:prose-invert">
          
          <p className="lead">
            This Privacy Policy describes Our policies and procedures on the collection, use, and disclosure of Your information when You use the Service and tells You about Your privacy rights and how the law protects You.
          </p>

          <h2>1. Information We Collect</h2>
          <p>
            We collect several different types of information for various purposes to provide and improve our Service to you. This may include, but is not limited to, your name, email address, shipping address, and payment information. All personal data is handled with the utmost care and security.
          </p>

          <h2>2. How We Use Your Data</h2>
          <p>
            airdeliver uses the collected data for various purposes: to provide and maintain our Service, to notify you about changes to our Service, to allow you to participate in interactive features of our Service when you choose to do so, to provide customer support, to gather analysis or valuable information so that we can improve our Service, and to monitor the usage of our Service.
          </p>
          
          <h2>3. Data Storage and Security</h2>
          <p>
            The security of your data is important to us but remember that no method of transmission over the Internet or method of electronic storage is 100% secure. While we strive to use commercially acceptable means to protect your Personal Data, we cannot guarantee its absolute security.
          </p>
          
          <h2>4. Use of AI and Drones</h2>
          <p>
            Our AI ordering system processes your natural language requests to build your shopping cart. This data is used to improve the AI's accuracy and performance. Our drone delivery service may collect operational data, such as flight paths and delivery times, to ensure safety and efficiency. This data is anonymized and not linked to your personal account information.
          </p>

          <h2>5. Your Data Rights</h2>
          <p>
            You have the right to access, update, or delete the information we have on you. Whenever made possible, you can access, update, or request deletion of your Personal Data directly within your account settings section. If you are unable to perform these actions yourself, please contact us to assist you.
          </p>

          <h2>6. Contact Us</h2>
          <p>
            If you have any questions about this Privacy Policy, please contact us at: support@airdeliver.com
          </p>
          
        </div>
      </section>
    </>
  );
}
