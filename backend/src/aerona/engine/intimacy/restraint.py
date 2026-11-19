from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.intimacy_shapes import OCCASION_ODDS_PCT
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import RestraintCustomRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.intimacy import RestraintOccasion, RestraintRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathBreach, OathKind
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.polity.oaths import break_on, oaths_of, swear
from aerona.engine.primitives.folk import folk_among
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import at_war

ROLE_MEMBERS: dict[RestraintRole, frozenset[MortalRole] | None] = {
    RestraintRole.CLERGY: frozenset({MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER}),
    RestraintRole.ASCETIC: frozenset({MortalRole.SAINT, MortalRole.SAGE}),
    RestraintRole.WARRIOR: frozenset({MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.OFFICER}),
    RestraintRole.RULER: frozenset({MortalRole.RULER}),
    RestraintRole.EVERYONE: None,
}


@dataclass
class RestraintTally:
    vowed: int = 0
    broken: int = 0


async def bound_by(ctx: TickContext, custom: RestraintCustomRow) -> list[EntityRow]:
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_among(ctx.session, [custom.people_entity_id])
    )
    roles = ROLE_MEMBERS[custom.role]
    if roles is not None:
        statement = statement.where(EntityRow.mortal_role.in_(sorted(roles)))
    return [being for being in await ctx.session.scalars(statement.order_by(EntityRow.id)) if not held(being.id)]


async def in_season(ctx: TickContext, custom: RestraintCustomRow, being: EntityRow) -> bool:
    if custom.occasion is not RestraintOccasion.BEFORE_BATTLE:
        return True
    realm = await realm_of(ctx.session, being.location_id) if being.location_id is not None else None
    return realm is not None and await at_war(ctx.session, realm)


async def vow_customs(ctx: TickContext, tally: RestraintTally) -> None:
    table = ctx.rules.unions_and_birth
    for custom in list(await ctx.session.scalars(select(RestraintCustomRow).order_by(RestraintCustomRow.id))):
        if held(custom.people_entity_id):
            continue
        for being in await bound_by(ctx, custom):
            if await oaths_of(ctx, being.id, OathKind.CELIBACY) or not await in_season(ctx, custom, being):
                continue
            if not ctx.rng(f"restraint.{custom.id}.{being.id}.{ctx.epoch}").chance(
                custom.strength * table.restraint_vow_pct / PERCENT * OCCASION_ODDS_PCT[custom.occasion] / PERCENT
            ):
                continue
            oath = await swear(ctx, being, OathKind.CELIBACY, recipient_id=None, note_text=f"by the custom of restraint for {spoken(custom.role)}")
            if custom.occasion is not RestraintOccasion.ALWAYS:
                oath.deadline_epoch = ctx.epoch + 1
            await record(
                ctx,
                "unions.vow_taken",
                roles={IncidentRole.ACTOR: being.id},
                facts={"vow": OathKind.CELIBACY, "occasion": custom.occasion},
                place=being.location_id,
            )
            tally.vowed += 1


async def break_vows(ctx: TickContext, pairs: list[tuple[EntityRow, EntityRow, RelationshipRow]], tally: RestraintTally) -> None:
    for first, second, _row in pairs:
        for being, lover in ((first, second), (second, first)):
            if not await oaths_of(ctx, being.id, OathKind.CELIBACY):
                continue
            await break_on(ctx, [being.id], OathKind.CELIBACY, OathBreach.LOVER_TAKEN)
            await record(
                ctx,
                "unions.vow_broken",
                roles={IncidentRole.ACTOR: being.id, IncidentRole.TARGET: lover.id},
                facts={"vow": OathKind.CELIBACY},
                place=being.location_id,
            )
            tally.broken += 1
