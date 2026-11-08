from sqlalchemy import select

from aerona.db.tables.culture import BookContentRow, IdeologyAdherentRow
from aerona.db.tables.discovery import BannedWorkRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import IdeologyStats, ItemStats
from aerona.engine.lore.printing import banned_for, censor, read_in_secret
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.queries import connect, living_entity
from tests.engine.society.factories import Realm, context, knowledge, make, tuned
from tests.engine.statecraft.test_statecraft import polity


async def test_a_strict_censor_bans_dark_books_and_rival_creeds_that_few_read_in_secret(realm: Realm) -> None:
    ctx = context(realm.session, tuned(discovery={"ban_strictness": 0, "ban_reading_pct": 100}))
    state, core = await polity(realm, "Lion Throne")
    lion = await living_entity(realm.session, state.id)
    assert lion is not None
    tome = await make(realm.session, "The Grey Codex", EntityType.ITEM, ItemStats(), world_id=realm.world.id)
    lore = await knowledge(realm, "Unmaking", KnowledgeBranch.FORBIDDEN)
    realm.session.add(BookContentRow(book_entity_id=tome.id, knowledge_entity_id=lore.id))
    await connect(realm.session, core.id, tome.id, BondKind.OWNS, 1)
    creed = await make(realm.session, "The Open Hand", EntityType.IDEOLOGY, IdeologyStats(), world_id=realm.world.id)
    realm.session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=core.id, strength=40))
    await realm.session.flush()
    assert await censor(ctx) == 0
    await enact(ctx, lion, LawKind.CENSORSHIP, {"strictness": 50})
    assert await censor(ctx) == 2
    banned = set(await realm.session.scalars(select(BannedWorkRow.work_entity_id).where(BannedWorkRow.polity_entity_id == state.id)))
    assert banned == {tome.id, creed.id}
    assert await censor(ctx) == 0
    assert await banned_for(realm.session, core.id, tome.id) and not await banned_for(realm.session, None, tome.id)
    assert await read_in_secret(ctx, core.id, tome.id)
