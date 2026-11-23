# Demo image provenance pilot

The runtime override is deliberately OFF. No storefront route imports the review component yet. This branch is a review pilot, not a claim to have fixed every catalog image.

## Recommendation

Use merchant/owner-authorized exact SKU and variant photos for commercial listings. For this demo, a small, reviewed Commons-photo manifest is a legitimate way to show real product-family references with visible limits. Unknown items use neutral demo illustration. Never substitute a different model under an exact-product claim.

1. Require BOTH SKU pattern ADL-DEMO-v1-... and attributes._seed_dataset=airdeliver-demo-v1. Require known template identity too. No prefix-only, name-only or description-only matching.
2. Verify owner rows contain these markers before enabling. Current seed source writes them; the owner's current database has not been inspected.
3. Check source description, creator and license for each image. Download locally, pin SHA256, retain original source and license links and retrieval time. No runtime external fetch or hotlink.
4. Label family references next to image, not only in alt text. Include creator/source/license/change notice. Current pilot never calls anything an exact SKU photo.
5. Keep the review status candidate until owner review. Runtime enablement needs frontend integration on catalog, featured, overlay and product-details surfaces, metadata propagation and regression checks. Do not enable on one surface while another silently drops attribution.
6. Add explicit copyright exceptions for these assets in any distribution: photos retain CC-BY-SA-4.0, not the repository's proprietary license. Resized/adapted photo derivatives retain the same license. This license does not apply to the surrounding application merely because it displays a photo collection.

## Pilot assessment

- Adidas Samba photograph by Pangalau shows a real black Samba. Family match supported by source and visual inspection; exact commercial SKU, size, year and authenticity are not independently certified.
- Jordan Royal photograph by HI 622 shows blue/black high-top Jordans. Filename says 2016 while description says 2017. This contradiction is retained and disqualifies exact model-year matching. Family-reference only, not every synthetic variant. Not a studio photograph.
- Royal Oak Offshore was rejected as an exact Royal Oak image. MacBook Air was rejected for MacBook Pro M4 Max. Older purple Samba and dark on-foot Jordan candidates rejected for quality and mismatch. Neutral illustration shown for the watch in the review preview.

The manifest has qualitative match confidence, not a misleading calibrated numeric probability. Source licenses supply copyright permissions, not blanket trademark, endorsement, authenticity, privacy or commercial-use clearance. Commons supplies no warranty. This is not legal advice.

## Licenses and sources checked 2026-11-23

- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- https://commons.wikimedia.org/wiki/File:Adidas_Samba.jpg
- https://commons.wikimedia.org/wiki/File:Air_Jordan_Royal_blue_2016.jpg
- https://creativecommons.org/licenses/by-sa/4.0/
- https://unsplash.com/license
- https://help.unsplash.com/en/articles/14224409-what-if-there-is-a-brand-logo-in-an-image-on-unsplash
- https://www.pexels.com/license/
- https://help.pexels.com/hc/en-us/articles/900005880463-What-are-the-Terms-and-Conditions

Unsplash permits broad copyright reuse but explicitly excludes brand/logo rights. Pexels permits website use, prohibits implied endorsement and limits systematic collection. Neither is a shortcut to exact product accuracy. Commons chosen for per-file provenance and explicit reusable-license evidence. No API key or paid account required for these two bounded downloads. No seeding, DB write, provider call or deployment.
