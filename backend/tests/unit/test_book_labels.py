from sqlalchemy import inspect

from aerona.db.tables.body import ConditionRow
from aerona.db.tables.factions import FactionGoalRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.faction import FactionGoalKind
from aerona.domain.enums.polity import OfficeKind
from aerona.services.books.records import kind_phrase
from aerona.services.books.typed import column_labels, label_of

NAMES = {7: "Esdorith", 9: "the Empire of Vosaldren"}


def test_a_goal_spoken_with_its_own_article_is_never_doubled() -> None:
    label = label_of(inspect(FactionGoalRow))
    for kind in FactionGoalKind:
        told = label(FactionGoalRow(faction_entity_id=7, kind=kind, since_epoch=3), NAMES)
        assert not told.startswith(("the a ", "the an ", "the the ")), told


def test_an_untitled_office_is_described_not_called_missing() -> None:
    told = label_of(inspect(OfficeRow))(OfficeRow(polity_entity_id=9, kind=OfficeKind.REGENT, title=None, since_epoch=4), NAMES)
    assert told and "regent" in told and "Vosaldren" in told


def test_a_kind_beside_its_kind_record_reads_once() -> None:
    labels = column_labels([column for column in ConditionRow.__table__.columns])
    assert labels["kind"] == "Kind"
    assert labels["kind_id"] == "Kind record"
    assert labels["source"] == "Source kind"
    assert labels["source_node_id"] == "Source"


def test_a_happening_with_no_line_is_told_by_its_kind() -> None:
    assert kind_phrase("disasters.flood") == "Flood (nature)"
