from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.db.tables.crafts import MaterialAffinityRow, SympatheticLinkRow
from aerona.db.tables.culture import RiteEffectRow
from aerona.db.tables.customs import EvidenceRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import AccusationRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import AffinityMode, LinkToken
from aerona.domain.enums.culture import MagicSchool, RiteEffectKind
from aerona.domain.enums.customs import EvidenceKind
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.folkways import AccusationOutcome
from aerona.engine.context import TickContext
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import active_bonds, has_flag

MAGICAL = frozenset({MaterialFamily.PRECIOUS, MaterialFamily.EXOTIC})


@dataclass
class SympathyTally:
    affinities: int = 0
    taken: int = 0
    burned: int = 0
    faded: int = 0
    evidence: int = 0


async def keep_affinities(ctx: TickContext, tally: SympathyTally) -> None:
    table = ctx.rules.affinities
    known = set(await ctx.session.scalars(select(MaterialAffinityRow.material_id)))
    for material in list(await ctx.session.scalars(select(WorldMaterialRow).where(WorldMaterialRow.family.in_(MAGICAL)).order_by(WorldMaterialRow.id))):
        if material.id in known:
            continue
        rng = ctx.rng(seed_of("affinity", material.id))
        if not rng.chance(table.seed_chance):
            continue
        ctx.session.add(MaterialAffinityRow(material_id=material.id, school=rng.pick(list(MagicSchool)), mode=rng.pick(list(AffinityMode)), locked=[]))
        tally.affinities += 1


async def casters(ctx: TickContext) -> list[EntityRow]:
    cursing = set(await ctx.session.scalars(select(RiteEffectRow.rite_entity_id).where(RiteEffectRow.effect == RiteEffectKind.CURSE)))
    if not cursing:
        return []
    bonds = await active_bonds(ctx.session, [BondKind.OWNS], targets=sorted(cursing))
    ids = sorted({bond.source_node_id for bond in bonds})
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.id.in_(ids), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def take_links(ctx: TickContext, tally: SympathyTally) -> None:
    table = ctx.rules.sympathy
    for caster in await casters(ctx):
        grudge = await ctx.session.scalar(
            select(MemoryRow)
            .join(EntityRow, EntityRow.id == MemoryRow.subject_node_id)
            .where(
                MemoryRow.holder_node_id == caster.id,
                MemoryRow.magnitude < 0,
                EntityRow.location_id == caster.location_id,
                EntityRow.status == EntityStatus.CANON,
            )
            .order_by(MemoryRow.magnitude, MemoryRow.id)
            .limit(1)
        )
        if grudge is None or grudge.subject_node_id is None or held(grudge.subject_node_id):
            continue
        rng = ctx.rng(seed_of("sympathy", caster.id, ctx.epoch))
        if not rng.chance(table.take_chance):
            continue
        token = rng.pick([LinkToken.HAIR, LinkToken.BLOOD])
        true_name = await ctx.session.get(TrueNameRow, grudge.subject_node_id)
        if true_name is not None and caster.id in true_name.known_by:
            token = LinkToken.NAME
        ctx.session.add(SympatheticLinkRow(holder_node_id=caster.id, target_node_id=grudge.subject_node_id, token=token, obtained_epoch=ctx.epoch, locked=[]))
        tally.taken += 1


async def burn_and_fade(ctx: TickContext, tally: SympathyTally) -> None:
    table = ctx.rules.sympathy
    for row in list(await ctx.session.scalars(select(SympatheticLinkRow).order_by(SympatheticLinkRow.id))):
        if held(row.holder_node_id) or held(row.target_node_id):
            continue
        burnt = (
            row.token in {LinkToken.HAIR, LinkToken.BLOOD}
            and await has_flag(ctx.session, row.target_node_id, EntityFlag.CURSED)
            and ctx.rng(seed_of("sympathy.burn", row.id, ctx.epoch)).chance(table.burn_chance)
        )
        if burnt:
            await ctx.session.execute(delete(SympatheticLinkRow).where(SympatheticLinkRow.id == row.id))
            tally.burned += 1
            continue
        if "strength" in row.locked:
            continue
        row.strength -= table.decay
        if row.strength <= 0:
            await ctx.session.execute(delete(SympatheticLinkRow).where(SympatheticLinkRow.id == row.id))
            tally.faded += 1


async def links_as_evidence(ctx: TickContext, tally: SympathyTally) -> None:
    accused = await ctx.session.scalars(
        select(AccusationRow).where(AccusationRow.outcome == AccusationOutcome.PENDING, AccusationRow.case_id.is_not(None)).order_by(AccusationRow.id)
    )
    for accusation in list(accused):
        links = list(await ctx.session.scalars(select(SympatheticLinkRow).where(SympatheticLinkRow.holder_node_id == accusation.accused_node_id)))
        if not links or accusation.case_id is None:
            continue
        laid = await ctx.session.scalar(
            select(EvidenceRow.id).where(
                EvidenceRow.case_id == accusation.case_id, EvidenceRow.kind == EvidenceKind.MAGIC, EvidenceRow.points_to_node_id == accusation.accused_node_id
            )
        )
        if laid is not None:
            continue
        ctx.session.add(
            EvidenceRow(
                case_id=accusation.case_id,
                kind=EvidenceKind.MAGIC,
                points_to_node_id=accusation.accused_node_id,
                reliability=max(link.strength for link in links),
                found_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.evidence += 1


async def keep_sympathy(ctx: TickContext, tally: SympathyTally) -> None:
    await keep_affinities(ctx, tally)
    await take_links(ctx, tally)
    await ctx.session.flush()
    await burn_and_fade(ctx, tally)
    await links_as_evidence(ctx, tally)
    await ctx.session.flush()
