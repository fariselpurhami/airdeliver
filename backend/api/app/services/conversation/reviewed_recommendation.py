"""Reviewed model-authored copy for explicit, current catalog card inputs.

Legacy incomplete dictionaries retain their separate compatibility path. This
adapter does not retrieve, mutate, infer stock or claim SQL freshness itself.
"""
import json
import anyio
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, StrictBool
from app.services.shopping_copy import Claim, ShoppingDraft, GroundingReview, validate_draft
from app.services.structured_output import infer_schema


class RecommendationReason(BaseModel):
    model_config = ConfigDict(extra='forbid')
    product_id: StrictInt
    text: StrictStr = Field(min_length=1, max_length=600)


class ReviewedRecommendation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    intro: StrictStr = Field(min_length=1, max_length=600)
    reasons: list[RecommendationReason] = Field(min_length=0, max_length=3)
    claims: list[Claim] = Field(max_length=30)


class RecommendationReview(GroundingReview):
    answers_actual_decision: StrictBool
    respects_requested_selection: StrictBool
    handles_decisive_unknowns: StrictBool
    useful_next_step: StrictBool


from app.services.conversation.recommendation_contract import RECOMMENDATION_WRITER_RULES, RECOMMENDATION_REVIEW_RULES


async def reviewed_recommendation(infer, query, cards, *, timeout=20):
    # Freeze before the first await, and reject duplicate/current-invalid inputs.
    frozen = [card.model_copy(deep=True) for card in cards]
    if not frozen or len(frozen)>5 or len({c.id for c in frozen})!=len(frozen):
        raise ValueError('Invalid recommendation evidence')
    payload = {'customer_message': query, 'catalog_evidence': [c.model_dump(mode='json') for c in frozen],
               'task': 'Answer this shopping decision with only the useful supplied cards, respecting the requested selection count. Distinguish verified suitability from a conditional preference and identify the decisive missing check. No mutation, merchant availability or superiority claims.'}
    with anyio.fail_after(timeout):
        raw = await infer_schema(infer, [
            {'role':'system','content': RECOMMENDATION_WRITER_RULES},
            {'role':'user','content':json.dumps(payload,ensure_ascii=False)}], ReviewedRecommendation)
        draft = ReviewedRecommendation.model_validate_json(raw)
        ids = [reason.product_id for reason in draft.reasons]
        if len(set(ids))!=len(ids) or not set(ids)<={c.id for c in frozen}:
            raise ValueError('Invalid recommendation identities')
        by_id = {c.id:c for c in frozen}
        for reason in draft.reasons:
            if by_id[reason.product_id].name.casefold() not in reason.text.casefold():
                raise ValueError('Reason omits product identity')
        combined = ShoppingDraft(text=draft.intro+'\n\n'+'\n'.join(r.text for r in draft.reasons), product_ids=ids, claims=draft.claims)
        validate_draft(combined, frozen)
        # Per-reason exact claims cannot borrow another selected product's specs.
        for reason in draft.reasons:
            claims = [c for c in draft.claims if c.product_id==reason.product_id]
            validate_draft(ShoppingDraft(text=reason.text, product_ids=[reason.product_id], claims=claims), frozen)
        review = await infer_schema(infer, [
            {'role':'system','content':RECOMMENDATION_REVIEW_RULES},
            {'role':'user','content':json.dumps({'input':payload,'draft':draft.model_dump()},ensure_ascii=False)}], RecommendationReview)
        verdict = RecommendationReview.model_validate_json(review)
        if not all(verdict.model_dump().values()):
            raise ValueError('Recommendation review rejected')
    return ids, {str(r.product_id):r.text for r in draft.reasons}, draft.intro
