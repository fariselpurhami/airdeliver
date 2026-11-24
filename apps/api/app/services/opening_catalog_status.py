"""Read-only current SQL classification, never relabel or create offers."""
from sqlalchemy import text

async def opening_catalog_status(db,recent_ids):
    result=await db.execute(text('''WITH classified AS (
      SELECT id,
       (coalesce(attributes->>'_seed_dataset','')='airdeliver-demo-v1' OR sku LIKE 'ADL-DEMO-v1-%') AS demo,
       (is_active AND inventory>0 AND price>=0 AND currency ~ '^[A-Z]{3}$' AND length(trim(name))>0
        AND coalesce(attributes->>'_seed_dataset','')<>'airdeliver-demo-v1' AND sku NOT LIKE 'ADL-DEMO-v1-%') AS eligible
      FROM products)
      SELECT count(*) AS total,
       count(*) FILTER(WHERE demo) AS demo,
       count(*) FILTER(WHERE eligible) AS real_eligible,
       count(*) FILTER(WHERE eligible AND id=ANY(CAST(:recent AS integer[]))) AS real_recent,
       count(*) FILTER(WHERE eligible AND NOT(id=ANY(CAST(:recent AS integer[])))) AS real_fresh
      FROM classified'''),{'recent':sorted(i for i in recent_ids if type(i) is int and 0<i<=2147483647)})
    counts=dict(result.mappings().one())
    reason=('catalog_empty' if not counts['total'] else 'demo_only_catalog' if counts['demo']==counts['total'] else
            'no_real_eligible_stock' if not counts['real_eligible'] else
            'all_real_cards_recent' if not counts['real_fresh'] else 'eligible_pool_not_published')
    return {'reason':reason,**counts}


def opening_status_notice(status):
    reason=status['reason']
    return {
      'catalog_empty':'System notice: this local catalog has no products. A store administrator must add real products before opening cards can appear.',
      'demo_only_catalog':'System notice: this local catalog contains only synthetic demo records. They are hidden, not offers. A store administrator must add real products with actual price and stock before opening cards can appear.',
      'no_real_eligible_stock':'System notice: no real active products with positive local stock and valid price/currency are eligible. A store administrator must verify the catalog data. No demo record will be shown.',
      'all_real_cards_recent':'System notice: the eligible real products were already shown within the opening cooldown. Browse or ask for a product to revisit them; opening rotation resumes as the cooldown expires.',
      'eligible_pool_not_published':'System notice: real eligible products exist, but this opening pool did not publish them. Please retry; the selection needs diagnosis, not demo data.'
    }[reason]
