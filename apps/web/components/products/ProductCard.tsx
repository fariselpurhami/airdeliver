'use client';

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { useCartStore } from "@/hooks/useCartStore";

interface Product {
  id: number;
  name: string;
  price: number;
  image_url: string;
  description?: string; // Optional description
  inventory?: number; // Optional inventory
}

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  const { addItem } = useCartStore();

  return (
    <motion.div
      className="relative group overflow-hidden border border-gray-200 dark:border-gray-800 rounded-lg shadow-sm"
      whileHover={{ y: -5 }}
      transition={{ duration: 0.3 }}
    >
      <Link href={`/product/${product.id}`} className="block">
        <div className="aspect-square w-full bg-gray-100 dark:bg-gray-800">
          <Image
            src={product.image_url}
            alt={product.name}
            width={400}
            height={400}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            placeholder="blur"
            blurDataURL="data:image/gif;base64,R0lGODlhAQABAIAAAMLCwgAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw=="
          />
        </div>
        <div className="p-4 bg-background">
          <h3 className="font-semibold text-lg truncate">{product.name}</h3>
          <p className="text-foreground/80">${product.price.toFixed(2)}</p>
        </div>
      </Link>
      <div className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <Button onClick={() => addItem({ ...product, quantity: 1 })} variant="secondary">
          Add to Cart
        </Button>
      </div>
    </motion.div>
  );
}
