from typing import Any

from tests.tools.every_setup import (
    created,
    dead_sibling,
    dead_star,
    death_son,
    friendly_sibling,
    home_star,
    house,
    item,
    knows_written_law,
    last_rite,
    last_trade_route,
    last_treaty,
    last_war,
    leaking_world,
    ley_line,
    named_spirit,
    outsider,
    plant,
    seasons,
    second_mortal,
    second_region,
    second_settlement,
    sky_son,
    spirit,
    surveyed,
    travel_resource,
)
from tests.tools.every_tool import TEXT, Case, Ids, Step, combined
from tests.tools.factories import Realm

REASON = "so that the valley keeps its promise"


def link(target_id: int) -> list[dict[str, Any]]:
    return [{"target_kind": "entity", "target_id": target_id, "kind": "related", "description": "made beside them"}]


def creation(name: str, **extra: Any) -> Any:
    def arguments(realm: Realm, ids: Ids) -> dict[str, Any]:
        resolved = {key: (value(realm, ids) if callable(value) else value) for key, value in extra.items()}
        return {"name": name, "description": TEXT, "power_level": 2, "links": link(realm.people_id), **resolved}

    return arguments


def plain(**values: Any) -> Any:
    def arguments(realm: Realm, ids: Ids) -> dict[str, Any]:
        return {key: (value(realm, ids) if callable(value) else value) for key, value in values.items()}

    return arguments


def region(realm: Realm, _ids: Ids) -> int:
    return realm.cosmos.region_id


def place(realm: Realm, _ids: Ids) -> int:
    return realm.cosmos.place_id


def world(realm: Realm, _ids: Ids) -> int:
    return realm.cosmos.world_id


def people(realm: Realm, _ids: Ids) -> int:
    return realm.people_id


def other_people(realm: Realm, _ids: Ids) -> int:
    return realm.other_people_id


def settlement(realm: Realm, _ids: Ids) -> int:
    return realm.settlement_id


def mortal(realm: Realm, _ids: Ids) -> int:
    return realm.mortal_id


def sibling(realm: Realm, _ids: Ids) -> int:
    return realm.sibling_id


def knowledge(realm: Realm, _ids: Ids) -> int:
    return realm.knowledge_id


def language(realm: Realm, _ids: Ids) -> int:
    return realm.language_id


def faction(realm: Realm, _ids: Ids) -> int:
    return realm.faction_id


def cult(realm: Realm, _ids: Ids) -> int:
    return realm.cult_id


def plant_kind(_realm: Realm, ids: Ids) -> int:
    return ids["plant"]


def species(realm: Realm, _ids: Ids) -> int:
    return realm.species_id


def resource(realm: Realm, _ids: Ids) -> int:
    return realm.resource_id


def god(realm: Realm, _ids: Ids) -> int:
    return realm.god_id


def route(realm: Realm, _ids: Ids) -> int:
    return realm.route_id


WAR = (
    Step("wage_war", plain(attacker_id=people, defender_id=settlement, cause="claim", aims=["tribute"], reason=REASON)),
    Step("raise_host", plain(community_id=people, soldiers=60, war_id=created("war"))),
)

SON_CASES: dict[str, Case] = {
    "world_summary": Case(),
    "inspect_entity": Case(plain(id=people)),
    "search_entities": Case(plain(query="Kessar")),
    "my_memory": Case(),
    "inspect_sibling": Case(plain(son_id=sibling)),
    "write_plan": Case(plain(plan="Tend the valley roads and teach the folk to keep ledgers of the harvest.")),
    "choose_anchor": Case(plain(entity_id=resource, reason=REASON)),
    "coin_words": Case(plain(language_id=language, words=[{"word": "valen", "meaning": "lamp"}])),
    "call_sibling": Case(plain(son_id=sibling, message="Walk with me along the river road.")),
    "swear_covenant": Case(plain(son_id=sibling, terms="Neither shall cross the river unbidden."), friendly_sibling),
    "give_gift": Case(plain(son_id=sibling, essence=5, words="Take this for the road ahead.")),
    "challenge": Case(plain(son_id=sibling, reason=REASON)),
    "birth_child": Case(plain(inspiration="A child of lamps and ledgers, keeper of the long roads.")),
    "bind_mortals": Case(plain(first_id=mortal, second_id=created("mortal"), reason=REASON), second_mortal),
    "touch_mortal": Case(plain(mortal_id=mortal, reason=REASON)),
    "plant_idea": Case(plain(mortal_id=mortal, reason=REASON)),
    "spread_word": Case(plain(subject_id=mortal, community_id=settlement, reason=REASON)),
    "stir_hearts": Case(plain(first_id=mortal, second_id=created("mortal"), reason=REASON), second_mortal),
    "rebel": Case(plain(proclamation="I will walk my own road from this day onward, by my own word.")),
    "pray_to_creator": Case(plain(message="Hear the valley and its roads.")),
    "make_bond": Case(plain(source_id=people, target=lambda realm, _ids: {"target_kind": "entity", "target_id": realm.settlement_id, "kind": "related"})),
    "create_region": Case(creation("Ambervale", location_id=None)),
    "create_place": Case(creation("Lamp Hollow", location_id=region)),
    "create_resource": Case(creation("Amber Seam", location_id=region)),
    "found_settlement": Case(creation("Lanternford", location_id=region)),
    "create_species": Case(creation("Ridge Hare", location_id=region)),
    "create_people": Case(creation("Vale Folk", location_id=region)),
    "create_mortal": Case(creation("Tamsin Reed", location_id=settlement)),
    "forge_item": Case(creation("Ledger Lamp", location_id=settlement)),
    "build_structure": Case(creation("Lamp Tower", location_id=settlement)),
    "create_language": Case(creation("Valen", words=[{"word": "orin", "meaning": "road"}])),
    "tell_legend": Case(creation("The Long Road")),
    "found_tradition": Case(creation("Lamp Night")),
    "found_cult": Case(creation("Keepers of Lamps", location_id=region)),
    "found_faction": Case(creation("Road Wardens", location_id=region)),
    "hang_celestial": Case(creation("The Lantern Moon")),
    "create_artwork": Case(creation("Song of Roads", location_id=settlement)),
    "decree_law": Case(creation("Law of Roads", location_id=settlement)),
    "summon_spirit": Case(creation("Road Warden Spirit", location_id=region)),
    "inspire_knowledge": Case(creation("Lampwork")),
    "utter_prophecy": Case(creation("The Lantern Sign")),
    "start_event": Case(creation("The Lamp Fair", location_id=settlement)),
    "create_vessel": Case(creation("Road Barge", location_id=settlement)),
    "raise_beast": Case(creation("Old Greyback", species_id=species, location_id=region)),
    "decree_natural_law": Case(creation("Law of Lamps")),
    "harvest_resource": Case(plain(resource_id=resource)),
    "open_cosmic_bed": Case(plain(region_id=region, reason=REASON), travel_resource),
    "open_trade_route": Case(plain(first_id=settlement, second_id=created("settlement"), reason=REASON), combined(second_settlement, surveyed)),
    "close_trade_route": Case(
        plain(route_id=created("trade_route"), reason=REASON),
        combined(second_settlement, surveyed),
        prelude=(Step("open_trade_route", plain(first_id=settlement, second_id=created("settlement"), reason=REASON)),),
        lookup=last_trade_route,
    ),
    "affect_entity": Case(plain(entity_id=people, changes=[{"stat": "population", "percent": 10}], reason=REASON)),
    "declare_chosen": Case(plain(mortal_id=mortal, boon="a lamp that never fails")),
    "curse": Case(plain(entity_id=faction, curse="their roads shall wander")),
    "send_dream": Case(plain(target_id=mortal, dream="A road of lamps leading to the high pass.")),
    "teach_knowledge": Case(plain(target_id=people, knowledge_id=knowledge, how="by lamplight at the gates")),
    "advance_knowledge": Case(plain(knowledge_id=knowledge, how="by lamplight at the gates")),
    "reveal_truth": Case(plain(community_id=people, domain="cosmology", name="The Turning Sky", claim=TEXT[:200])),
    "miracle": Case(plain(entity_id=people, how="the lamps burned through the night")),
    "send_disaster": Case(plain(target_id=region, name="The Long Flood", description="The river rose over the low fields.", reason=REASON)),
    "transform": Case(plain(entity_id=faction, new_description=TEXT, reason=REASON)),
    "destroy": Case(plain(entity_id=faction, reason=REASON)),
    "loose_disease": Case(plain(target_id=people, name="Grey Cough", target_functions=["breath"], reason=REASON)),
    "incite_war": Case(plain(a_id=people, b_id=other_people, pretext="the river border was crossed")),
    "make_interworld_treaty": Case(plain(a_id=people, b_id=other_people, terms="free passage on the light sail")),
    "war_on_foreign_god": Case(plain(god_id=god, reason=REASON)),
    "wage_war": Case(plain(attacker_id=people, defender_id=other_people, reason=REASON)),
    "raise_host": Case(plain(community_id=people, soldiers=50)),
    "disband_host": Case(
        plain(army_id=created("army"), reason=REASON), prelude=(Step("raise_host", plain(community_id=people, soldiers=40)),), lookup=last_war
    ),
    "lay_siege": Case(
        plain(war_id=created("war"), army_id=created("army"), settlement_id=settlement),
        prelude=WAR,
        lookup=last_war,
    ),
    "offer_peace": Case(plain(war_id=created("war"), victor_id=people, terms=["tribute"]), prelude=WAR, lookup=last_war),
    "commission_vessel": Case(plain(owner_id=people, name="Lamp Runner")),
    "design_unit": Case(plain(owner_id=people, name="Road Guard")),
    "plant_spies": Case(plain(owner_id=people, target_id=faction)),
    "seal_treaty": Case(plain(parties=lambda realm, _ids: [{"party_id": realm.people_id}, {"party_id": realm.settlement_id}])),
    "void_treaty": Case(
        plain(treaty_id=created("treaty"), breaker_id=people),
        prelude=(Step("seal_treaty", plain(parties=lambda realm, _ids: [{"party_id": realm.people_id}, {"party_id": realm.settlement_id}])),),
        lookup=last_treaty,
    ),
    "bless_bloodline": Case(plain(house_id=created("house")), house),
    "take_life": Case(plain(entity_id=mortal, how="a quiet end in sleep")),
    "resurrect_sibling": Case(plain(son_id=sibling), dead_sibling),
    "scatter_bones": Case(plain(son_id=sibling), dead_sibling),
    "reveal_tenet": Case(plain(cult_id=cult)),
    "open_rebirth_gate": Case(plain(spirit_id=created("spirit"), community_id=people), death_son),
    "move_to_world": Case(plain(world_id=lambda realm, _ids: realm.other_world_id)),
    "sever_ley": Case(plain(line_id=created("line"), reason=REASON), ley_line),
    "reorder_seasons": Case(plain(world_id=world, order=lambda _realm, ids: list(reversed(range(ids["seasons"])))), seasons),
    "shape_weather": Case(plain(region_id=region, reason=REASON), combined(sky_son, surveyed)),
    "declare_holy_world": Case(plain(world_id=world)),
    "seal_gate": Case(plain(route_id=route, reason=REASON)),
    "rekindle_star": Case(plain(star_id=created("star")), dead_star),
    "bind_spirit": Case(plain(spirit_id=created("spirit"), target_id=created("item")), combined(spirit, item)),
    "hang_star": Case(plain(name="Lamplight", description="A small steady star over the valley.")),
    "extinguish_star": Case(plain(star_id=created("star"), reason="its light has run its course"), home_star),
    "talk_to_foreign_god": Case(plain(god_id=god, words="Let us speak of the roads between us.")),
    "seal_leak": Case(plain(how="by lamplight and prayer"), leaking_world),
    "bargain_with_outsider": Case(plain(outsider_id=created("outsider"), request="a road through the far dark"), outsider),
    "birth_world": Case(plain(inspiration="A world of long valleys and lamplit roads.")),
    "raise_district": Case(plain(settlement_id=settlement, kind="market", reason=REASON)),
    "design_district": Case(plain(name="Lamp Ward", reason=REASON)),
    "shape_folk": Case(plain(people_id=people, endogamous=True, reason=REASON)),
    "forge_material": Case(plain(world_id=world, name="Lampglass", reason=REASON)),
    "commission_structure": Case(plain(community_id=settlement)),
    "commission_artwork": Case(plain(name="Road Hymn")),
    "design_rite": Case(plain(name="Lamp Rite", power=2, workings=[{"effect": "heal", "magnitude": 10}])),
    "cast_rite": Case(
        plain(rite_id=created("rite"), target_id=people),
        prelude=(Step("design_rite", plain(name="Lamp Rite", power=2, workings=[{"effect": "heal", "magnitude": 10}])),),
        lookup=last_rite,
    ),
    "found_school": Case(plain(name="School of Ledgers", tenets=["legalism"], founder_id=mortal), knows_written_law),
    "hide_secret": Case(plain(place_id=place, reason=REASON)),
    "sanctify_place": Case(plain(place_id=place, reason=REASON)),
    "raise_nexus": Case(plain(place_id=place, reason=REASON), surveyed),
    "reshape_land": Case(plain(region_id=region, act="green", reason=REASON), surveyed),
    "sow_crop": Case(plain(region_id=region, plant_id=plant_kind), plant),
    "sanctify_region": Case(plain(region_id=region, reason=REASON), surveyed),
    "curse_region": Case(plain(region_id=region, strength=20, reason=REASON), surveyed),
    "redirect_river": Case(plain(from_region_id=region, to_region_id=created("region"), reason=REASON), combined(second_region, surveyed)),
    "tend_land": Case(plain(region_id=region, reason=REASON), surveyed),
    "shape_blood": Case(plain(mortal_id=mortal, locus="height", allele="tall", reason=REASON)),
    "reveal_true_name": Case(plain(bearer_id=created("spirit"), learner_id=mortal, reason=REASON), named_spirit),
}
