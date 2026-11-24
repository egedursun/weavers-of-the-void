from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.naming import NAMING_PATTERNS
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import NameFormRow, NamingCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import NameForm, NamingPattern
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import TrueNameCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.intrigue.names import name_bearer, rename
from aerona.engine.mortal.kin import parents_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.recording.record import record

ROMAN = ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")


@dataclass
class NamingTally:
    seeded: int = 0
    named: int = 0
    renamed: int = 0


async def custom_of(ctx: TickContext, people: EntityRow) -> NamingCustomRow:
    row = await ctx.session.get(NamingCustomRow, people.id)
    if row is not None:
        return row
    table = ctx.rules.naming_customs
    rng = ctx.rng(seed_of("naming", people.id))
    row = NamingCustomRow(
        people_entity_id=people.id,
        pattern=rng.pick(list(NamingPattern)),
        secret_names=rng.chance(table.secret_chance),
        taboo_epochs=table.taboo_epochs if rng.chance(50) else 0,
        rename_on_initiation=rng.chance(table.rename_chance),
        rename_on_marriage=rng.chance(table.rename_chance),
        rename_on_vow=rng.chance(table.rename_chance),
        posthumous_names=rng.chance(table.posthumous_chance),
        locked=[],
    )
    ctx.session.add(row)
    return row


async def give(ctx: TickContext, mortal: EntityRow, form: NameForm, name: str, tally: NamingTally) -> None:
    row = await ctx.session.get(NameFormRow, (mortal.id, form))
    if row is not None:
        if "name" in row.locked:
            return
        row.name, row.given_epoch = name, ctx.epoch
    else:
        ctx.session.add(NameFormRow(holder_node_id=mortal.id, form=form, name=name, given_epoch=ctx.epoch, locked=[]))
    tally.named += 1


async def parent_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    parents = await parents_of(ctx.session, mortal.id)
    parent = await ctx.session.get(EntityRow, parents[0]) if parents else None
    return parent.name if parent is not None else None


async def clan_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    house = await ctx.session.scalar(select(BondRow.target_node_id).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.MEMBER_OF).limit(1))
    clan = await ctx.session.get(EntityRow, house) if house is not None else None
    return clan.name if clan is not None else None


async def place_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    home = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
    return home.name if home is not None else None


async def trade_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    for parent_id in await parents_of(ctx.session, mortal.id):
        profile = await ctx.session.get(MortalProfileRow, parent_id)
        if profile is not None and profile.profession is not None:
            return str(spoken(profile.profession))
    return None


async def ancestral_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    for parent_id in sorted(await parents_of(ctx.session, mortal.id)):
        for grandparent_id in sorted(await parents_of(ctx.session, parent_id)):
            forebear = await ctx.session.get(EntityRow, grandparent_id)
            if forebear is not None:
                return forebear.name
    return None


async def event_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    if mortal.world_id is None:
        return None
    kind = await ctx.session.scalar(
        select(NotableYearRow.kind)
        .where(NotableYearRow.world_id == mortal.world_id, NotableYearRow.epoch == ctx.epoch)
        .order_by(NotableYearRow.year.desc(), NotableYearRow.id.desc())
        .limit(1)
    )
    return f"the year of {spoken(kind)}" if kind is not None else None


async def no_part(ctx: TickContext, mortal: EntityRow) -> str | None:
    return None


PARTS: Mapping[NamingPattern, Callable[[TickContext, EntityRow], Awaitable[str | None]]] = total(
    NamingPattern,
    {
        NamingPattern.GIVEN: no_part,
        NamingPattern.PARENT: parent_part,
        NamingPattern.CLAN: clan_part,
        NamingPattern.TEKNONYM: no_part,
        NamingPattern.PLACE: place_part,
        NamingPattern.TRADE: trade_part,
        NamingPattern.ANCESTRAL: ancestral_part,
        NamingPattern.EVENT: event_part,
    },
)


async def birth_name(ctx: TickContext, mortal: EntityRow, custom: NamingCustomRow) -> str:
    part = await PARTS[custom.pattern](ctx, mortal)
    return f"{mortal.name}{NAMING_PATTERNS[custom.pattern].joiner}{part}" if part else mortal.name


async def teknonyms(ctx: TickContext, mortal: EntityRow, tally: NamingTally) -> None:
    for parent_id in await parents_of(ctx.session, mortal.id):
        parent = await ctx.session.get(EntityRow, parent_id)
        if parent is not None and not held(parent.id) and await ctx.session.get(NameFormRow, (parent.id, NameForm.BIRTH)) is not None:
            await give(ctx, parent, NameForm.DEED, f"parent of {mortal.name}", tally)


async def fresh_name(ctx: TickContext, namer: Namer, mortal: EntityRow, form: NameForm) -> str | None:
    return await namer.person([mortal], seed_of("name_form", mortal.id, form.value, ctx.epoch), mortal.world_id)


async def turned(ctx: TickContext, mortal: EntityRow, kind: BondKind) -> bool:
    found = await ctx.session.scalar(select(BondRow.id).where(BondRow.source_node_id == mortal.id, BondRow.kind == kind, BondRow.epoch == ctx.epoch).limit(1))
    return found is not None


async def rename_for(ctx: TickContext, namer: Namer, mortal: EntityRow, form: NameForm, tally: NamingTally) -> None:
    name = await fresh_name(ctx, namer, mortal, form)
    if not name:
        return
    await give(ctx, mortal, form, name, tally)
    true = await ctx.session.get(TrueNameRow, mortal.id)
    if true is not None and "name" not in (true.locked or []):
        await rename(ctx, namer, true, cause=TrueNameCause.NAME_FORM, name=name, form=form)
    tally.renamed += 1


async def name_life(ctx: TickContext, namer: Namer, mortal: EntityRow, custom: NamingCustomRow, tally: NamingTally) -> None:
    if mortal.birth_epoch == ctx.epoch and await ctx.session.get(NameFormRow, (mortal.id, NameForm.BIRTH)) is None:
        await give(ctx, mortal, NameForm.BIRTH, await birth_name(ctx, mortal, custom), tally)
        if custom.pattern is NamingPattern.TEKNONYM:
            await teknonyms(ctx, mortal, tally)
        if custom.secret_names:
            secret = await fresh_name(ctx, namer, mortal, NameForm.SECRET)
            if secret:
                await give(ctx, mortal, NameForm.SECRET, secret, tally)
                await name_bearer(ctx, mortal.id, secret)
    if custom.rename_on_marriage and await turned(ctx, mortal, BondKind.SPOUSE_OF):
        await rename_for(ctx, namer, mortal, NameForm.MARRIAGE, tally)
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    vowed = profile is not None and mortal.social_class is SocialClass.MONASTIC and await ctx.session.get(NameFormRow, (mortal.id, NameForm.VOW)) is None
    if custom.rename_on_vow and vowed:
        await rename_for(ctx, namer, mortal, NameForm.VOW, tally)
    if await turned(ctx, mortal, BondKind.RULES):
        prior = await ctx.session.scalar(
            select(NameFormRow.name).where(NameFormRow.form == NameForm.ASCENSION, NameFormRow.name.like(f"{mortal.name} %")).limit(1)
        )
        count = 2 if prior is not None else 1
        await give(ctx, mortal, NameForm.ASCENSION, f"{mortal.name} {ROMAN[min(count, len(ROMAN) - 1)]}", tally)


async def initiate_name(ctx: TickContext, namer: Namer, mortal: EntityRow, tally: NamingTally) -> None:
    folk = await people_of(ctx.session, mortal)
    custom = await ctx.session.get(NamingCustomRow, folk.id) if folk is not None else None
    if custom is not None and custom.rename_on_initiation:
        await rename_for(ctx, namer, mortal, NameForm.INITIATION, tally)


async def name_the_dead(ctx: TickContext, namer: Namer, people: EntityRow, custom: NamingCustomRow, tally: NamingTally) -> None:
    if not custom.posthumous_names:
        return
    dead = await ctx.session.scalars(
        select(EntityRow)
        .where(
            await present_among(ctx.session, [people.id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.DEAD,
            EntityRow.end_epoch == ctx.epoch,
        )
        .order_by(EntityRow.id)
    )
    for mortal in list(dead):
        if held(mortal.id) or await ctx.session.get(NameFormRow, (mortal.id, NameForm.POSTHUMOUS)) is not None:
            continue
        name = await fresh_name(ctx, namer, mortal, NameForm.POSTHUMOUS)
        if not name:
            continue
        if await ctx.session.get(NameFormRow, (mortal.id, NameForm.BIRTH)) is None:
            await give(ctx, mortal, NameForm.BIRTH, mortal.name, tally)
        await give(ctx, mortal, NameForm.POSTHUMOUS, name, tally)
        living = mortal.name
        mortal.name = name
        await record(ctx, "death.named", roles={IncidentRole.SUBJECT: mortal.id}, facts={"name": name, "living": living, "taboo": custom.taboo_epochs})


async def keep_naming(ctx: TickContext, tally: NamingTally) -> None:
    namer = Namer(ctx.session, ctx.rules)
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        fresh = await ctx.session.get(NamingCustomRow, people.id) is None
        custom = await custom_of(ctx, people)
        tally.seeded += fresh
        here = await present_among(ctx.session, [people.id])
        for mortal in list(
            await ctx.session.scalars(
                select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        ):
            if not held(mortal.id):
                await name_life(ctx, namer, mortal, custom, tally)
        await name_the_dead(ctx, namer, people, custom, tally)
    await ctx.session.flush()
