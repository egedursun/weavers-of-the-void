import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.titles import DeJureLinkRow, TitleProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.titles import TitleRank
from aerona.services.player import titles
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_creates_grants_redraws_and_destroys_titles(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    lord = await make_entity(session, "Ewen", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    rival = await make_entity(session, "Fia", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    created = await titles.create(scope, titles.CreateTitle(rank=TitleRank.DUCHY, name="Duchy of the Fens", holder_id=lord.id, lands=[world.region.id]))
    title_id = created.values["title_id"]
    row = await session.get(TitleProfileRow, title_id)
    assert row is not None and row.holder_node_id == lord.id and row.rank is TitleRank.DUCHY
    assert await session.get(DeJureLinkRow, (title_id, world.region.id)) is not None
    await titles.edit(scope, titles.EditTitle(title_id=title_id, rank=TitleRank.KINGDOM, prestige=70, emblem="Or a crescent on Azure"))
    assert row.rank is TitleRank.KINGDOM and row.prestige == 70 and {"rank", "prestige", "emblem"} <= set(row.locked)
    with pytest.raises(ValidationFailedError):
        await titles.edit(scope, titles.EditTitle(title_id=title_id, liege_id=title_id))
    await titles.grant(scope, titles.PassTitle(title_id=title_id, holder_id=rival.id, usurped=True))
    assert row.holder_node_id == rival.id
    await titles.remove_de_jure(scope, titles.DeJureTarget(title_id=title_id, member_id=world.region.id))
    await titles.set_de_jure(scope, titles.SetDeJure(title_id=title_id, member_id=world.region.id))
    await titles.destroy(scope, titles.TitleTarget(title_id=title_id))
    assert row.destroyed_epoch is not None and row.holder_node_id is None
    await titles.restore(scope, titles.PassTitle(title_id=title_id, holder_id=lord.id))
    assert row.destroyed_epoch is None and row.holder_node_id == lord.id
    await titles.hold_title(scope, titles.EditTitle(title_id=title_id, hold=False))
    await titles.remove(scope, titles.TitleTarget(title_id=title_id))
    with pytest.raises(NotFoundError):
        await titles.remove(scope, titles.TitleTarget(title_id=title_id))
