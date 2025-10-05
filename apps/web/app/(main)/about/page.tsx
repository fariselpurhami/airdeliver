// In apps/web/app/(main)/about/page.tsx

import { Award, Target, Users } from "lucide-react";
import Link from "next/link";
import Image from "next/image";

// Helper component for Mission/Vision cards
const InfoCard = ({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) => (
  <div className="p-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg shadow-sm">
    <div className="flex items-center mb-4">
      <div className="mr-4 text-primary">{icon}</div>
      <h3 className="text-2xl font-bold">{title}</h3>
    </div>
    <p className="text-gray-600 dark:text-gray-400 leading-relaxed">{children}</p>
  </div>
);

// Helper component for Team Member cards
const TeamMemberCard = ({ name, role, imageUrl }: { name: string; role: string; imageUrl: string }) => (
  <div className="text-center">
    <div className="relative w-40 h-40 mx-auto mb-4">
      <Image
        src={imageUrl}
        alt={`Photo of ${name}`}
        fill
        className="object-cover rounded-full"
        // Placeholder for blur effect
        placeholder="blur"
        blurDataURL="data:image/gif;base64,R0lGODlhAQABAIAAAMLCwgAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw=="
      />
    </div>
    <h4 className="text-xl font-semibold text-gray-900 dark:text-white">{name}</h4>
    <p className="text-primary">{role}</p>
  </div>
);


export default function AboutPage() {
  return (
    <>
      {/* 1️⃣ Hero Section */}
      <section className="relative flex items-center justify-center py-24 px-4 text-center text-white bg-gradient-to-r from-gray-900 via-gray-800 to-blue-900 dark:from-black dark:to-blue-950">
        <div className="z-10">
          <h1 className="text-5xl font-extrabold tracking-tight md:text-7xl">About airdeliver</h1>
          <p className="mt-4 text-lg md:text-xl text-gray-300 max-w-2xl mx-auto">
            We are redefining the entire logistics ecosystem, one drone at a time.
          </p>
        </div>
      </section>

      {/* 2️⃣ Story / Mission Section */}
      <section className="px-4 py-16 md:py-24 bg-white dark:bg-gray-900">
        <div className="container mx-auto max-w-4xl text-lg text-center text-gray-700 dark:text-gray-300 leading-relaxed">
          <p className="mb-6">
            Customers waste hours waiting for deliveries every day. airdeliver eliminates that wait by combining a cutting-edge eCommerce platform with a fully autonomous, AI-driven fleet of delivery drones. Our technology ensures packages reach their destination faster, safer, and more efficiently than any traditional delivery method.
          </p>
          <p>
            We serve urban centers and remote locations alike, providing unparalleled coverage, precision, and reliability. By leveraging advanced routing algorithms, real-time tracking, and automated fleet management, we are not just moving packages—we're redefining the future of commerce.
          </p>
        </div>
      </section>

      {/* 3️⃣ Mission & Vision Section */}
      <section className="px-4 py-16 md:py-24 bg-gray-50 dark:bg-black/50">
        <div className="container mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl">
          <InfoCard icon={<Target size={32} />} title="Our Mission">
            Our mission is simple: deliver instant, seamless, and sustainable logistics worldwide. We are committed to innovation, environmental responsibility, and exceptional customer experience.
          </InfoCard>
          <InfoCard icon={<Award size={32} />} title="Our Vision">
            To build a fully autonomous delivery network that makes goods and services accessible to anyone, anywhere, instantly.
          </InfoCard>
        </div>
      </section>

      {/* 4️⃣ Team Section */}
      <section className="px-4 py-16 md:py-24 bg-white dark:bg-gray-900">
        <div className="container mx-auto text-center">
          <h2 className="text-4xl font-bold tracking-tight md:text-5xl mb-12">Meet the Innovators</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8 max-w-5xl mx-auto">
            {/* Replace with your actual team members */}
            <TeamMemberCard name="Faris Elpurhami" role="Founder & CEO" imageUrl="/team-placeholder-1.jpg" />
            <TeamMemberCard name="Maria Garcia" role="Head of AI" imageUrl="/team-placeholder-2.jpg" />
            <TeamMemberCard name="Chen Wei" role="Lead Robotics Engineer" imageUrl="/team-placeholder-3.jpg" />
            <TeamMemberCard name="Samira Khan" role="Head of Operations" imageUrl="/team-placeholder-4.jpg" />
          </div>
        </div>
      </section>

      {/* 5️⃣ Final CTA Section */}
      <section className="px-4 py-20 text-center bg-gray-900 dark:bg-gray-950">
        <div className="container mx-auto">
          <h2 className="text-4xl font-bold text-white md:text-5xl">
            Join Us as We Transform the Future of Commerce.
          </h2>
          <Link
            href="/products"
            className="inline-flex items-center justify-center px-8 py-4 mt-8 text-lg font-bold text-black bg-white rounded-full shadow-lg hover:bg-gray-200 transition-transform duration-300 hover:scale-105"
            aria-label="Browse all products"
          >
            Shop Now
          </Link>
        </div>
      </section>
    </>
  );
}
