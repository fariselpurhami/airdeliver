import { ProductList } from "@/components/products/ProductList";
import { ShoppingBag } from "lucide-react";

interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string;
}

async function getProducts(): Promise<Product[]> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/products/`, { cache: 'no-store' });
    if (!res.ok) {
      console.error('Failed to fetch products:', res.statusText);
      return [];
    }
    return res.json();
  } catch (error) {
    console.error('API Fetch Error (Products Page):', error);
    return [];
  }
}

export default async function ProductsPage() {
  const products = await getProducts();

  return (
    <>
      {/* 1️⃣ Hero Section - NOW UPDATED */}
      <section className="py-20 px-4 text-center text-white bg-gradient-to-r from-gray-900 via-gray-800 to-blue-900 dark:from-black dark:to-blue-950">
        <ShoppingBag size={48} className="mx-auto mb-4" />
        <h1 className="text-5xl font-extrabold tracking-tight md:text-6xl">All Products</h1>
        <p className="mt-4 text-lg text-gray-300 max-w-2xl mx-auto">
          Browse our collection of cutting-edge drones and accessories.
        </p>
      </section>

      {/* 2️⃣ Products Grid Section */}
      <section className="px-4 py-16 md:py-24 bg-white dark:bg-gray-900">
        <div className="container mx-auto">
          {products.length === 0 ? (
            <div className="text-center py-10">
              <p className="text-gray-500">Could not load products at the moment.</p>
              <p className="text-sm text-gray-400">Please ensure the backend server is running and the database is populated.</p>
            </div>
          ) : (
            <ProductList products={products} />
          )}
        </div>
      </section>
    </>
  );
}
