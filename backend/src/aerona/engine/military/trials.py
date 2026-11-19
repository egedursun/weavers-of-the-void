from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.polity import LawKind, SuccessionRule
from aerona.engine.context import TickContext
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import set_ruler
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.queries import living_entity


async def trial_claims(ctx: TickContext) -> list[tuple[EntityRow, EntityRow, int]]:
    book = await RealmBook.load(ctx.session)
    found: list[tuple[EntityRow, EntityRow, int]] = []
    for realm in book.realms.values():
        rule = await law_param(ctx.session, realm.entity.id, LawKind.SUCCESSION_RULE, "rule")
        if rule != SuccessionRule.BY_COMBAT.value or realm.ruler_id is None:
            continue
        ruler = await living_entity(ctx.session, realm.ruler_id)
        claim = await ctx.session.scalar(
            select(ClaimRow).where(ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.id).limit(1)
        )
        claimant = await living_entity(ctx.session, claim.claimant_entity_id) if claim is not None else None
        if ruler is not None and claimant is not None and claimant.id != ruler.id:
            found.append((claimant, ruler, realm.entity.id))
    return found


async def settle_trial(ctx: TickContext, claimant: EntityRow, ruler: EntityRow, realm_id: int) -> bool:
    book = await RealmBook.load(ctx.session)
    realm = book.realms.get(realm_id)
    claim = await ctx.session.scalar(
        select(ClaimRow).where(ClaimRow.polity_entity_id == realm_id, ClaimRow.claimant_entity_id == claimant.id, ClaimRow.ended_epoch.is_(None)).limit(1)
    )
    won = ruler.status is not EntityStatus.CANON
    if claim is not None:
        claim.ended_epoch = ctx.epoch
        claim.pressed = won
    if won and realm is not None and claimant.status is EntityStatus.CANON:
        return set_ruler(ctx, realm, claimant.id, "won rule by trial of combat")
    return False
