import re
from sqlmodel import Session, select, or_
from app.models.product import Product
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import case, cast, String, and_

class AICommerceEngine:

    def __init__(self):
        self.intent_keywords = {
            "ADD_TO_CART": ["add", "buy", "get", "purchase", "i want", "i need", "i'd like"],
            "REMOVE_FROM_CART": ["remove", "delete", "take off", "drop"],
            "SEARCH_PRODUCT": ["find", "search for", "show me", "can i see", "do you have"],
            "CHECK_PRICE": ["how much is", "what's the price of", "price of"],
        }
        
        self.stop_words = [
            "a", "an", "the", "some", "for", "me", "my", "to", "please", "thank you", 
            "item", "items", "product", "products", "of", "is", "are"
        ]

        self.price_patterns = {
            "max_price": re.compile(r"(under|less than|below|max|maximum) (\$|usd)? ?(\d+\.?\d*)"),
            "min_price": re.compile(r"(over|more than|above|min|minimum) (\$|usd)? ?(\d+\.?\d*)"),
            "around_price": re.compile(r"(around|about|approx|approximately) (\$|usd)? ?(\d+\.?\d*)"),
            "price_range": re.compile(r"(between|from) (\$|usd)? ?(\d+\.?\d*) (and|to) (\$|usd)? ?(\d+\.?\d*)"),
        }
        
        self.quantity_pattern = re.compile(r"(\d+) (units|items|pairs|of them|)")

        self.synonym_map = {
            "phone": "smartphone",
            "cellphone": "smartphone",
            "watch": "smartwatch",
            "tv": "television",
            "laptop": "computer",
            "pc": "computer",
            "cheap": "budget",
            "affordable": "budget",
            "costly": "premium",
            "expensive": "premium",
            "sneakers": "shoes",
            "running": "sport",
            "formal": "business",
            "dress": "clothing",
            "shirt": "clothing",
            "pants": "clothing",
        }

        self.context_map = {
            "interview": {"category": "clothing", "tags": ["formal", "business", "suit"]},
            "job": {"category": "clothing", "tags": ["formal", "business", "suit"]},
            "meeting": {"category": "clothing", "tags": ["business"]},
            "sport": {"category": "clothing", "tags": ["sport", "fitness"]},
            "running": {"category": "shoes", "tags": ["sport", "running"]},
            "workout": {"tags": ["sport", "fitness"]},
            "party": {"category": "clothing", "tags": ["party", "formal"]},
            "gift": {"tags": ["gift", "popular", "premium"]},
            "present": {"tags": ["gift", "popular", "premium"]},
            "gift for her": {"tags": ["gift", "women", "jewelry", "perfume"]},
            "girlfriend": {"tags": ["gift", "women", "jewelry", "perfume"]},
            "wife": {"tags": ["gift", "women", "jewelry", "perfume"]},
            "gift for him": {"tags": ["gift", "men", "watch", "electronics"]},
            "boyfriend": {"tags": ["gift", "men", "watch", "electronics"]},
            "husband": {"tags": ["gift", "men", "watch", "electronics"]},
        }

    def _normalize_message(self, message: str) -> str:
        message = message.lower()
        message = re.sub(r"[^\w\s\d\$\.]", "", message)
        return message

    def _classify_intent(self, normalized_message: str) -> Tuple[str, str]:
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if normalized_message.startswith(keyword + " "):
                    cleaned_message = normalized_message[len(keyword):].strip()
                    return intent, cleaned_message
        
        return "SEARCH_PRODUCT", normalized_message

    def _extract_entities(self, message: str) -> Dict[str, Any]:
        entities = {
            "product_name": None,
            "min_price": None,
            "max_price": None,
            "quantity": 1,
            "context_rules": [],
        }
        
        original_message = message

        for context_key, rules in self.context_map.items():
            if context_key in message:
                entities["context_rules"].append(rules)
                message = message.replace(context_key, "")

        for price_type, pattern in self.price_patterns.items():
            match = pattern.search(message)
            if match:
                if price_type == "max_price":
                    entities["max_price"] = float(match.group(3))
                elif price_type == "min_price":
                    entities["min_price"] = float(match.group(3))
                elif price_type == "around_price":
                    price = float(match.group(3))
                    entities["min_price"] = price * 0.9
                    entities["max_price"] = price * 1.1
                elif price_type == "price_range":
                    entities["min_price"] = float(match.group(3))
                    entities["max_price"] = float(match.group(6))
                
                message = message.replace(match.group(0), "")

        quantity_match = self.quantity_pattern.search(message)
        if quantity_match:
            try:
                entities["quantity"] = int(quantity_match.group(1))
                message = message.replace(quantity_match.group(0), "")
            except ValueError:
                entities["quantity"] = 1

        product_name_parts = []
        for word in message.split():
            if word not in self.stop_words:
                product_name_parts.append(word)
        
        product_name = " ".join(product_name_parts).strip()
        
        if not product_name:
            if not entities["context_rules"] and not entities["min_price"] and not entities["max_price"]:
                if original_message.strip():
                     entities["product_name"] = original_message.strip().rstrip('s')
            else:
                 entities["product_name"] = None
        else:
            entities["product_name"] = product_name.rstrip('s')
            
            synonym = self.synonym_map.get(entities["product_name"])
            if synonym:
                if "tags" not in entities:
                    entities["tags"] = []
                entities["tags"] = [synonym]

        return entities

    def _generate_query_statement(self, db: Session, entities: dict) -> Any:
        statement = select(Product)
        search_criteria = []
        
        product_name = entities.get("product_name")
        context_tags = set()
        context_categories = set()

        if entities.get("min_price"):
            statement = statement.where(Product.price >= entities["min_price"])
        if entities.get("max_price"):
            statement = statement.where(Product.price <= entities["max_price"])
            
        for rule in entities.get("context_rules", []):
            if "category" in rule:
                context_categories.add(rule["category"])
            if "tags" in rule:
                context_tags.update(rule["tags"])

        if context_categories:
            statement = statement.where(Product.category.in_(list(context_categories)))
        
        
        if context_tags:
            tag_criteria = [cast(Product.tags, String).ilike(f"%{tag}%") for tag in context_tags]
            statement = statement.where(or_(*tag_criteria))


        if entities.get("tags"):
            synonym_criteria = [cast(Product.tags, String).ilike(f"%{tag}%") for tag in entities["tags"]]
            statement = statement.where(or_(*synonym_criteria))

        if product_name:
            name_query = f"%{product_name}%"
            words = product_name.split()
            
            exact_name_match = Product.name.ilike(product_name)
            partial_name_match = Product.name.ilike(name_query)
            
            # **IMPROVEMENT**: Use AND logic for multi-word name search
            multi_word_name_match = and_(*[Product.name.ilike(f"%{word}%") for word in words])
            
            tag_match = cast(Product.tags, String).ilike(name_query)
            desc_match = Product.description.ilike(name_query)
            
            search_criteria.append(exact_name_match)
            search_criteria.append(partial_name_match)
            search_criteria.append(multi_word_name_match)
            search_criteria.append(tag_match)
            search_criteria.append(desc_match)

            # **IMPROVEMENT**: Give much higher rank to exact and multi-word matches
            search_rank = case(
                (exact_name_match, 10),
                (multi_word_name_match, 8),
                (partial_name_match, 5),                     
                (tag_match, 3),                      
                (desc_match, 2),                     
                else_=0
            ).label("rank")
            
            statement = statement.where(or_(*search_criteria)).order_by(search_rank.desc(), Product.price.asc())

        elif not context_tags and not context_categories and not entities.get("min_price") and not entities.get("max_price"):
            return None

        statement = statement.limit(5)
        return statement

    def find_products_from_message(self, db: Session, message: str) -> Tuple[List[Product], Dict[str, Any]]:
        normalized_message = self._normalize_message(message)
        intent, cleaned_message = self._classify_intent(normalized_message)
        
        entities = self._extract_entities(cleaned_message)
        
        statement = self._generate_query_statement(db, entities)
        
        if statement is None:
            return [], entities
            
        products = db.exec(statement).all()
        
        if not products and entities.get("product_name") and " " in entities.get("product_name", ""):
            new_entities = entities.copy()
            new_entities["product_name"] = entities["product_name"].split(" ")[-1]
            statement = self._generate_query_statement(db, new_entities)
            if statement is not None:
                products = db.exec(statement).all()
                return products, new_entities

        return products, entities

ai_commerce_engine = AICommerceEngine()
