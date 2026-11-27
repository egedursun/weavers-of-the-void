import re

from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.domain.enums.records import FactValue

MOVING_VERBS = (
    "bought|brought|sold|took|taken|raided|gave|spent|paid|sent|delivered|reaching|carried|lent|owes|traded|shipped|moved|stole|seized|"
    "looted|levied|raised|gathered|harvested|mined|caught|fed|healed|freed|ransomed"
)
VERB_AMOUNT = re.compile(rf"\b(?:{MOVING_VERBS})\s+\{{(\w+)(?::[^}}]*)?\}}")
AMOUNT_NOUN = re.compile(r"\{(\w+)(?::[^}]*)?\}\s+(?:loads|dead)\b")
COUNTED_NOUN = re.compile(r"\{(\w+):[^}|]*\|(?:loads|dead)\}")

NEVER_ZERO: frozenset[tuple[str, str]] = frozenset(
    {
        ("being.traded", "moved"),
        ("carrion.laid", "dead"),
        ("casualties.disaster_dead", "dead"),
        ("contraband.books", "carried"),
        ("disease.expelled", "expelled"),
        ("economy.holding_transferred", "moved"),
        ("endowment.paid", "amount"),
        ("gods.essence_sent", "amount"),
        ("land.fossil_traded", "units"),
        ("market.credit", "moved"),
        ("market.credit", "owed"),
        ("market.famine_grain", "delivered"),
        ("relief.given", "helped"),
        ("money.temple_loot", "loads"),
        ("trade.convoy_lost", "cargo_lost"),
        ("trade.convoy_raided", "cargo_lost"),
        ("trade_policy.smuggled", "loads"),
    }
)

ZERO_TOLD: frozenset[tuple[str, str]] = frozenset(
    {
        ("tools.mortal.appeal", "fee"),
        ("admiralty.commissioned", "cost"),
        ("affairs.election", "share"),
        ("affliction.aged", "years"),
        ("affliction.charm_renewed", "cost"),
        ("beast.hoard_robbed", "taken"),
        ("civilization.loan", "amount"),
        ("collection.trophy_taken", "pieces"),
        ("commons.poaching", "poached"),
        ("contraband.slaves", "count"),
        ("daily.tourism_season", "coin"),
        ("disease.sanitation_ordered", "cost"),
        ("endowment.ransomed", "freed"),
        ("land.dredged", "cost"),
        ("manumission.revolt", "freed"),
        ("market.cartel_exposed", "fines"),
        ("market.price_war_won", "losses"),
        ("mind.divided", "share"),
        ("mind.famine_aid", "loads"),
        ("mind.plot", "wealth"),
        ("money.peg_held", "spent"),
        ("nomads.confederation", "camps"),
        ("occupation.deportation", "carried"),
        ("polity.works", "cost"),
        ("population.resettlement", "people"),
        ("population.target_met", "change"),
        ("power_bases.split", "hosts"),
        ("seasons.summer_drought", "lost"),
        ("sky.aurora_spread", "reach"),
        ("slave_markets.sold", "count"),
        ("sons.rebel_theft", "amount"),
        ("tools.mortal.bartered", "given"),
        ("tools.mortal.buy_shares", "share"),
        ("tools.mortal.free_bound", "freed"),
        ("tools.mortal.seize_hoards", "hoards"),
        ("tradition.forage_taken", "food"),
        ("underworld.trafficked", "taken"),
        ("war.campaign_launched", "forces"),
        ("war.god_duel", "score"),
        ("war.sack.deport", "moved"),
        ("weather.late_frost", "lost"),
    }
)


def moved_amounts(spec: IncidentKindSpec) -> list[str]:
    numbers = {fact.key for fact in spec.facts if fact.value is FactValue.NUMBER}
    found = [match.group(1) for pattern in (VERB_AMOUNT, AMOUNT_NOUN, COUNTED_NOUN) for match in pattern.finditer(spec.template)]
    return sorted({key for key in found if key in numbers})


def amount_problems(kinds: dict[str, IncidentKindSpec]) -> list[str]:
    found: list[str] = []
    for key, spec in sorted(kinds.items()):
        for fact in moved_amounts(spec):
            pair = (key, fact)
            if (pair in NEVER_ZERO) == (pair in ZERO_TOLD):
                found.append(f"{key}: tells the amount {fact} it moved; list it once in NEVER_ZERO or ZERO_TOLD of catalog/incident_kinds/amounts.py")
    for key, fact in sorted(NEVER_ZERO | ZERO_TOLD):
        listed = kinds.get(key)
        if listed is None or fact not in moved_amounts(listed):
            found.append(f"{key}: amounts.py lists {fact}, which the kind does not tell as an amount it moved")
    return found
