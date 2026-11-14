from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import NameFormRow, NamingCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import NameForm, NamingPattern
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.intrigue.names import name_bearer, rename
from aerona.engine.mortal.kin import parents_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import Namer, seed_of

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


async def birth_name(ctx: TickContext, mortal: EntityRow, custom: NamingCustomRow) -> str:
    if custom.pattern is NamingPattern.PARENT:
        parents = await parents_of(ctx.session, mortal.id)
        parent = await ctx.session.get(EntityRow, parents[0]) if parents else None
        return f"{mortal.name}, child of {parent.name}" if parent is not None else mortal.name
    if custom.pattern is NamingPattern.CLAN:
        house = await ctx.session.scalar(select(BondRow.target_node_id).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.MEMBER_OF).limit(1))
        clan = await ctx.session.get(EntityRow, house) if house is not None else None
        return f"{mortal.name} of {clan.name}" if clan is not None else mortal.name
    return mortal.name


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
        await rename(ctx, namer, true, cause=form.value, name=name)
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
    await ctx.session.flush()
