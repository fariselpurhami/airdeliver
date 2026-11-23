import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { CatalogImage } from '@/components/products/CatalogImage';
jest.mock('next/image',()=>({__esModule:true,default:({unoptimized,fill,priority,...props}:any)=><img {...props}/>}));
it('keeps source then uses local accessible fallback once on error',()=>{
 const {rerender}=render(<CatalogImage src="https://images.unsplash.com/photo-demo" alt="Catalog shoe" width={240} height={180}/>);
 const image=screen.getByRole('img');
 expect(image).toHaveAttribute('src','https://images.unsplash.com/photo-demo');
 fireEvent.error(image);
 expect(image).toHaveAttribute('src','/images/catalog-placeholder.svg');
 expect(image).toHaveAttribute('alt','Catalog shoe. Image unavailable.');
 fireEvent.error(image);expect(image).toHaveAttribute('src','/images/catalog-placeholder.svg');
 rerender(<CatalogImage src="https://images.unsplash.com/new" alt="New shoe" width={240} height={180}/>);
 expect(image).toHaveAttribute('src','https://images.unsplash.com/new');
});
it('empty source never loads a missing default.jpeg',()=>{
 const {container}=render(<CatalogImage src={null} alt="Catalog item" width={240} height={180}/>);
 expect(screen.getByRole('img')).toHaveAttribute('src','/images/catalog-placeholder.svg');
 if(process.env.IMAGE_PREVIEW_HTML) require('fs').writeFileSync(process.env.IMAGE_PREVIEW_HTML,'<!doctype html><html><body style="margin:0;background:#0b1019;color:white;font:18px Arial;padding:32px"><h1>Catalog image unavailable</h1><p>A truthful local fallback, no substitute product photo.</p>'+container.innerHTML+'</body></html>');
});
