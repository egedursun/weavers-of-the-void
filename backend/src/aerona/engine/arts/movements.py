from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.arts import ArtMovementRow, CanonWorkRow, CollectorRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.discovery import ArtFormProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import CanonPath
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_id_of
from aerona.engine.collective.crowds import mood_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.quota import WorldQuota
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import town_of
from aerona.engine.structures.readers import strength_at

MANIFESTO_AXES = 3
TEACHING = (StructureKind.SCHOOL, StructureKind.ACADEMY)
PATH_WEIGHT = {CanonPath.RENOWN: 60, CanonPath.COPYING: 50, CanonPath.INSTITUTION: 55, CanonPath.TEACHING: 45, CanonPath.MOVEMENT: 50}


@dataclass
class MovementTally:
    founded: int = 0
    scandals: int = 0
    orthodox: int = 0
    canonised: int = 0
    contested: int = 0
    dropped: int = 0
    taught: int = 0


async def makers_by_town(ctx: TickContext) -> dict[int, list[EntityRow]]:
    authors = select(ArtworkProfileRow.author_entity_id).where(ArtworkProfileRow.author_entity_id.is_not(None)).distinct()
    found: dict[int, list[EntityRow]] = defaultdict(list)
    for mortal in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(authors), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)):
        town = await town_of(ctx.session, mortal)
        if town is not None:
            found[town.id].append(mortal)
    return found


async def found_movement(ctx: TickContext, town: EntityRow, makers: list[EntityRow]) -> ArtMovementRow:
    faction = await found_faction(ctx, town, FactionKind.ART_MOVEMENT)
    lead = max(makers, key=lambda row: (row.power_level, -row.id))
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, lead.id)
    manifesto = {axis.value: value for axis, value in sorted(values.items(), key=lambda item: (-item[1], item[0].value))[:MANIFESTO_AXES]}
    forms = Counter(
        form
        for form in await ctx.session.scalars(
            select(ArtworkProfileRow.art_form_entity_id).where(
                ArtworkProfileRow.author_entity_id.in_([maker.id for maker in makers]), ArtworkProfileRow.art_form_entity_id.is_not(None)
            )
        )
    )
    form = min(forms.items(), key=lambda item: (-item[1], item[0]))[0] if forms else None
    row = ArtMovementRow(faction_entity_id=faction.id, manifesto=manifesto, art_form_entity_id=form, founded_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    for maker in makers:
        if await ctx.session.get(FactionMembershipRow, (faction.id, maker.id)) is None:
            ctx.session.add(FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=maker.id, joined_epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    await record(
        ctx,
        "arts.movement",
        roles={IncidentRole.PRODUCT: faction.id, IncidentRole.PLACE: town.id, IncidentRole.MEMBER: [maker.id for maker in makers]},
        facts={"art_form": form, "makers": len(makers)},
        steps=(StepDraft(StepAction.FOUND, target=faction.id),),
        place=town.id,
    )
    return row


async def found_movements(ctx: TickContext, tally: MovementTally) -> None:
    table = ctx.rules.art_movements
    homed = set(
        await ctx.session.scalars(
            select(FactionProfileRow.home_entity_id).where(FactionProfileRow.kind == FactionKind.ART_MOVEMENT, FactionProfileRow.home_entity_id.is_not(None))
        )
    )
    quota = WorldQuota(table.movements_per_epoch)
    for town_id, makers in ctx.rng("movement.order").shuffled(sorted((await makers_by_town(ctx)).items())):
        town = await living_entity(ctx.session, town_id)
        if town is None or quota.full(town.world_id) or held(town.id) or town_id in homed or len(makers) < table.found_artists:
            continue
        if ctx.rng(f"movement.{town_id}").chance(table.found_chance):
            await found_movement(ctx, town, makers)
            quota.take(town.world_id)
            tally.founded += 1


async def canon_room(ctx: TickContext, people_id: int) -> int:
    table = ctx.rules.canon
    people = await ctx.session.get(EntityRow, people_id)
    population = stat_or(people, "population", 0) if people is not None else 0
    return table.canon_size + (population // table.canon_people_per_work if table.canon_people_per_work > 0 else 0)


async def people_of_faction(ctx: TickContext, faction_id: int) -> int | None:
    profile = await ctx.session.get(FactionProfileRow, faction_id)
    home = await ctx.session.get(EntityRow, profile.home_entity_id) if profile is not None and profile.home_entity_id is not None else None
    return await people_id_of(ctx.session, home)


async def tend_movements(ctx: TickContext, tally: MovementTally) -> None:
    table = ctx.rules.art_movements
    rows = list(await ctx.session.scalars(select(ArtMovementRow).order_by(ArtMovementRow.faction_entity_id)))
    for row in rows:
        faction = await living_entity(ctx.session, row.faction_entity_id)
        if faction is None or held(faction.id):
            continue
        if row.art_form_entity_id is not None and "patrons" not in row.locked:
            row.patrons = len(
                list(await ctx.session.scalars(select(CollectorRow.holder_entity_id).where(CollectorRow.taste_form_entity_id == row.art_form_entity_id)))
            )
        profile = await ctx.session.get(FactionProfileRow, faction.id)
        home = await living_entity(ctx.session, profile.home_entity_id) if profile is not None else None
        if home is not None and not held(home.id) and ctx.rng(f"scandal.{faction.id}.{ctx.epoch}").chance(table.scandal_chance):
            mood = await mood_of(ctx, home.id)
            if "agitation" not in mood.locked:
                mood.agitation = clamp_int(mood.agitation + table.scandal_agitation, 0, PERCENT)
            row.scandals += 1
            tally.scandals += 1
            await record(
                ctx,
                "arts.scandal",
                roles={IncidentRole.ACTOR: faction.id, IncidentRole.PLACE: home.id},
                facts={"agitation": table.scandal_agitation, "scandals": row.scandals},
                steps=(StepDraft(StepAction.SHAME, actor=faction.id, target=home.id),),
                place=home.id,
            )
        if not row.orthodoxy and row.patrons >= table.orthodoxy_patrons and "orthodoxy" not in row.locked:
            people = await people_of_faction(ctx, faction.id)
            for other in rows:
                if other is not row and other.orthodoxy and "orthodoxy" not in other.locked and await people_of_faction(ctx, other.faction_entity_id) == people:
                    other.orthodoxy = False
            row.orthodoxy = True
            tally.orthodox += 1
            await record(ctx, "arts.orthodox", roles={IncidentRole.SUBJECT: faction.id, IncidentRole.MEMBER: people}, facts={"patrons": row.patrons})


async def orthodox_makers(ctx: TickContext) -> set[int]:
    orthodox = select(ArtMovementRow.faction_entity_id).where(ArtMovementRow.orthodoxy.is_(True))
    return set(await ctx.session.scalars(select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id.in_(orthodox))))


async def path_for(ctx: TickContext, artwork: EntityRow, profile: ArtworkProfileRow, orthodox: set[int]) -> CanonPath | None:
    table = ctx.rules.canon
    if profile.quality >= table.renown_quality and ctx.epoch - artwork.birth_epoch >= table.age_epochs:
        return CanonPath.RENOWN
    if profile.copies >= table.copies:
        return CanonPath.COPYING
    patron = await ctx.session.get(EntityRow, profile.patron_entity_id) if profile.patron_entity_id is not None else None
    if patron is not None and patron.entity_type is EntityType.CULT:
        return CanonPath.INSTITUTION
    if profile.author_entity_id is not None and profile.author_entity_id in orthodox:
        return CanonPath.MOVEMENT
    town = await town_of(ctx.session, artwork)
    if town is not None and await strength_at(ctx.session, town.id, TEACHING) > 0:
        return CanonPath.TEACHING
    return None


async def people_of_work(ctx: TickContext, artwork: EntityRow, profile: ArtworkProfileRow) -> int | None:
    author = await ctx.session.get(EntityRow, profile.author_entity_id) if profile.author_entity_id is not None else None
    for holder in (author, artwork):
        folk = await people_id_of(ctx.session, await town_of(ctx.session, holder)) if holder is not None else None
        if folk is not None:
            return folk
    return None


async def form_canon(ctx: TickContext, tally: MovementTally) -> None:
    orthodox = await orthodox_makers(ctx)
    works = await ctx.session.execute(
        select(EntityRow, ArtworkProfileRow)
        .join(ArtworkProfileRow, ArtworkProfileRow.artwork_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for artwork, profile in list(works):
        if held(artwork.id):
            continue
        people = await people_of_work(ctx, artwork, profile)
        if people is None or await ctx.session.get(CanonWorkRow, (people, artwork.id)) is not None:
            continue
        path = await path_for(ctx, artwork, profile, orthodox)
        if path is None:
            continue
        size = len(list(await ctx.session.scalars(select(CanonWorkRow.artwork_entity_id).where(CanonWorkRow.people_entity_id == people))))
        if size >= await canon_room(ctx, people):
            continue
        ctx.session.add(
            CanonWorkRow(people_entity_id=people, artwork_entity_id=artwork.id, path=path, weight=PATH_WEIGHT[path], since_epoch=ctx.epoch, locked=[])
        )
        if "canon" not in profile.locked:
            profile.canon = True
        tally.canonised += 1
        await record(
            ctx,
            "arts.canonised",
            roles={IncidentRole.SUBJECT: artwork.id, IncidentRole.MEMBER: people},
            facts={"path": path, "weight": PATH_WEIGHT[path]},
            steps=(StepDraft(StepAction.HONOUR, target=artwork.id),),
        )
    await ctx.session.flush()


async def contest_canon(ctx: TickContext, tally: MovementTally) -> None:
    table = ctx.rules.canon
    rows = list(await ctx.session.scalars(select(CanonWorkRow).order_by(CanonWorkRow.people_entity_id, CanonWorkRow.artwork_entity_id)))
    movements = list(await ctx.session.scalars(select(ArtMovementRow.faction_entity_id).order_by(ArtMovementRow.faction_entity_id)))
    rivals_by_people: dict[int, int] = defaultdict(int)
    for faction_id in movements:
        people = await people_of_faction(ctx, faction_id)
        if people is not None:
            rivals_by_people[people] += 1
    for row in rows:
        if held(row.artwork_entity_id) or rivals_by_people.get(row.people_entity_id, 0) < 2:
            continue
        if not ctx.rng(f"contest.{row.people_entity_id}.{row.artwork_entity_id}.{ctx.epoch}").chance(table.contest_chance):
            continue
        row.contested = True
        if "weight" not in row.locked:
            row.weight = max(0, row.weight - table.contest_loss)
        tally.contested += 1
        if row.weight == 0:
            profile = await ctx.session.get(ArtworkProfileRow, row.artwork_entity_id)
            await ctx.session.delete(row)
            if profile is not None and "canon" not in profile.locked:
                profile.canon = False
            tally.dropped += 1
    await ctx.session.flush()


async def canon_message(ctx: TickContext, rows: list[CanonWorkRow]) -> dict[ValueAxis, float]:
    total: dict[ValueAxis, float] = defaultdict(float)
    weights: dict[ValueAxis, int] = defaultdict(int)
    for row in rows:
        profile = await ctx.session.get(ArtworkProfileRow, row.artwork_entity_id)
        for key, value in (profile.message if profile is not None else {}).items():
            if key in ValueAxis.__members__.values():
                axis = ValueAxis(key)
                total[axis] += value * row.weight
                weights[axis] += row.weight
    return {axis: total[axis] / weights[axis] for axis in total if weights[axis]}


async def teach_canon(ctx: TickContext, tally: MovementTally) -> None:
    pull = ctx.rules.canon.value_pull
    by_people: dict[int, list[CanonWorkRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(CanonWorkRow).order_by(CanonWorkRow.people_entity_id, CanonWorkRow.artwork_entity_id)):
        by_people[row.people_entity_id].append(row)
    for people_id, rows in sorted(by_people.items()):
        if held(people_id) or not pull:
            continue
        message = await canon_message(ctx, rows)
        if not message:
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people_id)
        shifted = {
            axis: clamp_int(values.get(axis, 0) + round_half_up((message[axis] - values.get(axis, 0)) * pull / PERCENT), -PERCENT, PERCENT)
            if axis in message
            else values.get(axis, 0)
            for axis in {*values, *message}
        }
        await write_values(ctx.session, ValueHolder.CULTURE, people_id, shifted)
        tally.taught += 1


async def honour_forms(ctx: TickContext) -> None:
    step = ctx.rules.canon.form_prestige
    forms = Counter(
        form
        for form in await ctx.session.scalars(
            select(ArtworkProfileRow.art_form_entity_id)
            .join(CanonWorkRow, CanonWorkRow.artwork_entity_id == ArtworkProfileRow.artwork_entity_id)
            .where(ArtworkProfileRow.art_form_entity_id.is_not(None))
        )
        if form is not None
    )
    for form_id, works in sorted(forms.items()):
        form = await ctx.session.get(ArtFormProfileRow, form_id)
        if form is not None and not held(form_id) and "prestige" not in form.locked:
            form.prestige = max(form.prestige, clamp_int(works * step, 0, PERCENT))


async def keep_movements(ctx: TickContext, tally: MovementTally) -> None:
    await found_movements(ctx, tally)
    await tend_movements(ctx, tally)
    await form_canon(ctx, tally)
    await contest_canon(ctx, tally)
    await teach_canon(ctx, tally)
    await honour_forms(ctx)
    await ctx.session.flush()
