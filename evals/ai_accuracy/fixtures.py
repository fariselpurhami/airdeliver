"""Synthetic catalog cards used by the runner. Names match cases.json."""
SPECS={'Cotton Shirt':('24.00','Shirts','material','cotton'),'Trail Backpack':('59.00','Backpacks','weight','650 g'),
 'Studio Headphones':('79.00','Headphones','connectivity','Bluetooth'),'Desk Lamp':('35.00','Lighting','material','aluminium'),
 'Steel Bottle':('18.00','Bottles','capacity','750 ml'),'Running Shoes':('95.00','Shoes','material','mesh'),
 'Oak Desk':('240.00','Furniture','material','oak'),'Ceramic Mug':('12.00','Kitchen','material','ceramic'),
 'Wool Scarf':('30.00','Accessories','material','wool'),'Smart Watch':('150.00','Wearables','connectivity','Bluetooth')}
def cards():
    return {n:dict(id=i+1,name=n,price=p,currency='USD',inventory=5,is_active=True,category=c,attributes={k:v})
            for i,(n,(p,c,k,v)) in enumerate(SPECS.items())}
