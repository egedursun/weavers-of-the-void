from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionScale
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.factions.book import move_member
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat

COHESION_GAIN = 30
OFFSHOOT_COHESION = 80


async def found_offshoot(
    ctx: TickContext,
    parent: EntityRow,
    profile: FactionProfileRow,
    *,
    name: str,
    body: str,
    share_pct: int,
    leaving: list[FactionMembershipRow],
) -> EntityRow:
    share = clamp_int(share_pct, 0, PERCENT) / PERCENT
    child = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=name,
            body=body,
            stats=FactionStats(
                strength=round_half_up((stat(parent, "strength") or 0) * share),
                wealth=round_half_up((stat(parent, "wealth") or 0) * share),
                sway=round_half_up((stat(parent, "sway") or 0) * share),
            ),
            power=max(1, parent.power_level - 1),
            location_id=parent.location_id,
            world_id=parent.world_id,
            subtype=parent.subtype,
            engine_kind=parent.engine_kind,
            affiliated_entity_id=parent.affiliated_entity_id,
            pending=False,
        ),
    )
    taken = round_half_up(profile.treasury * share)
    ctx.session.add(
        FactionProfileRow(
            faction_entity_id=child.id,
            kind=profile.kind,
            scale=FactionScale.BAND,
            treasury=taken,
            cohesion=OFFSHOOT_COHESION,
            secrecy=profile.secrecy,
            armed=profile.armed,
            reputation=profile.reputation,
            influence_over={},
            cohort_share={},
            home_entity_id=profile.home_entity_id,
            outlawed=profile.outlawed,
            pay=profile.pay,
            loyalty=50,
            unpaid_epochs=0,
            founded_epoch=ctx.epoch,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    profile.treasury -= taken
    profile.cohesion = clamp_int(profile.cohesion + COHESION_GAIN, 0, PERCENT)
    for key in ("strength", "wealth", "sway"):
        if stat(parent, key) is not None:
            set_stats(parent, **{key: max(0, (stat(parent, key) or 0) - (stat(child, key) or 0))})
    for row in leaving:
        await move_member(ctx.session, row, child.id, ctx.epoch)
    await ctx.session.flush()
    return child
