from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.orders import ExchangeRateRow
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import SkillKind, SkillSource
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm


async def money_changer(session: AsyncSession, realm: Realm) -> Ids:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.ACCOUNTING, level=6, peak=6, last_used_epoch=1, source=SkillSource.PRACTICE))
    coins = [
        CurrencyRow(issuer_entity_id=realm.settlement_id, name=name, metal=MaterialKind.SILVER, purity=80, supply=100, trust=70, minted_epoch=1)
        for name in ("Wheel Coin", "Star Coin")
    ]
    session.add_all(coins)
    await session.flush()
    session.add(ExchangeRateRow(base_currency_id=coins[0].id, quote_currency_id=coins[1].id, market_entity_id=realm.settlement_id, locked=[]))
    await session.flush()
    return {}
