// file: apps/web/components/layout/Footer.tsx
// version: 1.1.0 (Social Media Icons)
// date: 2025-09-28
// author: Gemini

import Link from 'next/link';
import Image from 'next/image';
//import { Chatbot } from '../ai/Chatbot';
import {
  FiInstagram,
  FiFacebook,
  FiYoutube,
} from 'react-icons/fi';
import { FaTiktok } from 'react-icons/fa';
import { RiTwitterXFill } from 'react-icons/ri';

// Define our social media links in an array for easy management
const socialLinks = [
  { name: 'Facebook', href: '#', icon: FiFacebook },
  { name: 'Instagram', href: '#', icon: FiInstagram },
  { name: 'X (Twitter)', href: '#', icon: RiTwitterXFill },
  { name: 'YouTube', href: '#', icon: FiYoutube },
  { name: 'TikTok', href: '#', icon: FaTiktok },
];

const Footer = () => {
  return (
    <>
      <footer className="border-t mt-12 py-8 bg-background">
        <div className="container mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Company Info */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl font-bold">airdeliver</span>
            </div>
            <p className="text-sm text-foreground/60 italic">
              We Soar In The Sky By Delivering Your Orders.
            </p>
          </div>
          
          {/* Shop Links */}
          <div>
            <h3 className="font-semibold mb-2">Shop</h3>
            <ul className="space-y-1 text-sm text-foreground/80">
              <li><Link href="/products" className="hover:underline">All Products</Link></li>
              <li><Link href="/products?category=drones" className="hover:underline">Drones</Link></li>
              <li><Link href="/products?category=accessories" className="hover:underline">Accessories</Link></li>
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h3 className="font-semibold mb-2">Company</h3>
            <ul className="space-y-1 text-sm text-foreground/80">
              <li><Link href="/about" className="hover:underline">About Us</Link></li>
              <li><Link href="/legal/terms-of-service" className="hover:underline">Terms of Service</Link></li>
              <li><Link href="/legal/privacy-policy" className="hover:underline">Privacy Policy</Link></li>
            </ul>
          </div>

          {/* Follow Us Section */}
          <div>
            <h3 className="font-semibold mb-4">Follow Us</h3>
            <div className="flex items-center gap-4">
              {socialLinks.map((social) => (
                <Link
                  key={social.name}
                  href={social.href}
                  aria-label={social.name}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground/70 hover:text-foreground transition-colors"
                >
                  <social.icon size={22} />
                </Link>
              ))}
            </div>
          </div>
        </div>
        <div className="text-center mt-8 text-xs text-foreground/50">
          © {new Date().getFullYear()} airdeliver Inc. All rights reserved.
        </div>
      </footer>
      {/* The chatbot is kept here to float above everything */}
      
    </>
  );
};

export default Footer;
