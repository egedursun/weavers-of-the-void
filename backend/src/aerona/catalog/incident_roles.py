from types import MappingProxyType

from aerona.domain.enums.modifier import IncidentRole

A = IncidentRole.ACTOR
T = IncidentRole.TARGET
S = IncidentRole.SUBJECT
P = IncidentRole.PLACE

INCIDENT_ROLES: MappingProxyType[str, tuple[IncidentRole, ...]] = MappingProxyType(
    {
        "afterlife.possession": (A, T),
        "afterlife.reborn": (A, S),
        "beyond.soul_harvest": (A, T),
        "body.maimed_cult": (S, A),
        "creatures.predation": (A, T),
        "creatures.prey_extinct": (A, T),
        "creatures.soul_eaten": (A, T),
        "curses.spread": (A, T),
        "duel.honour": (A, T),
        "grudges.enmity": (A, T),
        "grudges.holy_war": (A, T),
        "heroism.defeat": (A, T, S),
        "heroism.legendary_weapon": (S, A),
        "heroism.rewind": (A, T),
        "institutions.cult_merged": (T, A),
        "institutions.people_union": (T, A),
        "institutions.place_swallowed": (A, T),
        "life_cycles.looted": (A, T, S),
        "living_stats.mystery_knowledge": (A, P, S),
        "living_stats.work_knowledge": (S, A, T),
        "magic.rite": (A, S),
        "memory.vengeance": (A, T),
        "migration.famine": (A, S, T),
        "mind.famine_aid": (A, T),
        "mortal.mourning": (S, P, S),
        "polity.law_enacted": (A, S),
        "polity.secession": (A, T),
        "polity.succession_war": (A, T, S),
        "refugees.sheltered": (S, A),
        "remembrance.plague_turned": (S, T),
        "spirits.haunting": (A, T),
        "trade.barter": (A, A),
        "tools.son.incite": (T, T),
        "trade.decree": (A, T),
        "war.duel_decree": (A, T),
        "war.outbreak": (S, A, T, A, T),
        "war.uprising_redirected": (A, S, T),
        "world_balance.faction": (S, A),
        "writing.script": (A, S),
    }
)


def positional_role(template_key: str | None, position: int) -> IncidentRole | None:
    roles = INCIDENT_ROLES.get(template_key or "")
    return roles[position] if roles is not None and position < len(roles) else None
