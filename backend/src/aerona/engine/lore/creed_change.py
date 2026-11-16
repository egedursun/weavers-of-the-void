from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.lore import IDEOLOGY_VALUES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.total import total
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow, IdeologyTenetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.regime import RegimeRow
from aerona.db.tables.thin_sections import ConstitutionRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.regime import SelectorateKind
from aerona.domain.models.entity_stats import IdeologyStats
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.technology.profiles import family_level

IT = IdeologyTenet
SELECTORATES: Mapping[IdeologyTenet, SelectorateKind | None] = total(
    IdeologyTenet,
    {
        IT.LEGALISM: SelectorateKind.COUNCIL,
        IT.RESTRAINT: None,
        IT.EGALITARIANISM: SelectorateKind.CITIZENS,
        IT.DIVINE_RIGHT: SelectorateKind.PRIESTS,
        IT.MERCANTILISM: SelectorateKind.SHAREHOLDERS,
        IT.MILITARISM: SelectorateKind.ARMY,
        IT.ASCETICISM: None,
        IT.RATIONALISM: SelectorateKind.COUNCIL,
        IT.NATURE_HARMONY: None,
        IT.XENOPHOBIA: None,
        IT.COSMOPOLITANISM: None,
        IT.ANTI_GOD: None,
        IT.CREATORISM: SelectorateKind.PRIESTS,
    },
)
RIGHTS: Mapping[IdeologyTenet, int] = total(
    IdeologyTenet,
    {
        IT.LEGALISM: 1,
        IT.RESTRAINT: 1,
        IT.EGALITARIANISM: 1,
        IT.DIVINE_RIGHT: -1,
        IT.MERCANTILISM: 0,
        IT.MILITARISM: -1,
        IT.ASCETICISM: 0,
        IT.RATIONALISM: 1,
        IT.NATURE_HARMONY: 0,
        IT.XENOPHOBIA: -1,
        IT.COSMOPOLITANISM: 1,
        IT.ANTI_GOD: 0,
        IT.CREATORISM: 0,
    },
)


async def tenets_held(ctx: TickContext, creed_id: int) -> list[IdeologyTenet]:
    return sorted(
        await ctx.session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creed_id)), key=lambda tenet: tenet.value
    )


async def creed_of(ctx: TickContext, creed_id: int) -> tuple[EntityRow, IdeologyProfileRow]:
    creed = await ctx.session.get(EntityRow, creed_id)
    profile = await ctx.session.get(IdeologyProfileRow, creed_id)
    if creed is None or profile is None or creed.entity_type is not EntityType.IDEOLOGY:
        raise NotFoundError("No such creed.")
    return creed, profile


async def give_tenets(ctx: TickContext, creed_id: int, profile: IdeologyProfileRow, tenets: list[IdeologyTenet]) -> None:
    for row in list(await ctx.session.scalars(select(IdeologyTenetRow).where(IdeologyTenetRow.ideology_entity_id == creed_id))):
        await ctx.session.delete(row)
    await ctx.session.flush()
    delta: dict[str, int] = {}
    for tenet in tenets:
        ctx.session.add(IdeologyTenetRow(ideology_entity_id=creed_id, tenet=tenet))
        for axis, value in IDEOLOGY_VALUES[tenet].items():
            delta[axis.value] = delta.get(axis.value, 0) + value
    profile.tenets, profile.value_delta, profile.updated_epoch = [tenet.value for tenet in tenets], delta, ctx.epoch


async def split_creed(ctx: TickContext, creed_id: int, community_id: int, dropped: IdeologyTenet | None, added: IdeologyTenet | None) -> EntityRow:
    creed, profile = await creed_of(ctx, creed_id)
    follower = await ctx.session.get(IdeologyAdherentRow, (creed_id, community_id))
    if follower is None:
        raise ValidationFailedError("Only a follower of the creed can split from it.")
    tenets = [tenet for tenet in await tenets_held(ctx, creed_id) if tenet is not dropped]
    if added is not None and added not in tenets:
        tenets.append(added)
    if not tenets:
        raise ValidationFailedError("A creed that splits keeps at least one tenet.")
    community = await ctx.session.get(EntityRow, community_id)
    name = f"{creed.name} of {community.name}" if community is not None else f"{creed.name} reformed"
    splinter = await create_record(
        ctx,
        RecordSpec(
            name=name,
            entity_type=EntityType.IDEOLOGY,
            stats=IdeologyStats(adherents=1, appeal=PERCENT // 4),
            body=f"A creed split from {creed.name}: {', '.join(tenet.value.replace('_', ' ') for tenet in tenets)}.",
            power=2,
            world_id=creed.world_id,
            location_id=community.location_id if community is not None else creed.location_id,
        ),
    )
    ctx.session.add(
        IdeologyProfileRow(
            ideology_entity_id=splinter.id,
            value_delta={},
            tenets=[],
            founder_entity_id=profile.founder_entity_id,
            appeal=dict(profile.appeal),
            texts=[],
            locked=[],
        )
    )
    await ctx.session.flush()
    fresh = await ctx.session.get(IdeologyProfileRow, splinter.id)
    if fresh is not None:
        await give_tenets(ctx, splinter.id, fresh, tenets)
    ctx.session.add(
        IdeologyAdherentRow(
            ideology_entity_id=splinter.id, adherent_entity_id=community_id, strength=follower.strength, state=follower.state, since_epoch=ctx.epoch
        )
    )
    await ctx.session.delete(follower)
    await note(ctx, f"{splinter.name} split from {creed.name}.", key="lore.creed_split", ids=[creed.id, splinter.id, community_id])
    return splinter


async def merge_creeds(ctx: TickContext, keeper_id: int, absorbed_id: int) -> EntityRow:
    if keeper_id == absorbed_id:
        raise ValidationFailedError("A creed cannot merge with itself.")
    keeper, profile = await creed_of(ctx, keeper_id)
    absorbed, _ = await creed_of(ctx, absorbed_id)
    tenets = list(dict.fromkeys([*await tenets_held(ctx, keeper_id), *await tenets_held(ctx, absorbed_id)]))[: ctx.rules.ideologies.founding_tenets + 1]
    await give_tenets(ctx, keeper_id, profile, tenets)
    for row in list(await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == absorbed_id))):
        kept = await ctx.session.get(IdeologyAdherentRow, (keeper_id, row.adherent_entity_id))
        if kept is None:
            ctx.session.add(
                IdeologyAdherentRow(
                    ideology_entity_id=keeper_id, adherent_entity_id=row.adherent_entity_id, strength=row.strength, state=row.state, since_epoch=ctx.epoch
                )
            )
        else:
            kept.strength, kept.state = max(kept.strength, row.strength), kept.state or row.state
        await ctx.session.delete(row)
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).where(PolityProfileRow.ideology_entity_id == absorbed_id))):
        realm.ideology_entity_id = keeper_id
    await retire_in(ctx, absorbed, f"merged into {keeper.name}", status=EntityStatus.DESTROYED)
    await note(ctx, f"{absorbed.name} merged into {keeper.name}.", key="lore.creed_merged", ids=[keeper.id, absorbed.id])
    return keeper


def distance(first: Mapping[ValueAxis, int], second: Mapping[ValueAxis, int], tenets: list[IdeologyTenet]) -> int:
    axes = {axis for tenet in tenets for axis in IDEOLOGY_VALUES[tenet]}
    return sum(abs(first.get(axis, 0) - second.get(axis, 0)) for axis in axes)


async def schisms(ctx: TickContext, creed: EntityRow) -> int:
    table = ctx.rules.ideologies
    tenets = await tenets_held(ctx, creed.id)
    followers = [
        row
        for row in await ctx.session.scalars(
            select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id).order_by(IdeologyAdherentRow.adherent_entity_id)
        )
    ]
    places = [
        row
        for row in followers
        if (place := await ctx.session.get(EntityRow, row.adherent_entity_id)) is not None and place.entity_type is not EntityType.MORTAL
    ]
    if len(places) < 2 or len(tenets) < 2 or held(creed.id):
        return 0
    first = await values_for(ctx.session, places[0].adherent_entity_id)
    for row in places[1:]:
        values = await values_for(ctx.session, row.adherent_entity_id)
        if distance(first, values, tenets) < table.split_distance or held(row.adherent_entity_id):
            continue
        if not ctx.rng(f"creed_split.{creed.id}.{row.adherent_entity_id}.{ctx.epoch}").chance(table.split_chance):
            continue
        dropped = max(tenets, key=lambda tenet: (distance(first, values, [tenet]), tenet.value))
        await split_creed(ctx, creed.id, row.adherent_entity_id, dropped, None)
        return 1
    return 0


async def syntheses(ctx: TickContext, creeds: list[EntityRow]) -> int:
    table = ctx.rules.ideologies
    merged = 0
    gone: set[int] = set()
    for index, first in enumerate(creeds):
        for second in creeds[index + 1 :]:
            if first.id in gone or second.id in gone or held(first.id, second.id):
                continue
            shared = set(await tenets_held(ctx, first.id)) & set(await tenets_held(ctx, second.id))
            places = set(await ctx.session.scalars(select(IdeologyAdherentRow.adherent_entity_id).where(IdeologyAdherentRow.ideology_entity_id == first.id)))
            common = await ctx.session.scalar(
                select(IdeologyAdherentRow.adherent_entity_id)
                .where(IdeologyAdherentRow.ideology_entity_id == second.id, IdeologyAdherentRow.adherent_entity_id.in_(places))
                .limit(1)
            )
            if len(shared) < table.merge_shared or common is None or not ctx.rng(f"creed_merge.{first.id}.{second.id}.{ctx.epoch}").chance(table.merge_chance):
                continue
            await merge_creeds(ctx, first.id, second.id)
            gone.add(second.id)
            merged += 1
    return merged


async def write_constitution(ctx: TickContext, polity_id: int, creed_id: int | None) -> ConstitutionRow:
    table = ctx.rules.ideologies
    tenets = await tenets_held(ctx, creed_id) if creed_id is not None else []
    regime = await ctx.session.get(RegimeRow, polity_id)
    chosen = next(
        (kind for tenet in tenets if (kind := SELECTORATES[tenet]) is not None), regime.selectorate if regime is not None else SelectorateKind.COUNCIL
    )
    rights = clamp_int(table.constitution_rights + sum(RIGHTS[tenet] for tenet in tenets) * table.rights_per_tenet, 0, PERCENT)
    row = await ctx.session.get(ConstitutionRow, polity_id)
    if row is None:
        row = ConstitutionRow(polity_entity_id=polity_id, selectorate=chosen, locked=[])
        ctx.session.add(row)
    for key, value in (("ideology_entity_id", creed_id), ("selectorate", chosen), ("offices", max(1, len(tenets) + 1)), ("rights", rights)):
        if key not in row.locked:
            setattr(row, key, value)
    row.written_epoch = ctx.epoch
    return row


async def keep_constitutions(ctx: TickContext) -> int:
    written = 0
    drift = ctx.rules.ideologies.constitution_drift
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).where(PolityProfileRow.ideology_entity_id.is_not(None)))):
        if held(realm.polity_entity_id):
            continue
        row = await ctx.session.get(ConstitutionRow, realm.polity_entity_id)
        if row is None or (row.ideology_entity_id != realm.ideology_entity_id and "ideology_entity_id" not in row.locked):
            row = await write_constitution(ctx, realm.polity_entity_id, realm.ideology_entity_id)
            written += 1
            await note(ctx, "A realm set down a constitution in the name of its creed.", key="lore.constitution_written", ids=[realm.polity_entity_id])
    for row in list(await ctx.session.scalars(select(ConstitutionRow))):
        regime = await ctx.session.get(RegimeRow, row.polity_entity_id)
        if regime is None or held(row.polity_entity_id):
            continue
        if "selectorate" not in regime.locked:
            regime.selectorate = row.selectorate
        if "public_share" not in regime.locked:
            regime.public_share = clamp_int(regime.public_share + round_half_up((row.rights - regime.public_share) * drift / PERCENT), 0, PERCENT)
    return written


async def media_factor(ctx: TickContext, mortal: EntityRow) -> float:
    return 1 + await family_level(ctx.session, mortal.id, TechFamily.COMMUNICATION) * ctx.rules.ideologies.media_pct / PERCENT
