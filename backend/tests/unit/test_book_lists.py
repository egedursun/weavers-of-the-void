from aerona.db.tables.discovery import BlueprintRow, TheoryProfileRow
from aerona.db.tables.mind import LifeDreamRow
from aerona.services.books.typed import TypedIndex


def test_id_lists_render_as_names_and_milestones_as_shares() -> None:
    index = TypedIndex({7: "Ash Guild", 9: "The Hollow Faith"})
    licensed = BlueprintRow.__table__.columns["licensed_to"]
    endorsed = TheoryProfileRow.__table__.columns["endorsed_by"]
    milestones = LifeDreamRow.__table__.columns["milestones"]
    assert index.value(licensed, [7]) == "Ash Guild"
    assert index.value(endorsed, [9, 4]) == "The Hollow Faith, #4"
    assert index.value(milestones, [25, 50]) == "25%, 50%"
