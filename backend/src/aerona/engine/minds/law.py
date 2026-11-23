from sqlalchemy import select

from aerona.catalog.life.minds import STANCE_BOND
from aerona.catalog.life_traits import MADE_MIND_STANCE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindArchiveRow, MindLawRow, MindProfileRow, MindStateRow
from aerona.db.write_guard import held
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.life_traits import MadeMindStanceTrait
from aerona.domain.enums.made import MadeMindStance
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MadeMindSouls, StateMedium
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.factions.companies import realm_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.minds.continuity import law_for
from aerona.engine.minds.profiles import is_made, profile_of
from aerona.engine.minds.souls import default_law, soul_law
from aerona.engine.minds.values import liberty_of
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.community_relations import change_relation

STATUS_STEPS = ("property", "ward", "servant", "citizen", "sovereign")
KEEPING_STANCES = having(MADE_MIND_STANCE_TRAITS, MadeMindStanceTrait.KEEPING_STANCES)


async def grant_soul(ctx: TickContext, mind_id: int) -> MindProfileRow:
    profile = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    if (await soul_law(ctx.session, mind_id)).made_mind_souls is MadeMindSouls.NONE:
        raise ValidationFailedError("The law of this world gives no made mind a soul.")
    profile.souled = True
    await record_incident(ctx, "mind.souled", roles={IncidentRole.SUBJECT: mind_id})
    return profile


async def withhold_soul(ctx: TickContext, mind_id: int) -> MindProfileRow:
    profile = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    profile.souled = False
    await record_incident(ctx, "mind.soul_withheld", roles={IncidentRole.SUBJECT: mind_id})
    return profile


async def seed_laws(ctx: TickContext) -> int:
    known = set(await ctx.session.scalars(select(MindLawRow.world_id)))
    added = 0
    for world in await ctx.session.scalars(select(WorldRow.id).order_by(WorldRow.id)):
        if world not in known:
            ctx.session.add(default_law(world))
            added += 1
    return added


async def tend_soul(ctx: TickContext, row: MindProfileRow) -> None:
    rule = (await soul_law(ctx.session, row.node_id)).made_mind_souls
    if "souled" in row.locked:
        return
    if rule is MadeMindSouls.ALWAYS:
        row.souled = True
    elif rule is MadeMindSouls.NONE:
        row.souled = False
    elif rule is MadeMindSouls.EMERGENT and row.will in {MindWill.FULL, MindWill.EXCEEDING}:
        row.souled = True


async def tend_status(ctx: TickContext, row: MindProfileRow, entity: EntityRow) -> None:
    table = ctx.rules.mind_law
    status = await law_for(ctx, entity, LawKind.MIND_STATUS, "status") or "property"
    step = STATUS_STEPS.index(status) if status in STATUS_STEPS else 0
    doctrine = await doctrine_here(ctx.session, entity)
    lean = STANCE_BOND[doctrine.made_mind_stance] if doctrine is not None else 0
    if "maker_bond" not in row.locked:
        row.maker_bond = clamp_int(row.maker_bond + step * table.bond_by_status // 2 + lean, -PERCENT, PERCENT)
    if doctrine is not None and doctrine.made_mind_stance is MadeMindStance.ABOMINATION and "stability" not in row.locked:
        row.stability = clamp_percent(row.stability - 1)
    wanted = 3 if await liberty_of(ctx.session, row.node_id) > 0 else 1
    if wanted - step < table.movement_gap or row.will not in {MindWill.FULL, MindWill.EXCEEDING}:
        return
    realm = await realm_of(ctx, entity.location_id)
    if realm is None or held(realm) or not ctx.rng(f"mind.movement.{row.node_id}.{ctx.epoch}").chance(table.movement_chance):
        return
    await change_relation(ctx, row.node_id, realm, -table.bond_by_status, MemoryKind.HUMILIATED_ME, note="held at a status below what it sought")
    await record_incident(
        ctx, "mind.movement", roles={IncidentRole.ACTOR: row.node_id, IncidentRole.TARGET: realm}, facts={"bond_loss": table.bond_by_status, "wanted": wanted}
    )
    ctx.count("mind_movements")


async def keep_the_dead(ctx: TickContext) -> int:
    kept = 0
    dead = (
        select(EntityRow)
        .join(MindProfileRow, MindProfileRow.node_id == EntityRow.id)
        .where(EntityRow.status != EntityStatus.CANON, EntityRow.end_epoch == ctx.epoch)
    )
    for entity in list(await ctx.session.scalars(dead)):
        row = await ctx.session.get(MindProfileRow, entity.id)
        doctrine = await doctrine_here(ctx.session, entity)
        if row is None or not is_made(row) or doctrine is None or doctrine.made_afterlife_stance not in KEEPING_STANCES or held(entity.id):
            continue
        archive = await ctx.session.scalar(select(MindArchiveRow).order_by(MindArchiveRow.structure_entity_id).limit(1))
        if archive is None:
            continue
        state = MindStateRow(mind_node_id=entity.id, taken_epoch=ctx.epoch, fidelity_pct=row.fidelity_pct, holder_node_id=archive.structure_entity_id)
        state.medium_kind, state.sealed, state.copies, state.owner_node_id, state.locked = StateMedium.RECORD, False, 1, archive.holder_node_id, []
        ctx.session.add(state)
        await record_incident(
            ctx,
            "mind.archived_at_death",
            roles={IncidentRole.SUBJECT: entity.id, IncidentRole.PLACE: archive.structure_entity_id},
            facts={"fidelity": row.fidelity_pct},
            place=archive.structure_entity_id,
        )
        kept += 1
    return kept


@reads(
    "cult.zeal",
    "table.cult_doctrines",
    "table.entities",
    "table.law_profiles",
    "table.mind_archives",
    "table.mind_laws",
    "table.mind_profiles",
    "table.nodes",
    "table.worlds",
)
@writes("table.memories", "table.mind_laws", "table.mind_profiles", "table.mind_states")
async def keep_mind_law(ctx: TickContext) -> None:
    ctx.count("mind_laws_seeded", await seed_laws(ctx))
    rows = await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.made_by_node_id.is_not(None)).order_by(MindProfileRow.node_id))
    for row in list(rows):
        entity = await ctx.session.get(EntityRow, row.node_id)
        if entity is None or entity.status is not EntityStatus.CANON or held(row.node_id) or not is_made(row):
            continue
        await tend_soul(ctx, row)
        await tend_status(ctx, row, entity)
    ctx.count("made_dead_kept", await keep_the_dead(ctx))
    await ctx.session.flush()
