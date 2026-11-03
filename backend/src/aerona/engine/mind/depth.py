import re

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import DEPTH_WORDS, TRAITS
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import TraitKind, TraitSource, ValueHolder
from aerona.engine.mind.book import add_trait, clamp_value, stored_values, traits_of, write_values
from aerona.rules.registry import Rules

DEPTH_FIXUP = "mind.depth_personality"


def depth_text(mortal: EntityRow) -> str:
    depth = mortal.depth
    if depth is None:
        return ""
    return " ".join(f"{key} {value}" for key, value in depth.specifics.items()).lower()


def read_depth(text: str) -> list[TraitKind]:
    if not text:
        return []
    found: list[TraitKind] = []
    for trait, words in DEPTH_WORDS.items():
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            opposite = TRAITS[trait].opposite
            if opposite not in found:
                found.append(trait)
    return found


async def apply_depth(session: AsyncSession, rules: Rules, mortal: EntityRow, epoch: int, *, shift_values: bool) -> int:
    added = 0
    for trait in read_depth(depth_text(mortal)):
        if len(await traits_of(session, mortal.id)) >= rules.traits.max_traits and trait not in await traits_of(session, mortal.id):
            break
        if not await add_trait(session, mortal.id, trait, TraitSource.BIRTH, epoch):
            continue
        added += 1
        if shift_values:
            values = dict(await stored_values(session, ValueHolder.PERSONAL, mortal.id))
            for axis, value in TRAITS[trait].values.items():
                values[axis] = clamp_value(values.get(axis, 0) + value * rules.culture_drift.trait_value_pct / PERCENT)
            await write_values(session, ValueHolder.PERSONAL, mortal.id, values)
    return added


async def backfill_depth(session: AsyncSession, rules: Rules, mortals: list[EntityRow], epoch: int) -> int:
    if await session.get(AppliedFixupRow, DEPTH_FIXUP) is not None:
        return 0
    added = 0
    for mortal in mortals:
        if mortal.entity_type is EntityType.MORTAL:
            added += await apply_depth(session, rules, mortal, epoch, shift_values=True)
    session.add(AppliedFixupRow(key=DEPTH_FIXUP, result={"traits": added}))
    await session.flush()
    return added
