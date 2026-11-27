from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.life.lore import STRIKE_RESEARCH_INCIDENTS_2
from aerona.domain.enums.discovery import ResearchIncident
from aerona.engine.recording.render import placeholders


def test_a_research_incident_tells_deaths_exactly_when_it_can_kill() -> None:
    telling = {member for member in ResearchIncident if "dead" in placeholders(INCIDENT_KINDS[f"discovery.incident_{member.value}"].template)}
    assert telling == set(STRIKE_RESEARCH_INCIDENTS_2)
