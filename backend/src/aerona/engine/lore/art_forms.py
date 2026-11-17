from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.theories import DISCIPLINES, FORM_OF_MEDIUM
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ArtworkProfileRow, HolderLevelRow, TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.discovery import ArtFormPractitionerRow, ArtFormProfileRow, BannedWorkRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.mind import CultureValueRow, InspirationRow, SkillRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import InspirationState, MemoryKind, ValueAxis
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ArtFormStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.couplings.novelty import novelty_of
from aerona.engine.lore.language import barrier
from aerona.engine.lore.learning import realm_of
from aerona.engine.lore.printing import banned_for
from aerona.engine.lore.research_depth import trade_partners
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, shift_stat
from aerona.engine.services.community_relations import change_relation
from aerona.engine.tongues.grammar import gap


async def best_discipline(session: AsyncSession, mortal_id: int) -> tuple[ArtMode, int] | None:
    skills = dict((await session.execute(select(SkillRow.skill, SkillRow.level).where(SkillRow.holder_node_id == mortal_id))).all())
    ranked = sorted(
        ((max((int(skills.get(skill, 0)) for skill in spec.skills), default=0), discipline) for discipline, spec in DISCIPLINES.items()),
        key=lambda item: (-item[0], item[1].value),
    )
    return (ranked[0][1], ranked[0][0]) if ranked and ranked[0][0] > 0 else None


async def practise(ctx: TickContext, form_id: int, who: int, mastery: int) -> ArtFormPractitionerRow:
    row = await ctx.session.get(ArtFormPractitionerRow, (form_id, who))
    if row is None:
        row = ArtFormPractitionerRow(
            art_form_entity_id=form_id, practitioner_entity_id=who, mastery=clamp_int(mastery, 0, PERCENT), since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def found_form(
    ctx: TickContext, home: EntityRow, discipline: ArtMode, name: str, *, founder: EntityRow | None, parents: list[int], structure: dict[str, str | int]
) -> EntityRow:
    form = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ART_FORM,
            name=name,
            body=f"{DISCIPLINES[discipline].label} first practised in {home.name}.",
            stats=ArtFormStats(practitioners=1, prestige=PERCENT * 3 // 10),
            power=3,
            world_id=home.world_id,
            location_id=home.id,
            subtype=DISCIPLINES[discipline].label.lower(),
            maker_entity_id=founder.id if founder is not None else None,
        ),
    )
    tongue = await spoken_language(ctx.session, home.id)
    ctx.session.add(
        ArtFormProfileRow(
            art_form_entity_id=form.id,
            discipline=discipline,
            structure=structure,
            origin_culture_id=home.id,
            founder_entity_id=founder.id if founder is not None else None,
            language_entity_id=tongue.id if tongue is not None and DISCIPLINES[discipline].verbal else None,
            difficulty=PERCENT * 2 // 5,
            prestige=PERCENT * 3 // 10,
            sacred=False,
            notation=False,
            occasions=[],
            parent_ids=parents,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    await practise(ctx, form.id, home.id, PERCENT // 5)
    if founder is not None:
        await practise(ctx, form.id, founder.id, PERCENT // 2)
    return form


async def inspired(ctx: TickContext, mortal_id: int) -> bool:
    found = await ctx.session.scalar(
        select(InspirationRow.id).where(InspirationRow.holder_node_id == mortal_id, InspirationRow.state == InspirationState.BURNING).limit(1)
    )
    return found is not None


async def shaken(ctx: TickContext, home: EntityRow) -> bool:
    region = (await RegionAtlas.load(ctx.session)).top_region(home.id)
    plague = await ctx.session.scalar(
        select(OutbreakRow.id)
        .where(OutbreakRow.region_entity_id == region, OutbreakRow.status == OutbreakStatus.ENDED, OutbreakRow.ended_epoch >= ctx.epoch - 1)
        .limit(1)
    )
    defeat = await ctx.session.scalar(select(WarRow.id).where(WarRow.loser_entity_id == home.id, WarRow.ended_epoch >= ctx.epoch - 1).limit(1))
    return plague is not None or defeat is not None


async def invent(ctx: TickContext) -> int:
    table = ctx.rules.art_forms
    founded = 0
    skilled = await ctx.session.scalars(select(SkillRow.holder_node_id).where(SkillRow.level >= table.invent_skill).distinct())
    for mortal_id in sorted(skilled):
        mortal = await ctx.session.get(EntityRow, mortal_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON or held(mortal.id):
            continue
        home = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
        if home is None or home.entity_type not in COMMUNITY_TYPES or held(home.id):
            continue
        best = await best_discipline(ctx.session, mortal.id)
        if best is None or best[1] < table.invent_skill:
            continue
        stirred = await inspired(ctx, mortal.id) or await shaken(ctx, home)
        if not ctx.rng(f"art_form.invent.{mortal.id}.{ctx.epoch}").chance(table.invent_pct * (1 + table.stirred_pct / PERCENT * stirred)):
            continue
        form = await found_form(ctx, home, best[0], f"The {DISCIPLINES[best[0]].label.lower()} of {mortal.name}", founder=mortal, parents=[], structure={})
        founded += 1
        await note(
            ctx,
            f"{mortal.name} set down a new {DISCIPLINES[best[0]].label.lower()}: {form.name}.",
            key="art_forms.invented",
            ids=[mortal.id, form.id],
            kind=ChronicleKind.CULTURE,
        )
    return founded


async def fuse(ctx: TickContext) -> int:
    table = ctx.rules.art_forms
    by_home: dict[tuple[int, ArtMode], list[int]] = defaultdict(list)
    profiles = {row.art_form_entity_id: row for row in await ctx.session.scalars(select(ArtFormProfileRow))}
    for row in await ctx.session.scalars(select(ArtFormPractitionerRow).order_by(ArtFormPractitionerRow.art_form_entity_id)):
        profile = profiles.get(row.art_form_entity_id)
        if profile is not None:
            by_home[(row.practitioner_entity_id, profile.discipline)].append(row.art_form_entity_id)
    fused = 0
    for (home_id, discipline), forms in sorted(by_home.items(), key=lambda item: (item[0][0], item[0][1].value)):
        home = await ctx.session.get(EntityRow, home_id)
        if len(forms) < 2 or home is None or home.entity_type not in COMMUNITY_TYPES or held(home_id):
            continue
        first, second = forms[0], forms[1]
        if any(set(profile.parent_ids) == {first, second} for profile in profiles.values()):
            continue
        if not ctx.rng(f"art_form.fuse.{home_id}.{first}.{second}.{ctx.epoch}").chance(table.fusion_pct):
            continue
        merged = {**profiles[second].structure, **profiles[first].structure}
        form = await found_form(
            ctx, home, discipline, f"The {DISCIPLINES[discipline].label.lower()} of {home.name}", founder=None, parents=[first, second], structure=merged
        )
        fused += 1
        await note(ctx, f"Two forms met in {home.name} and became one: {form.name}.", key="art_forms.fused", ids=[home.id, form.id], kind=ChronicleKind.CULTURE)
    return fused


async def fit_of(session: AsyncSession, community_id: int) -> float:
    taste = await session.get(CultureValueRow, (community_id, ValueAxis.ARTWORK))
    return 1 + (taste.value if taste is not None else 0) / PERCENT


async def spread(ctx: TickContext) -> int:
    table = ctx.rules.art_forms
    moved = 0
    homes = list(
        await ctx.session.scalars(
            select(ArtFormPractitionerRow).order_by(ArtFormPractitionerRow.art_form_entity_id, ArtFormPractitionerRow.practitioner_entity_id)
        )
    )
    for row in homes:
        source = await ctx.session.get(EntityRow, row.practitioner_entity_id)
        profile = await ctx.session.get(ArtFormProfileRow, row.art_form_entity_id)
        if source is None or profile is None or source.entity_type not in COMMUNITY_TYPES:
            continue
        for partner in sorted(await trade_partners(ctx.session, source.id)):
            target = await ctx.session.get(EntityRow, partner)
            if target is None or target.entity_type not in COMMUNITY_TYPES or target.status is not EntityStatus.CANON or held(partner):
                continue
            if await ctx.session.get(ArtFormPractitionerRow, (profile.art_form_entity_id, partner)) is not None:
                continue
            if await banned_for(ctx.session, partner, profile.art_form_entity_id):
                continue
            chance = table.spread_pct * (1 + (await fit_of(ctx.session, partner) - 1) * table.value_fit_pct / PERCENT)
            chance *= 1 + table.notation_pct / PERCENT * profile.notation
            chance *= await novelty_of(ctx.session, profile.art_form_entity_id) / PERCENT
            if not ctx.rng(f"art_form.spread.{profile.art_form_entity_id}.{partner}.{ctx.epoch}").chance(chance):
                continue
            mastery = row.mastery // 2
            if profile.language_entity_id is not None:
                understood = await barrier(ctx.session, ctx.rules, source.id, partner, ctx.epoch)
                partner_tongue = await spoken_language(ctx.session, partner)
                strain = 1 + await gap(ctx.session, profile.language_entity_id, partner_tongue.id if partner_tongue is not None else None)
                mastery = round_half_up(mastery * max(0.0, 1 - table.translation_pct / PERCENT * (1 - understood) * strain))
            await practise(ctx, profile.art_form_entity_id, partner, mastery)
            moved += 1
    return moved


async def conquest_spread(ctx: TickContext) -> int:
    table = ctx.rules.art_forms
    atlas = await RegionAtlas.load(ctx.session)
    moved = 0
    for occupation in list(await ctx.session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id))):
        locals_ = [item for item in atlas.communities_in(occupation.region_entity_id) if not held(item)]
        pairs = [(occupation.occupier_entity_id, local) for local in locals_] + [(local, occupation.occupier_entity_id) for local in locals_]
        for source, target in pairs:
            if held(target):
                continue
            forms = await ctx.session.scalars(select(ArtFormPractitionerRow).where(ArtFormPractitionerRow.practitioner_entity_id == source))
            for row in list(forms):
                if await ctx.session.get(ArtFormPractitionerRow, (row.art_form_entity_id, target)) is not None:
                    continue
                if await banned_for(ctx.session, target, row.art_form_entity_id):
                    continue
                if ctx.rng(f"art_form.conquest.{row.art_form_entity_id}.{target}.{ctx.epoch}").chance(table.spread_pct):
                    await practise(ctx, row.art_form_entity_id, target, row.mastery // 2)
                    moved += 1
    return moved


async def master(ctx: TickContext) -> int:
    gain = ctx.rules.art_forms.mastery_gain
    grown = 0
    difficulty = dict((await ctx.session.execute(select(ArtFormProfileRow.art_form_entity_id, ArtFormProfileRow.difficulty))).all())
    for row in list(await ctx.session.scalars(select(ArtFormPractitionerRow))):
        if "mastery" in row.locked or held(row.practitioner_entity_id) or row.mastery >= PERCENT:
            continue
        hard = difficulty.get(row.art_form_entity_id, 0)
        row.mastery = clamp_int(row.mastery + max(1, round_half_up(gain * (PERCENT - hard / 2) / PERCENT)), 0, PERCENT)
        grown += 1
    return grown


async def written_down(session: AsyncSession, holders: list[int]) -> bool:
    found = await session.scalar(
        select(HolderLevelRow.holder_entity_id)
        .where(HolderLevelRow.holder_entity_id.in_(holders), HolderLevelRow.branch == KnowledgeBranch.WRITING, HolderLevelRow.level >= 1)
        .limit(1)
    )
    return found is not None


async def tend_forms(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.art_forms
    counts = dict(
        (await ctx.session.execute(select(ArtFormPractitionerRow.art_form_entity_id, func.count()).group_by(ArtFormPractitionerRow.art_form_entity_id))).all()
    )
    lost = sacred = 0
    for profile in list(await ctx.session.scalars(select(ArtFormProfileRow).order_by(ArtFormProfileRow.art_form_entity_id))):
        form = await ctx.session.get(EntityRow, profile.art_form_entity_id)
        if form is None or form.status is not EntityStatus.CANON or held(form.id):
            continue
        practitioners = int(counts.get(profile.art_form_entity_id, 0))
        holders = list(
            await ctx.session.scalars(select(ArtFormPractitionerRow.practitioner_entity_id).where(ArtFormPractitionerRow.art_form_entity_id == form.id))
        )
        if "notation" not in profile.locked and not profile.notation and await written_down(ctx.session, holders):
            profile.notation = True
        if "prestige" not in profile.locked:
            aim = min(PERCENT, practitioners * PERCENT // 10) * await novelty_of(ctx.session, form.id) // PERCENT
            step = table.prestige_drift if aim > profile.prestige else -table.prestige_drift if aim < profile.prestige else 0
            profile.prestige = clamp_int(profile.prestige + step, 0, PERCENT)
        if practitioners:
            profile.updated_epoch = ctx.epoch
        elif not profile.notation and ctx.epoch - profile.updated_epoch >= table.decline_epochs:
            await retire_in(ctx, form, "no one practised it and nothing kept it written", EntityStatus.DESTROYED)
            lost += 1
            lost_text = f"{form.name} was lost: no one practised it and nothing kept it written."
            await note(ctx, lost_text, key="art_forms.lost", ids=[form.id], kind=ChronicleKind.CULTURE)
        if profile.sacred or profile.occasions:
            sacred += await hallow(ctx, holders, set(profile.occasions), sacred=profile.sacred)
        set_stats(form, practitioners=practitioners, prestige=profile.prestige)
    return {"art_forms_lost": lost, "traditions_hallowed": sacred}


async def hallow(ctx: TickContext, holders: list[int], occasions: set[str], *, sacred: bool) -> int:
    lift = ctx.rules.art_forms.sacred_tradition_pct
    raised = 0
    rows = await ctx.session.execute(
        select(TraditionParticipationRow, TraditionProfileRow.kind)
        .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == TraditionParticipationRow.tradition_entity_id)
        .where(TraditionParticipationRow.community_entity_id.in_(holders))
    )
    for row, kind in rows.all():
        if not (sacred or kind.value in occasions) or "participation" in row.locked or held(row.community_entity_id):
            continue
        row.participation = clamp_int(row.participation + round_half_up((PERCENT - row.participation) * lift / PERCENT), 0, PERCENT)
        raised += 1
    return raised


async def humiliations(ctx: TickContext) -> int:
    table = ctx.rules.art_forms
    hurt = 0
    bans = await ctx.session.execute(
        select(BannedWorkRow.polity_entity_id, ArtFormProfileRow.origin_culture_id)
        .join(ArtFormProfileRow, ArtFormProfileRow.art_form_entity_id == BannedWorkRow.work_entity_id)
        .where(BannedWorkRow.since_epoch == ctx.epoch)
    )
    for realm, origin in bans.all():
        culture = await ctx.session.get(EntityRow, origin) if origin is not None else None
        people = await people_of(ctx.session, culture) if culture is not None else None
        if people is not None and not held(people.id) and await realm_of(ctx.session, people.id) == realm:
            await change_relation(ctx, people.id, realm, -table.suppression_resistance, MemoryKind.HUMILIATED_ME, note="banned its own art")
            hurt += 1
    return hurt


async def credit_artworks(ctx: TickContext) -> int:
    table = ctx.rules.art_forms
    credited = 0
    rows = await ctx.session.scalars(
        select(ArtworkProfileRow).where(ArtworkProfileRow.art_form_entity_id.is_(None), ArtworkProfileRow.author_entity_id.is_not(None))
    )
    for artwork in list(rows):
        discipline = FORM_OF_MEDIUM.get(artwork.medium)
        if discipline is None or "art_form_entity_id" in artwork.locked or held(artwork.artwork_entity_id):
            continue
        found = await ctx.session.execute(
            select(ArtFormPractitionerRow, ArtFormProfileRow)
            .join(ArtFormProfileRow, ArtFormProfileRow.art_form_entity_id == ArtFormPractitionerRow.art_form_entity_id)
            .where(ArtFormPractitionerRow.practitioner_entity_id == artwork.author_entity_id, ArtFormProfileRow.discipline == discipline)
            .order_by(ArtFormPractitionerRow.mastery.desc())
            .limit(1)
        )
        pair = found.first()
        if pair is None:
            continue
        practitioner, profile = pair
        artwork.art_form_entity_id = profile.art_form_entity_id
        if "quality" not in artwork.locked:
            artwork.quality = clamp_int(
                artwork.quality + round_half_up(artwork.quality * table.mastery_quality_pct * practitioner.mastery / PERCENT / PERCENT), 0, PERCENT
            )
        work = await ctx.session.get(EntityRow, artwork.artwork_entity_id)
        if work is not None:
            shift_stat(work, "renown", round_half_up(table.prestige_renown_pct * profile.prestige / PERCENT), 0)
        credited += 1
    return credited


async def art_forms(ctx: TickContext) -> dict[str, int]:
    counts = {
        "art_forms_invented": await invent(ctx),
        "art_forms_fused": await fuse(ctx),
        "art_forms_spread": await spread(ctx),
        "art_forms_carried_by_conquest": await conquest_spread(ctx),
        "art_mastery": await master(ctx),
        "art_humiliations": await humiliations(ctx),
        "artworks_in_a_form": await credit_artworks(ctx),
    }
    return {**counts, **await tend_forms(ctx)}
