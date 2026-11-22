from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import expose
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mortal.standing import add_stress, shift_standing
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import shift_stat


@dataclass(frozen=True)
class Cursed:
    item: EntityRow
    bearer: EntityRow
    strength: int

    def part(self, pct: int) -> int:
        return max(1, round_half_up(self.strength * pct / PERCENT))


WIDER_CURSES: Handlers[CurseKind, Callable[[TickContext, Cursed], Awaitable[None]]] = Handlers(CurseKind)


@WIDER_CURSES.on(CurseKind.BARRENNESS)
async def barren(ctx: TickContext, cursed: Cursed) -> None:
    await shift_standing(ctx.session, cursed.bearer, "fertility", -cursed.part(ctx.rules.item_curses.wider_pct), ctx.epoch, default=0)


@WIDER_CURSES.on(CurseKind.TRANSFORMATION)
async def transform(ctx: TickContext, cursed: Cursed) -> None:
    if ctx.rng(f"curse.transform.{cursed.item.id}.{ctx.epoch}").chance(cursed.part(ctx.rules.item_curses.wider_pct)):
        await add_flag(ctx.session, cursed.bearer.id, EntityFlag.MUTATED, ctx.epoch)


@WIDER_CURSES.on(CurseKind.SLEEP)
async def sleep(ctx: TickContext, cursed: Cursed) -> None:
    if ctx.rng(f"curse.sleep.{cursed.item.id}.{ctx.epoch}").chance(cursed.part(ctx.rules.item_curses.wider_pct)):
        await add_flag(ctx.session, cursed.bearer.id, EntityFlag.DORMANT, ctx.epoch)


@WIDER_CURSES.on(CurseKind.SILENCE)
async def silence(ctx: TickContext, cursed: Cursed) -> None:
    await shift_standing(ctx.session, cursed.bearer, "renown", -cursed.part(ctx.rules.item_curses.wider_pct), ctx.epoch, default=0)


@WIDER_CURSES.on(CurseKind.HUNGER)
async def hunger(ctx: TickContext, cursed: Cursed) -> None:
    if cursed.bearer.entity_type is EntityType.MORTAL:
        harm = Harm(damage=cursed.part(ctx.rules.item_curses.wasting_pct), cause=HarmCause.CURSE, death_cause=f"starved under the curse of {cursed.item.name}")
        await apply_hits(ctx, cursed.bearer, harm)


@WIDER_CURSES.on(CurseKind.FORGETTING)
async def forget(ctx: TickContext, cursed: Cursed) -> None:
    best = await ctx.session.scalar(select(SkillRow).where(SkillRow.holder_node_id == cursed.bearer.id).order_by(SkillRow.level.desc()).limit(1))
    if best is not None and not held(cursed.bearer.id):
        best.level = max(0, best.level - cursed.part(ctx.rules.item_curses.wider_pct))


@WIDER_CURSES.on(CurseKind.RESTLESSNESS)
async def wander(ctx: TickContext, cursed: Cursed) -> None:
    if cursed.bearer.entity_type is EntityType.MORTAL:
        await add_stress(ctx.session, cursed.bearer.id, cursed.part(ctx.rules.item_curses.wider_pct), ctx.epoch)


@WIDER_CURSES.on(CurseKind.LINE_CURSE)
async def curse_line(ctx: TickContext, cursed: Cursed) -> None:
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == cursed.bearer.id).limit(1))
    profile = await ctx.session.get(HouseProfileRow, house) if house is not None and not held(house) else None
    if profile is not None and "prestige" not in profile.locked:
        profile.prestige = clamp_int(profile.prestige - cursed.part(ctx.rules.item_curses.wider_pct), 0, PERCENT)


@WIDER_CURSES.on(CurseKind.PLACE_CURSE)
async def curse_place(ctx: TickContext, cursed: Cursed) -> None:
    place = cursed.bearer.location_id
    profile = await ctx.session.get(SettlementProfileRow, place) if place is not None and not held(place) else None
    if profile is not None and "sanitation" not in profile.locked:
        profile.sanitation = clamp_int(profile.sanitation - cursed.part(ctx.rules.item_curses.wider_pct), 0, PERCENT)


@WIDER_CURSES.on(CurseKind.COMPULSION)
async def compel(ctx: TickContext, cursed: Cursed) -> None:
    shift_stat(cursed.bearer, "willpower", -cursed.part(ctx.rules.item_curses.wider_pct), 0)


@WIDER_CURSES.on(CurseKind.AGING)
async def age(ctx: TickContext, cursed: Cursed) -> None:
    if cursed.bearer.entity_type is EntityType.MORTAL:
        shift_stat(cursed.bearer, "age", ctx.rules.item_curses.aging_years, 0)


@WIDER_CURSES.on(CurseKind.EXPOSURE)
async def lay_bare(ctx: TickContext, cursed: Cursed) -> None:
    secret = await ctx.session.scalar(
        select(SecretRow).where(SecretRow.about_node_id == cursed.bearer.id, SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.id).limit(1)
    )
    if secret is not None:
        await expose(ctx, secret)
