"""Evidence-bounded answer shape, never a source of product facts or actions."""
FOUR_PHASE_POLICY = '''For substantive product advice, restore the four logical phases in this order: opening, data core, synthesis, closure. Write exactly four nonempty sections separated by a blank line, without phase labels or headings. Opening: answer the current need and acknowledge an explicit occasion or concern without inferred tastes. Data core: concise evidence-backed facts or tradeoffs; bullets are allowed only inside this section. Synthesis: explain what the supplied evidence supports for the customer's actual constraints, and name missing evidence rather than inventing a winner. Closure: an honest useful next step or focused question, never global availability, reservation, procurement, discount or transaction promises. All product claims still require exact supplied evidence and the existing independent review. Missing facts stay unknown, not classified/proprietary. Do not infer personality, wealth, urgency, merchant stock, compatibility or superiority. Keep the four sections concise, at most 160 words total; do not pad an unknown answer. The structured cards remain the product evidence. Short listed-price questions, clarification, no-match and social replies remain short and do not require four sections. Opening carousels keep their own two-paragraph contract; do not confuse four answer phases with four opening rows.'''

FOUR_PHASE_REVIEW = '''When input.request_evidence.product_answer_shape is four_phase, fulfills_discovery_task is true ONLY if the substantive answer has four nonempty sections in order: opening answering the current need, data core with supported facts/tradeoffs, synthesis tied to actual constraints with honest unknowns, and useful low-pressure closure. Require blank-line separation and no internal phase labels/headings. A sequence of four generic filler paragraphs fails. Reject unsupported winners, fabricated global availability, private facts, discounts, urgency or procurement promises. The price/clarification/no-match/social and opening-carousel exceptions retain their own format.'''


def answer_shape(mode, cards, evidence):
    if mode != 'catalog_results' or not cards:
        return 'short'
    if evidence.get('sales_intent') == 'OPENING_INSIGHT':
        return 'opening_two_paragraph'
    if evidence.get('shopping_task') == 'price_inquiry':
        return 'short'
    return 'four_phase'
