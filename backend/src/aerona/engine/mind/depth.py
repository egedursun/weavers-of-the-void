import re

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.backfill_words import LOCAL_TRAIT_WORDS
from aerona.catalog.mind import DEPTH_WORDS, TRAITS
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import TraitKind, TraitSource, ValueHolder
from aerona.engine.mind.book import add_trait, clamp_value, stored_values, traits_of, write_values
from aerona.rules.registry import Rules

DEPTH_FIXUP = "mind.depth_personality"
LOCAL_DEPTH_FIXUP = "mind.depth_personality_local"


def depth_text(mortal: EntityRow) -> str:
    depth = mortal.depth
    if depth is None:
        return ""
    return " ".join(f"{key} {value}" for key, value in depth.specifics.items()).lower()


def mentions(text: str, trait: TraitKind) -> bool:
    if any(re.search(rf"\b{re.escape(word)}\b", text) for word in DEPTH_WORDS.get(trait, ())):
        return True
    return any(re.search(rf"(?<![^\W\d_]){re.escape(word)}", text) for word in LOCAL_TRAIT_WORDS.get(trait, ()))


def read_depth(text: str) -> list[TraitKind]:
    if not text:
        return []
    found: list[TraitKind] = []
    for trait in dict.fromkeys([*DEPTH_WORDS, *LOCAL_TRAIT_WORDS]):
        if mentions(text, trait):
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
    added = 0
    for key in (DEPTH_FIXUP, LOCAL_DEPTH_FIXUP):
        if not await fixup_due(session, key):
            continue
        found = 0
        for mortal in mortals:
            if mortal.entity_type is EntityType.MORTAL:
                found += await apply_depth(session, rules, mortal, epoch, shift_values=True)
        session.add(AppliedFixupRow(key=key, result={"traits": found}))
        await session.flush()
        added += found
    return added
