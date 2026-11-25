"""Generate1000 neutral local test rows, never real merchant inventory."""
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.real_catalog_import import CATEGORIES,ImportFile
from app.services import catalog_visibility

ITEMS={
 'clothing':['Cotton crewneck shirt','Linen relaxed shirt','Fleece zip jacket','Straight leg trousers','Knit cardigan','Cotton midi dress','Lightweight rain jacket','Jersey long sleeve shirt'],
 'accessories':['Canvas tote bag','Leatherette card holder','Woven belt','Lightweight scarf','Travel backpack','Structured crossbody bag','Cotton baseball cap','Zip pouch'],
 'electronics':['Wireless over ear headphones','Portable Bluetooth speaker','USB C power bank','Adjustable desk light','Compact wireless keyboard','Wireless optical mouse','USB C hub','Tablet stand'],
 'makeup':['Tinted lip balm','Powder blush','Satin lipstick','Mascara','Eye shadow palette','Liquid eyeliner','Makeup brush set','Pressed face powder'],
 'beauty':['Facial cleansing brush','Cosmetic travel case','Compact mirror','Hair dryer','Paddle hair brush','Satin hair wrap','Manicure kit','Perfume atomizer'],
 'personal_care':['Unscented body wash','Daily body lotion','Gentle face cleanser','Fluoride toothpaste','Soft bristle toothbrush','Liquid hand soap','Daily shampoo','Moisturising conditioner'],
 'sports':['Exercise mat','Resistance band set','Stainless water bottle','Adjustable jump rope','Foam roller','Gym duffel bag','Yoga block pair','Training gloves']}
BASE_PRICES={'clothing':[24,39,59,45,49,54,69,29],'accessories':[18,16,22,19,48,35,14,12],'electronics':[59,39,29,24,45,19,32,22],'makeup':[8,14,12,15,24,10,28,14],'beauty':[22,19,12,39,14,16,18,9],'personal_care':[9,12,11,5,4,6,10,11],'sports':[29,24,22,16,24,35,18,19]}
COLORS=['Black','Navy','Cream','Forest','Slate','Rose','Terracotta','Sand']

def generate(count=1000):
 if not catalog_visibility.fixtures_enabled():raise ValueError('Requires APP_ENV=development and AIRDELIVER_DEV_FIXTURES=true')
 if type(count) is not int or not 1<=count<=1000:raise ValueError('Count1..1000')
 rows=[];stamp=datetime.now(timezone.utc).isoformat()
 for i in range(count):
  category=list(CATEGORIES)[i%7];j=i//7;item=ITEMS[category][j%8];color=COLORS[(j//8)%8];variant=j//64
  price=BASE_PRICES[category][j%8]
  attrs={'color':color,'item_type':item}
  if category=='clothing':
   size=['S','M','L'][variant];attrs['size']=size;attrs['material']='Cotton' if 'Cotton' in item or 'Jersey' in item else 'Linen blend' if 'Linen' in item else 'Polyester' if 'Fleece' in item or 'rain' in item else 'Cotton blend'
   suffix=f'Size {size}';detail=f"{attrs['material']} fabric; {size} size."
  elif category in {'personal_care','makeup'}:
   # Stable per-item pack rather than nonsense color/size or capacity claims.
   variants=(['250 ml','500 ml','750 ml'] if category=='personal_care' and j%8 not in (3,4) else ['75 ml','100 ml','125 ml'] if category=='personal_care' and j%8==3 else ['1 piece','2 pieces','3 pieces'] if category=='personal_care' else ['Single pack','Twin pack','Triple pack'])
   suffix=variants[variant];attrs={'item_type':item,'pack':suffix}
   if category=='makeup':attrs['shade']=color;detail=f'{color} shade; {suffix.lower()}.'
   else:detail=f'{suffix} pack format.'
   # More product variations with a coherent packaging label, no health claims.
   finish=['Standard','Pump','Travel','Refill','Desk','Home','Compact','Family'][(j//8)%8]
   if category=='personal_care':attrs['packaging']=finish;color=finish
  elif category=='electronics':
   suffix=['Standard','Compact','Extended'][variant];attrs['format']=suffix;detail=f'{color} finish; {suffix.lower()} format.'
   if 'power bank' in item:attrs['capacity']=['5000 mAh','10000 mAh','20000 mAh'][variant];detail+=f" Rated test capacity {attrs['capacity']}."
   if 'USB C hub' in item:attrs['ports']=['4','6','8'][variant];detail+=f" {attrs['ports']} ports."
  else:
   suffix=['Small','Medium','Large'][variant];attrs['format']=suffix;detail=f'{color} finish; {suffix.lower()} format.'
  attrs.update({'fixture_profile_id':f'{category}-{j%8:02d}','fixture_basis':'docs/verification/dev-fixture-generation-basis-v1.md','fixture_generator':'scripts/generate_dev_catalog.py:v1','fixture_variant':str(j),'image_kind':'neutral category illustration, not product photo','fixture_image':f'frontend/web/public/dev-fixtures/{category}.svg'})
  name=f'{color} {item} - {suffix}'
  # Stock is an explicit generous test quantity, not urgency/popularity evidence.
  rows.append(dict(sku=f'ADL-DEV-v1-{category}-{j+1:04d}',name=name,description=f'{item}. {detail} Synthetic local test product, not a merchant offer.',category=category,price=f'{price*(variant+1) if category in {"makeup","personal_care"} else price+variant*5}.00',currency='USD',inventory=40,image_url=f'/dev-fixtures/{category}.svg',source_url='https://airdeliver.local/dev-fixture',licence='Synthetic local test data',image_licence='Original locally generated neutral SVG',inventory_verified_at=stamp,attributes=attrs,tags=[category,item.lower()]))
 payload=dict(version=1,source_id='airdeliver-dev-fixtures-v1',source_kind='dev_fixture',authorised_source_url='local:airdeliver-dev-fixtures-v1',rights_confirmed=True,offers_authorised=True,products=rows)
 return ImportFile.model_validate(payload).model_dump(mode='json')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--count',type=int,default=1000);a=p.parse_args()
 Path(a.output).write_text(json.dumps(generate(a.count),ensure_ascii=False,indent=2)+'\n');print('Generated synthetic fixture file, not actualinventory. Review with import_real_catalog dryrun.')
