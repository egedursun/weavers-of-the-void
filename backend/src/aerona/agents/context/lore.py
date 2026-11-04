from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.techniques import TECHNIQUES
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import (
    HolderTechniqueRow,
    IdeologyTenetRow,
    ItemProfileRow,
    LanguageRegisterRow,
    LanguageStandingRow,
    LegendProfileRow,
    ProphecyConditionRow,
    RiteProfileRow,
    TraditionEffectRow,
    TraditionProfileRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ProphecyState
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.lore.language import tongues_of

BELIEVED = 50
RENOWNED = 40


def words(value: str) -> str:
    return value.replace("_", " ")


@dataclass
class LoreLines:
    tongues: list[str] = field(default_factory=list)
    techniques: list[str] = field(default_factory=list)
    creed: str = ""
    legends: list[str] = field(default_factory=list)
    traditions: list[str] = field(default_factory=list)
    prophecies: list[str] = field(default_factory=list)
    rites: list[str] = field(default_factory=list)
    treasures: list[str] = field(default_factory=list)


async def linked(session: AsyncSession, source: int, kinds: list[BondKind]) -> list[int]:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == source, BondRow.kind.in_(kinds), BondRow.state == BondState.ACTIVE)
    return list(await session.scalars(statement.order_by(BondRow.id)))


async def tongue_lines(session: AsyncSession, home_id: int) -> list[str]:
    found = []
    for language_id in sorted(await tongues_of(session, home_id)):
        language = await session.get(EntityRow, language_id)
        standing = await session.get(LanguageStandingRow, language_id)
        if language is None:
            continue
        marks = [f"prestige {standing.prestige}"] if standing is not None else []
        if standing is not None and standing.lingua_franca:
            marks.append("the tongue of the trade roads")
        if standing is not None and standing.liturgical:
            marks.append("a holy tongue")
        registers = await session.scalars(
            select(LanguageRegisterRow.register).where(LanguageRegisterRow.holder_entity_id == home_id, LanguageRegisterRow.language_entity_id == language_id)
        )
        marks.extend(f"spoken at {words(register.value)}" for register in sorted(set(registers)))
        found.append(f"{language.name} ({', '.join(marks)})" if marks else language.name)
    return found


async def creed_line(session: AsyncSession, realm_id: int | None) -> str:
    profile = await session.get(PolityProfileRow, realm_id) if realm_id is not None else None
    creed = await session.get(EntityRow, profile.ideology_entity_id) if profile is not None and profile.ideology_entity_id is not None else None
    if creed is None:
        return ""
    tenets = [words(tenet.value) for tenet in await session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creed.id))]
    return f"{creed.name} ({', '.join(sorted(tenets))})" if tenets else creed.name


async def legend_lines(session: AsyncSession, home_id: int) -> list[str]:
    found = []
    for legend_id in await linked(session, home_id, [BondKind.CELEBRATES, BondKind.TELLS_OF]):
        row = await session.get(LegendProfileRow, legend_id)
        legend = await session.get(EntityRow, legend_id)
        if row is not None and legend is not None and legend.status is EntityStatus.CANON and row.credence >= BELIEVED:
            fixed = ", fixed in a work" if row.fixed_in_entity_id is not None else f", distorted {row.distortion}%"
            found.append(f"{legend.name} (a tale of {words(row.archetype.value)}, believed {row.credence}%{fixed})")
    return found


async def tradition_lines(session: AsyncSession, home_id: int) -> list[str]:
    found = []
    for tradition_id in await linked(session, home_id, [BondKind.CELEBRATES]):
        row = await session.get(TraditionProfileRow, tradition_id)
        tradition = await session.get(EntityRow, tradition_id)
        if row is not None and tradition is not None and tradition.status is EntityStatus.CANON:
            taboo = f", nothing of {words(row.taboo_target)}" if row.taboo_target else ""
            deed = f", never {words(row.taboo_act.value)}" if row.taboo_act is not None else ""
            season = f", kept at {words(row.calendar_slot.value)}" if row.calendar_slot is not None else ""
            brings = await session.scalars(select(TraditionEffectRow.effect).where(TraditionEffectRow.tradition_entity_id == tradition_id))
            gifts = sorted({words(effect.value) for effect in brings})
            brought = f"; it brings {', '.join(gifts)}" if gifts else ""
            found.append(f"{tradition.name} ({words(row.kind.value)}{taboo}{deed}{season}{brought})")
    return found


async def prophecy_lines(session: AsyncSession, named: set[int]) -> list[str]:
    found = []
    for row in await session.scalars(select(ProphecyConditionRow).where(ProphecyConditionRow.state == ProphecyState.PENDING)):
        values = {int(value) for value in row.args.values() if isinstance(value, int) or (isinstance(value, str) and value.isdigit())}
        if not values & named and not set(row.audience) & named:
            continue
        prophecy = await session.get(EntityRow, row.prophecy_entity_id)
        if prophecy is not None:
            deadline = f", before epoch {row.deadline_epoch}" if row.deadline_epoch is not None else ""
            found.append(f"{prophecy.name} (foretells: {words(row.predicate.value)}{deadline})")
    return found


async def lore_lines(session: AsyncSession, me: EntityRow, home: EntityRow, realm_id: int | None, house_id: int | None) -> LoreLines:
    held = await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == home.id))
    owned = await linked(session, me.id, [BondKind.OWNS])
    rites = []
    treasures = []
    for target in owned:
        rite = await session.get(RiteProfileRow, target)
        item = await session.get(ItemProfileRow, target)
        entity = await session.get(EntityRow, target)
        if entity is None or entity.status is not EntityStatus.CANON:
            continue
        if rite is not None:
            rites.append(f"{entity.name} ({words(rite.school.value)}, power {rite.power})")
        if item is not None and (item.renown >= RENOWNED or item.regalia_of_entity_id is not None):
            treasures.append(f"{entity.name} ({words(item.item_class.value)}, renown {item.renown})")
    named = {me.id, home.id, *([realm_id] if realm_id is not None else []), *([house_id] if house_id is not None else [])}
    return LoreLines(
        tongues=await tongue_lines(session, home.id),
        techniques=sorted(TECHNIQUES[technique].label for technique in held),
        creed=await creed_line(session, realm_id),
        legends=await legend_lines(session, home.id),
        traditions=await tradition_lines(session, home.id),
        prophecies=await prophecy_lines(session, named),
        rites=rites,
        treasures=treasures,
    )
