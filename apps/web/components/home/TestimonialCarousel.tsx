'use client';

// 1. قم باستيراد الأدوات الأساسية من React
import React, { useState, useEffect } from 'react';
import useEmblaCarousel from 'embla-carousel-react';
import Autoplay from 'embla-carousel-autoplay';

const TestimonialCarousel = ({ testimonials }) => {
  // الآن، سيعمل هذا الكود بنجاح
  const [isClient, setIsClient] = useState(false);
  const [emblaRef] = useEmblaCarousel({ loop: true }, [Autoplay()]);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return null; //  يعرض لا شيء حتى يتم تحميل المكون على جانب العميل
  }

  return (
    <div className="overflow-hidden" ref={emblaRef}>
      <div className="flex">
        {testimonials.map((testimonial) => (
          <div className="flex-grow-0 flex-shrink-0 w-full md:w-1/2 lg:w-1/3 p-4" key={testimonial.author}>
            <div className="h-full p-8 bg-gray-100 dark:bg-gray-800 rounded-lg shadow-inner flex flex-col">
              <p className="flex-grow italic text-gray-600 dark:text-gray-300">"{testimonial.quote}"</p>
              <div className="flex items-center mt-6">
                <div className="w-12 h-12 rounded-full bg-primary text-white flex items-center justify-center font-bold text-xl mr-4">
                  {testimonial.initials}
                </div>
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white">{testimonial.author}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">{testimonial.title}</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TestimonialCarousel;
