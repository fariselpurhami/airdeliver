// file: apps/web/app/(main)/page.tsx

"use client";

import React from 'react';
import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Bot, CreditCard, MapPin, Rocket, Zap, Facebook, Twitter, Instagram, Linkedin } from "lucide-react";
import { motion } from 'framer-motion';
import useEmblaCarousel from 'embla-carousel-react';
import Autoplay from 'embla-carousel-autoplay';
import { useAIOrderingStore } from '@/hooks/useAIOrdering'; // Import the correct AI ordering store

// --- Reusable Components for Cleanliness and Modularity ---

interface BenefitCardProps {
  icon: React.ReactNode;
  title: string;
  isEmphasized?: boolean;
  children: React.ReactNode;
}

const BenefitCard = ({ icon, title, isEmphasized = false, children }: BenefitCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 50 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, amount: 0.3 }}
    transition={{ duration: 0.6 }}
    className={`relative flex flex-col items-center p-8 text-center bg-gray-50 dark:bg-gray-800/50 rounded-xl shadow-sm hover:shadow-xl dark:hover:shadow-primary/20 transition-all duration-300 group ${isEmphasized ? 'lg:scale-105 border-2 border-primary/50 dark:bg-primary/10' : ''}`}
  >
    <div className="mb-5 text-primary transition-transform duration-300 group-hover:scale-110">
      {icon}
    </div>
    <h3 className="mb-2 text-xl font-bold">{title}</h3>
    <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{children}</p>
  </motion.div>
);

interface Testimonial {
  quote: string;
  author: string;
  title: string;
  initials: string;
}

const TestimonialCarousel = ({ testimonials }: { testimonials: Testimonial[] }) => {
  const [emblaRef] = useEmblaCarousel({ loop: true }, [Autoplay({ delay: 5000 })]);

  return (
    <div className="overflow-hidden" ref={emblaRef}>
      <div className="flex">
        {testimonials.map((testimonial, index) => (
          <div className="flex-grow-0 flex-shrink-0 w-full md:w-1/2 lg:w-1/3 p-4" key={index}>
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="h-full p-8 bg-gray-100 dark:bg-gray-800 rounded-lg shadow-inner flex flex-col"
            >
              <p className="flex-grow italic text-gray-600 dark:text-gray-300 text-base">"{testimonial.quote}"</p>
              <div className="flex items-center mt-6">
                <div className="w-12 h-12 rounded-full bg-primary text-white flex items-center justify-center font-bold text-xl mr-4">
                  {testimonial.initials}
                </div>
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white">{testimonial.author}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">{testimonial.title}</div>
                </div>
              </div>
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface Partner {
  name: string;
  logo: string;
}

const PartnerLogo = ({ partner }: { partner: Partner }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, amount: 0.5 }}
    transition={{ duration: 0.5 }}
    className="filter grayscale hover:grayscale-0 transition-all duration-300 p-2"
  >
    {/* Using a span for text, assuming placeholder logo is text for now */}
    <span className="text-2xl font-medium text-gray-400">{partner.name}</span>
    {/* If you have actual image logos, use this instead: */}
    {/* <Image src={partner.logo} alt={partner.name} width={120} height={60} className="object-contain" /> */}
  </motion.div>
);


// --- Main Home Page Component ---

export default function HomePage() {
  const { setOverlayVisible } = useAIOrderingStore(); // Get the function to open the AI chat overlay
  
  const testimonials: Testimonial[] = [
    { quote: "I ordered groceries while on a work call, and they arrived before the call ended. Airdeliver is magic.", author: "Sarah L.", title: "Busy Professional", initials: "SL" },
    { quote: "The AI understood exactly what I meant by 'snacks for movie night'. It's scary good.", author: "Mike R.", title: "Tech Enthusiast", initials: "MR" },
    { quote: "Tracking the little drone on the map is the best part! My kids love watching it arrive.", author: "Jenna P.", title: "Parent & Home Manager", initials: "JP" },
    { quote: "Finally, a delivery service that feels like it's from the future. The speed is unbelievable.", author: "David Chen", title: "Early Adopter", initials: "DC" },
  ];
  
  const partners: Partner[] = [
    { name: "PartnerCo", logo: "/placeholder-logo.svg" },
    { name: "Innovate Inc.", logo: "/placeholder-logo.svg" },
    { name: "Future Corp", logo: "/placeholder-logo.svg" },
    { name: "LogiTech", logo: "/placeholder-logo.svg" },
    { name: "Venture Global", logo: "/placeholder-logo.svg" },
  ];

  return (
    <>
      {/* 1️⃣ Hero Section */}
      <section className="relative flex items-center justify-center min-h-screen px-4 text-center py-24 overflow-hidden bg-gradient-to-br from-black via-gray-950 to-blue-950">
        {/* Subtle Futuristic Grid Background */}
        <div className="absolute inset-0 z-0 opacity-20 dark:opacity-10">
          <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-gray-700 dark:text-gray-800"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>

        {/* Hero Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="z-10 max-w-5xl"
        >
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg font-semibold tracking-wider text-gray-600 dark:text-primary uppercase mb-4 animate-fade-in-up"
          >
            Autonomous AI + Drones. Built for Tomorrow
          </motion.h2>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4 }}
            className="text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl text-white drop-shadow-lg leading-tight"
          >
            The Future of Delivery is Here
          </motion.h1>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-6"
          >
            <button
              onClick={() => setOverlayVisible(true)} // Open AI chat on click
              className="group inline-flex items-center justify-center w-full sm:w-auto px-10 py-5 text-xl font-bold text-black bg-white rounded-full shadow-lg hover:bg-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-white dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90 dark:focus-visible:ring-primary transition-all duration-300 hover:scale-105"
              aria-label="Start an order with AI"
            >
              Order with AI <Bot className="ml-3 h-7 w-7 transition-transform group-hover:rotate-12" />
            </button>
            <Link
              href="/products"
              className="inline-flex items-center justify-center w-full sm:w-auto px-10 py-5 text-xl font-semibold text-gray-100 bg-transparent border-2 border-white/50 rounded-full hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-white transition-colors duration-300"
              aria-label="Browse all products"
            >
              Shop Now <ArrowRight className="ml-3 h-6 w-6" />
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* 2️⃣ Value Proposition Section (Why Us / Benefits) */}
      <section className="px-4 py-20 md:py-32 bg-white dark:bg-gray-900">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl mx-auto mb-16 text-center"
          >
            <h2 className="text-4xl font-bold tracking-tight md:text-5xl text-gray-900 dark:text-white mb-6">An Unparalleled Experience</h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
              We leverage cutting-edge AI + drones to provide a delivery experience unlike any other, redefining speed, convenience, and reliability.
            </p>
          </motion.div>
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
            <BenefitCard icon={<Rocket size={40} />} title="Unmatched Speed" isEmphasized={true}>
              Delivery in minutes — not days. Our autonomous drone network gets your items to you faster than ever before.
            </BenefitCard>
            <BenefitCard icon={<Bot size={40} />} title="AI Intelligence">
              Your personal AI shopper understands your needs, building your cart from a single sentence or complex request.
            </BenefitCard>
            <BenefitCard icon={<CreditCard size={40} />} title="Seamless Payments">
              Global payment orchestration ensures you can pay your way, securely and effortlessly, every time.
            </BenefitCard>
            <BenefitCard icon={<MapPin size={40} />} title="Total Transparency">
              Live drone tracking and real-time updates give you total visibility and peace of mind from order to delivery.
            </BenefitCard>
          </div>
        </div>
      </section>

      {/* 3️⃣ Demo Section (See AI in Action) */}
      <section className="px-4 py-20 md:py-32 bg-gray-50 dark:bg-black/50">
        <div className="container mx-auto text-center max-w-5xl">
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.6 }}
            className="text-4xl font-bold tracking-tight md:text-5xl mb-12 text-gray-900 dark:text-white"
          >
            See AI in Action
          </motion.h2>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.7 }}
            className="relative w-full aspect-video max-w-4xl mx-auto bg-black rounded-xl shadow-2xl overflow-hidden ring-1 ring-white/10"
          >
            {/* Placeholder for animated GIF or video */}
            <Image
              src="/ai-demo-placeholder.gif" // Make sure you have this GIF in your public folder
              alt="Animated demo of AI ordering"
              fill
              className="object-cover"
              unoptimized={true} // Important for GIFs
            />
          </motion.div>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-8 text-xl text-gray-700 dark:text-gray-300 max-w-2xl mx-auto"
          >
            Request any item in one sentence. Let AI + drones handle the rest.
          </motion.p>
        </div>
      </section>

      {/* 4️⃣ Social Proof Section (Trust & Testimonials) */}
      <section className="px-4 py-20 md:py-32 bg-white dark:bg-gray-900">
        <div className="container mx-auto max-w-6xl">
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.6 }}
            className="mb-16 text-4xl font-bold text-center md:text-5xl text-gray-900 dark:text-white"
          >
            Trusted by Users Worldwide
          </motion.h2>
          <TestimonialCarousel testimonials={testimonials} />
          <div className="mt-24 text-center">
            <motion.h3
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.5 }}
              transition={{ duration: 0.5 }}
              className="text-sm font-semibold tracking-wider text-gray-500 uppercase dark:text-gray-400 mb-10"
            >
              Powering the next generation of logistics
            </motion.h3>
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true, amount: 0.5 }}
              transition={{ duration: 0.7 }}
              className="flex flex-wrap items-center justify-center max-w-5xl mx-auto mt-8 gap-x-16 gap-y-10"
            >
              {partners.map((partner) => (
                <PartnerLogo key={partner.name} partner={partner} />
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* 5️⃣ Final CTA Section */}
      <section className="px-4 py-24 text-center bg-gradient-to-r from-gray-900 via-gray-800 to-blue-900 dark:from-black dark:via-gray-950 dark:to-blue-950">
        <div className="container mx-auto max-w-4xl">
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.7 }}
            className="text-4xl font-bold text-white md:text-5xl mb-10 leading-tight"
          >
            Ready to Experience AI Delivery?
          </motion.h2>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Link
              href="/ai-order" // This Link can stay as it might eventually lead to a dedicated AI order page or pre-fill the chat
              className="group inline-flex items-center justify-center px-12 py-6 mt-8 text-2xl font-bold text-black bg-white rounded-full shadow-lg hover:bg-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-white dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90 dark:focus-visible:ring-primary transition-transform duration-300 hover:scale-105"
              aria-label="Start your first AI order now"
            >
              <Zap className="mr-4 h-7 w-7 transition-transform group-hover:rotate-[-15deg]" />
              Start Your First AI Order Now
            </Link>
          </motion.div>
        </div>
      </section>
    </>
  );
}
