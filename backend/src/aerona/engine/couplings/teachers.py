from sqlalchemy import Select, select

from aerona.catalog.bonds import bond_fits
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.couplings import TeachingRow
from aerona.db.tables.culture import ArtworkProfileRow, HolderTechniqueRow, RiteProfileRow
from aerona.db.tables.discovery import ArtFormPractitionerRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.place import PlaceSecretRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import AccountKind, AccountMedium
from aerona.domain.enums.couplings import TeachingKind, TeachingState
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.collective.accounts import RECORDED
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.faith.book import faith_tenets
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.intrigue.names import teach_name
from aerona.engine.lore.art_forms import practise
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import connect, top_region
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record as record_incident

HOSTILE_TEMPERS = frozenset({BeastTemper.ENRAGED})


async def origin_of(ctx: TickContext, teacher: EntityRow) -> EntityRow | None:
    bond = await ctx.session.scalar(
        select(BondRow).where(BondRow.source_node_id == teacher.id, BondRow.kind == BondKind.DESCENDS_FROM, BondRow.state == BondState.ACTIVE).limit(1)
    )
    return await ctx.session.get(EntityRow, bond.target_node_id) if bond is not None else None


async def taught(ctx: TickContext, teacher_id: int, learner_id: int, kind: TeachingKind) -> bool:
    found = await ctx.session.scalar(
        select(TeachingRow.id).where(TeachingRow.teacher_node_id == teacher_id, TeachingRow.learner_entity_id == learner_id, TeachingRow.kind == kind).limit(1)
    )
    return found is not None


async def barred(ctx: TickContext, teacher_id: int, learner_id: int) -> bool:
    found = await ctx.session.scalar(
        select(TeachingRow.id)
        .where(TeachingRow.teacher_node_id == teacher_id, TeachingRow.learner_entity_id == learner_id, TeachingRow.state == TeachingState.BLOCKED)
        .limit(1)
    )
    return found is not None


async def owned(ctx: TickContext, holder_id: int, targets: Select[tuple[int]] | Select[int]) -> list[int]:
    statement = select(BondRow.target_node_id).where(
        BondRow.source_node_id == holder_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(targets)
    )
    return list(await ctx.session.scalars(statement.order_by(BondRow.target_node_id)))


async def give_rite(ctx: TickContext, sources: list[int], learner: EntityRow) -> int | None:
    rites = select(RiteProfileRow.rite_entity_id)
    known = set(await owned(ctx, learner.id, rites))
    for source in sources:
        for rite in await owned(ctx, source, rites):
            if rite not in known:
                await connect(ctx.session, learner.id, rite, BondKind.OWNS, ctx.epoch, description="taught by the dead")
                return rite
    return None


async def give_technique(ctx: TickContext, sources: list[int], learner: EntityRow) -> int | None:
    known = set(await ctx.session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == learner.id)))
    for source in sources:
        for row in await ctx.session.scalars(
            select(HolderTechniqueRow).where(HolderTechniqueRow.holder_entity_id == source).order_by(HolderTechniqueRow.technique)
        ):
            if row.technique not in known:
                ctx.session.add(HolderTechniqueRow(holder_entity_id=learner.id, technique=row.technique, since_epoch=ctx.epoch, secret=False))
                return source
    return None


async def give_name(ctx: TickContext, sources: list[int], learner: EntityRow) -> int | None:
    for row in await ctx.session.scalars(select(TrueNameRow).order_by(TrueNameRow.bearer_node_id)):
        if any(source in row.known_by for source in sources) and await teach_name(ctx, row, learner.id):
            return row.bearer_node_id
    return None


async def give_language(ctx: TickContext, sources: list[int], learner: EntityRow) -> int | None:
    languages = select(EntityRow.id).where(EntityRow.entity_type == EntityType.LANGUAGE)
    spoken = set(await ctx.session.scalars(select(BondRow.target_node_id).where(BondRow.source_node_id == learner.id, BondRow.kind == BondKind.SPEAKS)))
    for source in sources:
        for language in await ctx.session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == source, BondRow.kind == BondKind.SPEAKS, BondRow.target_node_id.in_(languages))
        ):
            if language not in spoken:
                await connect(ctx.session, learner.id, language, BondKind.SPEAKS, ctx.epoch, description="taught by one who remembers it")
                return language
    return None


async def give_account(ctx: TickContext, teacher: EntityRow, learner: EntityRow, fidelity: int) -> int | None:
    for account in await ctx.session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == teacher.id).order_by(AccountRow.id)):
        copy = AccountRow(
            holder_entity_id=learner.id,
            author_node_id=teacher.id,
            kind=account.kind,
            medium=AccountMedium.ORAL,
            collection_id=account.collection_id,
            subject_node_id=account.subject_node_id,
            fidelity=clamp_percent(account.fidelity * fidelity // PERCENT),
            credence=account.credence,
            revised_from_id=account.id,
            defaced=False,
            epoch=ctx.epoch,
            locked=[],
        )
        known = await ctx.session.scalar(select(AccountRow.id).where(AccountRow.holder_entity_id == learner.id, AccountRow.revised_from_id == account.id))
        if known is None:
            ctx.session.add(copy)
            await ctx.session.flush()
            return account.subject_node_id or account.collection_id
    return None


async def give_treasure(ctx: TickContext, teacher: EntityRow, learner: EntityRow) -> int | None:
    region = await top_region(ctx.session, teacher)
    if region is None:
        return None
    places = select(EntityRow.id).where(EntityRow.location_id == region.id)
    secret = await ctx.session.scalar(
        select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id.in_(places), PlaceSecretRow.sealed.is_(True)).order_by(PlaceSecretRow.id).limit(1)
    )
    if secret is None:
        return None
    await connect(ctx.session, learner.id, secret.place_entity_id, BondKind.KNOWS, ctx.epoch, description="told where it lies")
    return secret.place_entity_id


async def give_art(ctx: TickContext, sources: list[int], learner: EntityRow) -> int | None:
    known = set(await ctx.session.scalars(select(ArtFormPractitionerRow.art_form_entity_id).where(ArtFormPractitionerRow.practitioner_entity_id == learner.id)))
    for source in sources:
        for row in await ctx.session.scalars(select(ArtFormPractitionerRow).where(ArtFormPractitionerRow.practitioner_entity_id == source)):
            if row.art_form_entity_id not in known:
                await practise(ctx, row.art_form_entity_id, learner.id, row.mastery // 2)
                return row.art_form_entity_id
    return None


async def give_song(ctx: TickContext, sources: list[int], learner: EntityRow) -> int | None:
    for source in sources:
        song = await ctx.session.scalar(
            select(ArtworkProfileRow.artwork_entity_id)
            .where(ArtworkProfileRow.author_entity_id == source, ArtworkProfileRow.performed.is_(True))
            .order_by(ArtworkProfileRow.artwork_entity_id)
            .limit(1)
        )
        if song is not None and bond_fits(BondKind.TELLS_OF, learner.entity_type, EntityType.ARTWORK):
            await connect(ctx.session, learner.id, song, BondKind.TELLS_OF, ctx.epoch, description="told back to the living")
            return song
    return None


async def give_prophecy(ctx: TickContext, teacher: EntityRow, learner: EntityRow) -> int | None:
    found = await ctx.session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == teacher.id, BondRow.kind == BondKind.PROPHESIES, BondRow.state == BondState.ACTIVE)
        .limit(1)
    )
    if found is None or not bond_fits(BondKind.PROPHESIES, learner.entity_type, EntityType.PROPHECY):
        return None
    await connect(ctx.session, learner.id, found, BondKind.PROPHESIES, ctx.epoch, description="heard from the dead")
    return found


async def teach(ctx: TickContext, teacher: EntityRow, learner: EntityRow, kind: TeachingKind, fidelity: int) -> int | None:
    origin = await origin_of(ctx, teacher)
    sources = [
        teacher.id,
        *([origin.id] if origin is not None else []),
        *([origin.affiliated_entity_id] if origin is not None and origin.affiliated_entity_id else []),
    ]
    by_source = {
        TeachingKind.RITE: give_rite,
        TeachingKind.TECHNIQUE: give_technique,
        TeachingKind.TRUE_NAME: give_name,
        TeachingKind.LANGUAGE: give_language,
        TeachingKind.ART_FORM: give_art,
        TeachingKind.SONG: give_song,
    }
    if kind in by_source:
        return await by_source[kind](ctx, sources, learner)
    if kind is TeachingKind.ACCOUNT:
        return await give_account(ctx, teacher, learner, fidelity)
    if kind is TeachingKind.TREASURE:
        return await give_treasure(ctx, teacher, learner)
    return await give_prophecy(ctx, teacher, learner)


def fidelity_of(ctx: TickContext, teacher: EntityRow, beast: BeastProfileRow | None) -> int:
    if beast is not None:
        return clamp_percent(beast.intelligence)
    return clamp_percent(PERCENT - stat_or(teacher, "unrest", 0) * ctx.rules.teachings.unrest_error_pct // PERCENT)


async def lesson(
    ctx: TickContext, teacher: EntityRow, learner: EntityRow, *, kinds: tuple[TeachingKind, ...], price: int = 0, forced: bool = False
) -> TeachingRow | None:
    if not forced and (held(teacher.id, learner.id) or await barred(ctx, teacher.id, learner.id)):
        return None
    beast = await ctx.session.get(BeastProfileRow, teacher.id)
    fidelity = fidelity_of(ctx, teacher, beast)
    for kind in kinds:
        if await taught(ctx, teacher.id, learner.id, kind):
            continue
        subject = await teach(ctx, teacher, learner, kind, fidelity)
        if subject is None:
            continue
        sold = price > 0
        if sold:
            await shift_points(ctx.session, learner, -price)
        row = TeachingRow(
            teacher_node_id=teacher.id,
            learner_entity_id=learner.id,
            kind=kind,
            subject_node_id=subject,
            fidelity=fidelity,
            state=TeachingState.SOLD if sold else TeachingState.TAUGHT,
            price=price,
            epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
        await ctx.session.flush()
        await record_incident(
            ctx, f"teaching.{kind.value}", roles={IncidentRole.TEACHER: teacher.id, IncidentRole.LEARNER: learner.id}, facts={"teaching": kind, "price": price}
        )
        return row
    return None


async def learners_of(ctx: TickContext, teacher: EntityRow) -> list[EntityRow]:
    origin = await origin_of(ctx, teacher)
    found: list[int] = []
    if origin is not None and origin.affiliated_entity_id is not None:
        found.append(origin.affiliated_entity_id)
    if teacher.location_id is not None:
        found.extend(
            await ctx.session.scalars(
                select(EntityRow.id)
                .where(
                    EntityRow.location_id == teacher.location_id,
                    EntityRow.entity_type.in_(COMMUNITY_TYPES),
                    EntityRow.status == EntityStatus.CANON,
                )
                .order_by(EntityRow.id)
            )
        )
    rows = [await ctx.session.get(EntityRow, node) for node in dict.fromkeys(found)]
    return [row for row in rows if row is not None and row.status is EntityStatus.CANON and row.entity_type in COMMUNITY_TYPES]


SPIRIT_LESSONS = (
    TeachingKind.RITE,
    TeachingKind.TECHNIQUE,
    TeachingKind.ART_FORM,
    TeachingKind.SONG,
    TeachingKind.TRUE_NAME,
    TeachingKind.PROPHECY,
    TeachingKind.TREASURE,
    TeachingKind.LANGUAGE,
)
BEAST_LESSONS = (TeachingKind.ACCOUNT, TeachingKind.RITE, TeachingKind.LANGUAGE, TeachingKind.TRUE_NAME)


async def lore_beasts(ctx: TickContext) -> list[tuple[EntityRow, BeastProfileRow]]:
    table = ctx.rules.teachings
    statement = (
        select(EntityRow, BeastProfileRow)
        .join(BeastProfileRow, BeastProfileRow.beast_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, BeastProfileRow.intelligence >= table.lore_intelligence, BeastProfileRow.lifespan >= table.lore_lifespan)
        .order_by(EntityRow.id)
    )
    return [(beast, profile) for beast, profile in await ctx.session.execute(statement)]


async def remember_age(ctx: TickContext, beast: EntityRow, profile: BeastProfileRow) -> int:
    told = select(AccountRow.collection_id).where(AccountRow.holder_entity_id == beast.id, AccountRow.collection_id.is_not(None))
    remembered = 0
    for collection in await ctx.session.scalars(
        select(CollectionRow)
        .where(
            CollectionRow.world_id == beast.world_id,
            CollectionRow.kind.in_(sorted(RECORDED)),
            CollectionRow.id.not_in(told),
            CollectionRow.start_epoch >= ctx.epoch - 1,
        )
        .order_by(CollectionRow.id)
        .limit(ctx.rules.teachings.memories_per_epoch)
    ):
        ctx.session.add(
            AccountRow(
                holder_entity_id=beast.id,
                author_node_id=beast.id,
                kind=AccountKind.ELDER_MEMORY,
                medium=AccountMedium.ORAL,
                collection_id=collection.id,
                fidelity=clamp_percent(profile.intelligence),
                credence=clamp_int(profile.age, 0, PERCENT),
                defaced=False,
                epoch=ctx.epoch,
                locked=[],
            )
        )
        remembered += 1
    await ctx.session.flush()
    return remembered


@reads(
    "spirit.unrest",
    "table.accounts",
    "table.art_form_practitioners",
    "table.artwork_profiles",
    "table.beast_profiles",
    "table.bonds",
    "table.creator",
    "table.cult_tenets",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_techniques",
    "table.hooks",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.naming_customs",
    "table.node_births",
    "table.nodes",
    "table.place_secrets",
    "table.sons",
    "table.stars",
    "table.teachings",
    "table.true_names",
    "table.worlds",
)
@writes(
    "table.accounts",
    "table.art_form_practitioners",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.holder_techniques",
    "table.hooks",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.teachings",
    "table.true_names",
)
async def teachings(ctx: TickContext) -> None:
    table = ctx.rules.teachings
    for beast, profile in await lore_beasts(ctx):
        if held(beast.id):
            continue
        ctx.count("elder_memories", await remember_age(ctx, beast, profile))
        if profile.temper in HOSTILE_TEMPERS:
            continue
        for learner in await learners_of(ctx, beast):
            if ctx.rng(f"beast_lesson.{beast.id}.{learner.id}.{ctx.epoch}").chance(table.beast_chance):
                price = table.beast_price if stat_or(learner, "wealth", 0) >= table.beast_price else 0
                if await lesson(ctx, beast, learner, kinds=BEAST_LESSONS, price=price) is not None:
                    ctx.count("beast_lessons")
    spirits = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for spirit in list(spirits):
        if held(spirit.id):
            continue
        for learner in await learners_of(ctx, spirit):
            chance = table.spirit_chance
            if TenetKind.ANCESTOR_VENERATION in await faith_tenets(ctx.session, learner.id):
                chance += table.veneration_bonus
            if (
                ctx.rng(f"spirit_lesson.{spirit.id}.{learner.id}.{ctx.epoch}").chance(chance)
                and await lesson(ctx, spirit, learner, kinds=SPIRIT_LESSONS) is not None
            ):
                ctx.count("spirit_lessons")
