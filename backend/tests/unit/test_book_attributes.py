import aerona.db.tables
from aerona.db.base import Base
from aerona.db.tables.warfare import HeroQuestRow
from aerona.domain.enums.quests import QuestAim
from aerona.services.books.typed import attribute_of


def test_every_column_of_every_table_reaches_its_attribute_even_when_they_are_named_apart() -> None:
    assert aerona.db.tables
    for mapper in Base.registry.mappers:
        for column in mapper.local_table.columns:
            assert mapper.get_property_by_column(column).key
    row = HeroQuestRow(aim=QuestAim.HUNT)
    column = HeroQuestRow.__table__.columns["kind"]
    assert attribute_of(row, column) is QuestAim.HUNT
