from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import WitnessMode
from aerona.services.books.records import part_taken


def test_one_who_only_heard_of_a_happening_is_never_called_its_witness() -> None:
    heard = IncidentParticipantRow(incident_id=1, node_id=2, role=IncidentRole.WITNESS, position=0, witness_mode=WitnessMode.HEARD)
    saw = IncidentParticipantRow(incident_id=1, node_id=3, role=IncidentRole.WITNESS, position=1, witness_mode=WitnessMode.SAW)
    doer = IncidentParticipantRow(incident_id=1, node_id=4, role=IncidentRole.ACTOR, position=2)
    assert part_taken(heard) == "heard of it"
    assert part_taken(saw) == "as witness"
    assert part_taken(doer) == "as actor"
