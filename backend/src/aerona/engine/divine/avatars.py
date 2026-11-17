from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.divine import AvatarRow
from aerona.db.tables.dominion import GodDesignRow, GodImageRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, god_of
from aerona.engine.divine.standing import standing_row
from aerona.engine.divine.wounds import manifestation_broken
from aerona.engine.primitives.faith import change_religion
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.recording.record import record


async def avatars_of(ctx: TickContext, god_id: int) -> list[AvatarRow]:
    return list(await ctx.session.scalars(select(AvatarRow).where(AvatarRow.god_node_id == god_id).order_by(AvatarRow.avatar_entity_id)))


async def manifest(ctx: TickContext, god: God, place: EntityRow) -> EntityRow:
    table = ctx.rules.avatars
    if await manifestation_broken(ctx.session, god.id):
        raise ValidationFailedError(f"{god.name}'s manifestation is shattered; it cannot take a mortal form until it heals.")
    if len(await avatars_of(ctx, god.id)) >= table.max_per_god:
        raise ValidationFailedError(f"{god.name} already walks the world in {table.max_per_god} mortal forms.")
    if place.entity_type not in COMMUNITY_TYPES and place.entity_type is not EntityType.REGION:
        raise ValidationFailedError("An avatar must walk among a people, a settlement or a land.")
    design = await ctx.session.get(GodDesignRow, god.id)
    image = await ctx.session.get(GodImageRow, god.id)
    floor = ctx.rules.god_design.manifestation_floor_pct / PERCENT
    vigour = floor + (1 - floor) * (design.manifestation_strength if design is not None else PERCENT) / PERCENT
    seen = f" Its peoples see it as {spoken(image.manifestation)}." if image is not None else ""
    avatar = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{god.name} in mortal form",
            entity_type=EntityType.MORTAL,
            body=f"The mortal form of {god.name}.{seen}",
            stats=MortalStats(
                hp=max(1, round_half_up(table.hp * vigour)),
                strength=clamp_percent(god.strength),
                agility=clamp_percent(god.agility),
                intellect=clamp_percent(god.wisdom),
                charisma=clamp_percent(god.charisma),
                age=table.age,
                lifespan=table.lifespan,
            ),
            power=clamp_int(round_half_up(god.might * vigour), 1, PERCENT),
            location_id=place.id,
            world_id=place.world_id,
            mortal_role=MortalRole.CHOSEN,
            subtype="avatar",
            creator_son_id=god.id if isinstance(god, SonRow) else None,
        ),
    )
    ctx.session.add(AvatarRow(avatar_entity_id=avatar.id, god_node_id=god.id, world_id=place.world_id, since_epoch=ctx.epoch, deeds=0, locked=[]))
    await ctx.session.flush()
    await record(
        ctx,
        "divine.avatar_manifest",
        roles={IncidentRole.SUBJECT: [place.id, avatar.id]},
        facts={"god": str(god.name)},
        son_id=god.id if isinstance(god, SonRow) else None,
    )
    return avatar


async def walk(ctx: TickContext, row: AvatarRow, avatar: EntityRow, god: God) -> bool:
    table = ctx.rules.avatars
    place = await ctx.session.get(EntityRow, avatar.location_id) if avatar.location_id is not None else None
    if place is None or place.status is not EntityStatus.CANON or place.entity_type not in COMMUNITY_TYPES:
        return False
    standing = await standing_row(ctx, place.id, god.id)
    for axis, gain in (("awe", table.presence_awe), ("love", table.presence_love)):
        if axis not in standing.locked:
            setattr(standing, axis, clamp_percent(getattr(standing, axis) + gain))
    if "deeds" not in row.locked:
        row.deeds += 1
    book = await ctx.divine()
    gods, _ = await book.faithful_of(ctx.session, place.id)
    if god.id in gods or held(place.id) or not ctx.rng(f"avatar_preach.{avatar.id}").chance(table.preach_chance):
        return False
    if not await change_religion(ctx.session, place, god.id, ctx.epoch, f"won over by {avatar.name}"):
        return False
    await record(ctx, "divine.avatar_converts", roles={IncidentRole.ACTOR: avatar.id, IncidentRole.SUBJECT: place.id}, facts={"god": str(god.name)})
    return True


async def avatar_cycles(ctx: TickContext) -> int:
    converted = 0
    for row in list(await ctx.session.scalars(select(AvatarRow).order_by(AvatarRow.avatar_entity_id))):
        avatar = await ctx.session.get(EntityRow, row.avatar_entity_id)
        god = await god_of(ctx.session, row.god_node_id)
        if avatar is None or god is None or avatar.status is not EntityStatus.CANON or held(avatar.id, god.id):
            continue
        converted += 1 if await walk(ctx, row, avatar, god) else 0
    return converted


async def withdraw(ctx: TickContext, avatar_id: int) -> None:
    row = await ctx.session.get(AvatarRow, avatar_id)
    avatar = await ctx.session.get(EntityRow, avatar_id)
    if row is None or avatar is None:
        raise ValidationFailedError("No such avatar.")
    await ctx.session.delete(row)
    avatar.end_epoch = ctx.epoch
    avatar.status = EntityStatus.DESTROYED
    await ctx.session.flush()
