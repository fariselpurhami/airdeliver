"""Exact operational status copy, not generated product advice or a classifier.

Machine categories and original diagnostics stay internal. Unknown prose is never
rewritten, so customer/model/product text cannot select actions by a substring.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class CustomerStatus:
    code: str
    text: str
    recovery: str = 'browse'

STATUSES = {
 'opening_unverified': CustomerStatus('opening_unverified', "I couldn't finish the introduction for this selection. You can try loading it again or explore the catalog directly.", 'retry_opening'),
 'opening_empty': CustomerStatus('opening_empty', "There isn't a selection to show here yet. You can browse the catalog or tell me what you're looking for.", 'retry_opening'),
 'capacity': CustomerStatus('capacity', "I can't take another shopping question right now. Please give it a little time, or explore the catalog while you wait. I haven't made a shopping change.", 'retry_chat'),
 'assistant_unavailable': CustomerStatus('assistant_unavailable', "I can't answer your shopping question right now. You can try again later or browse the catalog. I haven't made a shopping change.", 'retry_chat'),
 'reply_unverified': CustomerStatus('reply_unverified', "I couldn't confirm enough detail to give you a reliable answer. You can try the question again or explore the catalog. I haven't reserved anything.", 'retry_chat'),
 'catalog_unverified': CustomerStatus('catalog_unverified', "I couldn't check the current product details. Please try again before relying on a recommendation, or explore the catalog directly.", 'retry_chat'),
 'visual_unavailable': CustomerStatus('visual_unavailable', "I couldn't complete the image search. You can try the photo again or describe the product you're looking for.", 'browse'),
 'preferences_changed': CustomerStatus('preferences_changed', "Your saved shopping preferences changed while I was answering. Please send the question again so I can use the current settings.", 'retry_chat'),
 'research_unavailable': CustomerStatus('research_unavailable', "I couldn't check reliable information for that product right now. Please try again later or share the exact model and a manufacturer link.", 'retry_chat'),
 'research_unverified': CustomerStatus('research_unverified', "I found product information, but couldn't confirm that it supports the answer for the exact model you asked about. Share its manufacturer link or full model name so I can check the right details.", 'retry_chat'),
 'research_empty': CustomerStatus('research_empty', "I didn't find reliable information for that product in this search. That doesn't mean it doesn't exist. Could you share the exact model name or a manufacturer link?", 'browse'),
 'research_scope': CustomerStatus('research_scope', "That question is too broad for me to check carefully in one reply. Which exact model and detail would you like me to check first?", 'browse'),
 'catalog_not_ready': CustomerStatus('catalog_not_ready', "There aren't any purchasable products to show in this selection yet. Test items aren't real offers. You can explore the catalog, but checkout needs real product details, prices and stock.", 'browse'),
 'selection_recent': CustomerStatus('selection_recent', "You've already seen the products in this rotation. You can revisit them in the catalog or ask me about a particular item.", 'browse'),
}

# Exact historical strings are retained as aliases, never regex-matched input.
ALIASES = {
 'System notice: catalog cards were found, but the opening introduction could not be verified. Retry the opening or browse the catalog.': 'opening_unverified',
 'The opening selection could not be loaded. Please retry or browse the catalog.': 'opening_unverified',
 'System notice: no eligible cards were found for this opening selection. This does not mean the catalog is empty. Retry or browse the catalog.': 'opening_empty',
 'Chat assistance is temporarily at its shared model capacity. No shopping action was taken. Please wait briefly or use the catalog.': 'capacity',
 'System notice: a grounded shopping reply could not be generated. No product is reserved and no merchant availability has been verified. Please try again or browse the catalog.': 'reply_unverified',
 'System notice: current catalog evidence is incomplete. No product recommendation or reservation was made.': 'catalog_unverified',
 'System notice: no eligible supplied catalog cards were available for reviewed recommendations.': 'opening_empty',
 'System notice: a grounded recommendation could not be verified. No product has been reserved.': 'reply_unverified',
 'System notice: a grounded consultation could not be verified. No product recommendation or reservation was made.': 'reply_unverified',
 'System notice: the complete current product evidence could not be checked. Please retry.': 'catalog_unverified',
 'System notice: current gift candidates could not be checked. Please retry.': 'catalog_unverified',
 'System notice: catalog search is temporarily unavailable. Please try again.': 'catalog_unverified',
 'System notice: current catalog evidence could not be checked. No product recommendation was published.': 'catalog_unverified',
 'System notice: visual product evidence could not be checked in time. Please retry.': 'visual_unavailable',
 'System notice: visual search is temporarily unavailable. Please try again.': 'visual_unavailable',
 'System notice: saved shopping preferences changed during this reply. Please retry with your current preferences.': 'preferences_changed',
 'Personalization was reset during this reply. Please retry.': 'preferences_changed',
 'My cognitive subsystems are currently recalibrating. Please try again in a moment.': 'assistant_unavailable',
 'System notice: this local catalog has no products. A store administrator must add real products before opening cards can appear.': 'catalog_not_ready',
 'System notice: this local catalog contains only synthetic demo records. They are hidden, not offers. A store administrator must add real products with actual price and stock before opening cards can appear.': 'catalog_not_ready',
 'System notice: no real active products with positive local stock and valid price/currency are eligible. A store administrator must verify the catalog data. No demo record will be shown.': 'catalog_not_ready',
 'System notice: development fixtures exist, but this opening selection did not publish them. Fixture cards are synthetic local test data, not real stock or offers. Check fixture eligibility, cooldown and model-copy status.': 'catalog_not_ready',
 'System notice: the eligible real products were already shown within the opening cooldown. Browse or ask for a product to revisit them; opening rotation resumes as the cooldown expires.': 'selection_recent',
 'System notice: real eligible products exist, but this opening pool did not publish them. Please retry; the selection needs diagnosis, not demo data.': 'opening_unverified',
}
_ROUTER_MESSAGES = [
 'Chat assistance could not authenticate with the model provider. An administrator must check its credentials.',
 'Chat assistance was rate-limited by the model provider. This may be a request or account quota limit. No cause beyond the provider limit is verified.',
 'Chat assistance received a model-provider server error. Please retry later.',
 'Chat assistance encountered a model or request configuration error. An administrator must check the safe API diagnostics.',
 'Chat assistance timed out while routing this request. Please retry later.',
 'Chat assistance could not connect to the model provider. Please retry later.',
 'Chat assistance received an invalid structured routing response. No shopping action was taken.',
 'Chat assistance could not validate the model routing result. No shopping action was taken. Please retry or use the catalog.',
 'Chat assistance has a configuration problem. Please use the catalog or support page while it is corrected.',
 'Chat assistance is not configured right now. Please use the catalog or support page.',
 'Chat assistance has a model or endpoint configuration problem. Please use the catalog or support page while it is corrected.',
 'Chat assistance is temporarily unavailable. Please try again or use the catalog or support page.',
 'Chat assistance is temporarily unavailable.',
]
for _text in _ROUTER_MESSAGES:
    ALIASES[_text] = 'assistant_unavailable'
for _text, _code in tuple(ALIASES.items()):
    if _text.startswith('Chat assistance'):
        ALIASES['System notice: '+_text] = _code

# Exact source-research failures keep their diagnostic causes at the caller.
ALIASES['System notice: the AI provider has temporarily limited product research requests. Please retry later. No source-backed answer was verified.'] = 'research_unavailable'
ALIASES['System notice: the source evidence exceeds the local research request budget. Please narrow the product question. No source-backed answer was verified.'] = 'research_scope'
ALIASES['System notice: product web research is not configured. A store administrator must configure the research API credential. No source-backed answer was checked.'] = 'research_unavailable'
ALIASES['System notice: product web research could not authenticate. A store administrator must check its research credential. No source-backed answer was verified.'] = 'research_unavailable'
ALIASES['System notice: product web research is rate-limited right now. Please retry later. No source-backed answer was verified.'] = 'research_unavailable'
ALIASES['System notice: product web research timed out. Please retry. No source-backed answer was verified.'] = 'research_unavailable'
ALIASES['System notice: product web research could not connect. Please retry. No source-backed answer was verified.'] = 'research_unavailable'
ALIASES['System notice: the product research service returned a server error. Please retry. No source-backed answer was verified.'] = 'research_unavailable'
ALIASES['System notice: the product research service rejected the request. A store administrator must check the research configuration.'] = 'research_unavailable'
ALIASES['No source results were returned for this product question. That does not mean the model does not exist. Please retry or share a manufacturer link.'] = 'research_empty'
ALIASES['Source results were returned but none passed the source URL and readable-text checks. No product fact was verified. Please retry or share a manufacturer link.'] = 'research_unverified'
ALIASES['Source pages were found, but an exact supporting quote could not be verified. No unverified specifications were published. Please retry or share a manufacturer link.'] = 'research_unverified'
ALIASES['Source pages were found, but the extracted facts did not pass the exact-product grounding review. No unverified specifications were published. Please retry or share a manufacturer link.'] = 'research_unverified'
ALIASES['Source pages were found, but the product information response had an invalid format. Please retry. No unverified specifications were published.'] = 'research_unverified'
ALIASES['System notice: product research could not be completed. Please retry. No source-backed answer was verified.'] = 'research_unavailable'


def customer_status(text):
    if not isinstance(text, str): return None
    code = ALIASES.get(text)
    if code: return STATUSES[code]
    return next((item for item in STATUSES.values() if item.text == text), None)


def human_text(text):
    status = customer_status(text)
    return status.text if status else text


def human_payload(payload):
    """Only top-level server-owned display text; never arbitrary nested data."""
    result = dict(payload)
    for key in ('text', 'content', 'intro', 'intro_message', 'detail', 'message'):
        value = result.get(key)
        status = customer_status(value)
        if status:
            result[key] = status.text
            if key not in {'detail', 'message'}:
                result.setdefault('status_code', status.code)
                result.setdefault('recovery', status.recovery)
    return result
