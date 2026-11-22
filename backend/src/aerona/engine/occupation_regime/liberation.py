from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationRegimeRow
from aerona.db.tables.polity import PolityProfileRow, PolityTerritoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.occupation_regimes import CollaborationFate, OccupationEnding
from aerona.engine.context import TickContext
from aerona.engine.occupation_regime.book import RegimeTally
from aerona.engine.occupation_regime.collaborators import end_service
from aerona.engine.occupation_regime.rule import lift_laws
from aerona.engine.reckoning.book import ReckoningTally
from aerona.engine.reckoning.opening import choose, open_reckoning, victims_pressure
from aerona.engine.recording.record import record


async def reckon(ctx: TickContext, regime: OccupationRegimeRow, collaborators: list[CollaborationRow]) -> None:
    realm = await ctx.session.get(EntityRow, regime.owner_polity_id) if regime.owner_polity_id is not None else None
    profile = await ctx.session.get(PolityProfileRow, realm.id) if realm is not None else None
    if realm is None or profile is None or realm.status is not EntityStatus.CANON or held(realm.id) or not collaborators:
        return
    if not ctx.rng(f"occupation.reckoning.{regime.id}").chance(ctx.rules.reckoning.open_chance_pct):
        return
    pressure = await victims_pressure(ctx, realm.id)
    measures = await choose(ctx, None, profile, pressure)
    await open_reckoning(ctx, realm, regime.occupier_entity_id, measures, by=None, fallen_epoch=ctx.epoch, tally=ReckoningTally())


async def liberate(ctx: TickContext, regime: OccupationRegimeRow, tally: RegimeTally) -> None:
    owner = await ctx.session.get(EntityRow, regime.owner_polity_id) if regime.owner_polity_id is not None else None
    standing = owner is not None and owner.status is EntityStatus.CANON
    await lift_laws(ctx, regime)
    regime.ended_epoch, regime.ending = ctx.epoch, OccupationEnding.LIBERATED if standing else OccupationEnding.WITHDRAWN
    query = select(CollaborationRow).where(CollaborationRow.regime_id == regime.id, CollaborationRow.fate == CollaborationFate.SERVING)
    collaborators = list(await ctx.session.scalars(query.order_by(CollaborationRow.id)))
    for row in collaborators:
        await end_service(ctx, row, CollaborationFate.ENDED)
    tally.liberated += 1
    await record(
        ctx,
        "occupation.liberated",
        roles={IncidentRole.SUBJECT: regime.region_entity_id, IncidentRole.VICTIM: regime.occupier_entity_id, IncidentRole.BENEFICIARY: regime.owner_polity_id},
        facts={"ending": regime.ending, "collaborators": len(collaborators)},
    )
    await reckon(ctx, regime, collaborators)


async def ceded_to_occupier(ctx: TickContext, regime: OccupationRegimeRow) -> bool:
    return await ctx.session.get(PolityTerritoryRow, (regime.occupier_entity_id, regime.region_entity_id)) is not None


async def end_by_cession(ctx: TickContext, regime: OccupationRegimeRow, tally: RegimeTally) -> None:
    await lift_laws(ctx, regime)
    regime.ended_epoch, regime.ending = ctx.epoch, OccupationEnding.ANNEXED
    query = select(CollaborationRow).where(CollaborationRow.regime_id == regime.id, CollaborationRow.fate == CollaborationFate.SERVING)
    serving = list(await ctx.session.scalars(query.order_by(CollaborationRow.id)))
    for row in serving:
        await end_service(ctx, row, CollaborationFate.ENDED)
    tally.annexed += 1
    await record(
        ctx,
        "occupation.ceded",
        roles={IncidentRole.ACTOR: regime.occupier_entity_id, IncidentRole.SUBJECT: regime.region_entity_id, IncidentRole.VICTIM: regime.owner_polity_id},
        facts={"collaborators": len(serving)},
    )
