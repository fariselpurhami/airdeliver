"""Bounded non-sensitive shopping taxonomy, not an inferred personality profile."""
import re

AFFIRMATIVE=r'\b(i prefer|i like|i always choose|my favorite|my favourite)\b'
NEGATIVE=r'\b(not|never|don.t|avoid|hate|dislike|she|he|they|wife|husband|friend)\b'
# Values describe product/shopping choices, never health, wealth or identity.
SHOPPING_VALUES={
 'color':set('black white blue red green yellow orange purple pink brown gray grey silver gold beige navy teal cream ivory burgundy olive maroon charcoal turquoise violet'.split()),
 'material':set('cotton linen wool leather denim silk steel aluminum wood glass ceramic polyester nylon bamboo cashmere velvet suede titanium plastic recycled'.split()),
 'style':set('minimalist classic casual formal sporty vintage modern contemporary retro traditional streetwear bohemian elegant rustic industrial'.split()),
 'fit':{'regular','slim','relaxed','loose','oversized','fitted'},
 'pattern':{'solid','striped','checked','floral','geometric','plain','polka dot'},
 'sleeve':{'short sleeve','long sleeve','sleeveless','three quarter sleeve'},
 'neckline':{'crew neck','v neck','polo','turtleneck','round neck'},
 'closure':{'zipper','buttons','laces','slip on','velcro','magnetic'},
 'finish':{'matte','glossy','polished','brushed','satin','natural'},
 'shape':{'round','square','rectangular','oval','curved','compact'},
 'portability':{'lightweight','compact','foldable','portable'},
 'durability':{'durable','repairable','waterproof','water resistant','scratch resistant'},
 'comfort':{'soft','breathable','cushioned','adjustable','ergonomic'},
 'maintenance':{'machine washable','easy clean','dishwasher safe','low maintenance'},
 'packaging':{'minimal packaging','recyclable packaging','plastic free packaging'},
 'sourcing':{'recycled materials','refillable','reusable','locally made'},
 'shopping_priority':{'quality','value','longevity','comfort','design','performance'},
 'delivery_preference':{'pickup','home delivery','standard delivery','express delivery'},
}
DYNAMIC_CATEGORIES={'brand','product_category'}
CATEGORIES=set(SHOPPING_VALUES)|DYNAMIC_CATEGORIES

def normalized_value(value):
 if not isinstance(value,str):return ''
 value=' '.join(value.casefold().strip().split())
 if not 1<=len(value)<=120 or not re.fullmatch(r'[\w -]+',value):return ''
 return value
