from typing import Any

from tests.tools.every_setup import (
    cosmic_being,
    court_diviners,
    created,
    dead_creation,
    dead_sibling,
    dead_star,
    death_son,
    dreamer,
    faith_crisis,
    falling_body,
    friendly_sibling,
    heavens,
    home_star,
    house,
    hungry_town,
    item,
    knows_written_law,
    last_rite,
    last_trade_route,
    last_treaty,
    last_war,
    leaking_world,
    learning_house,
    ley_line,
    named_spirit,
    near_moon,
    offered_town,
    on_the_road,
    oracle_case,
    outsider,
    pact_friend,
    phenomenon,
    plant,
    rewritten_account,
    rich_son,
    rifted,
    rival_realm,
    ruled_law,
    ruled_realm,
    seasons,
    second_mortal,
    second_region,
    second_settlement,
    sickness,
    sky_son,
    son_creature,
    son_enchantment,
    son_geas,
    son_legend,
    son_office,
    son_plan,
    son_servitor,
    spirit,
    spirit_office,
    surveyed,
    tongue_words,
    town_profile,
    travel_resource,
    turf_held,
    two_stars,
    war_theatre,
    world_body,
    wounded,
)
from tests.tools.every_setup_ages import long_winter, open_tale, turning_cosmos
from tests.tools.every_setup_arts import art_work, built_construct, forged_work, two_clubs, wild_beast
from tests.tools.every_setup_crafts import material_resource
from tests.tools.every_setup_eras import realm_programme
from tests.tools.every_setup_folkways import owned_item
from tests.tools.every_setup_nature import first_kind, second_kind, two_kinds
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
    "raise_beast": Case(creation("Old Greyback", species_id=species, location_id=region, breath="frost", temperament="abductor", habitat="deep")),
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
    "convene_gathering": Case(plain(host_id=people, kind="festival", reason=REASON)),
    "raise_divine_creature": Case(plain(home_id=region, name="Grey Warden", description=REASON), rich_son),
    "teach_creature": Case(plain(creature_id=created("creature"), deed="tend_fields", lesson="reward", reason=REASON), son_creature),
    "release_creature": Case(plain(creature_id=created("creature"), reason=REASON), son_creature),
    "shape_image": Case(plain(stance="embrace", reason=REASON)),
    "make_servitor": Case(plain(name="Watcher of the Gate", rank="guardian", role="guard", post_id=place, reason=REASON), rich_son),
    "command_servitor": Case(plain(servitor_id=created("servitor"), role="judge", reason=REASON), son_servitor),
    "release_servitor": Case(plain(servitor_id=created("servitor"), reason=REASON), son_servitor),
    "lay_geas": Case(plain(bearer_id=mortal, mode="taboo", act="theft", reason=REASON)),
    "lift_geas": Case(plain(geas_id=created("geas"), reason=REASON), son_geas),
    "call_heroquest": Case(plain(quester_id=mortal, legend_id=created("legend"), reason=REASON), son_legend),
    "resign_office": Case(plain(office="dead", reason=REASON), son_office),
    "lay_enchantment": Case(plain(name="The Long Calm", effect="bounty", strength=30, reason=REASON)),
    "end_enchantment": Case(plain(law_id=created("law"), reason=REASON), son_enchantment),
    "reveal_tongue": Case(plain(mortal_id=mortal, reason=REASON)),
    "mark_lineage": Case(plain(species_id=species, reason=REASON)),
    "shield_convoy": Case(plain(convoy_id=created("convoy"), reason=REASON), on_the_road),
    "scour_streets": Case(plain(district_id=created("district"), reason=REASON), turf_held),
    "answer_oracle": Case(plain(case_id=created("case"), verdict="acquitted", reason=REASON), oracle_case),
    "read_dreams": Case(plain(mortal_id=created("mortal"), reason=REASON), dreamer),
    "stir_crowd": Case(plain(town_id=settlement, grievance="sermon", reason=REASON), town_profile),
    "reveal_true_history": Case(plain(account_id=created("revision"), reason=REASON), rewritten_account),
    "set_storylet": Case(plain(storylet="hoarded_store", reason=REASON), hungry_town),
    "move_plague_response": Case(plain(community_id=settlement, disease_id=created("disease"), response="quarantine", reason=REASON), sickness),
    "decree_sound": Case(plain(language_id=language, kind="shift", source="a", target="e", reason=REASON), tongue_words),
    "veil_name": Case(plain(language_id=language, node_id=mortal, reason=REASON), tongue_words),
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
    "design_unit": Case(plain(owner_id=people, name="Road Guard", base_kind="line_infantry", doctrine="shock", formation="line")),
    "shape_vehicle_type": Case(plain(owner_id=people, frame="wagon", emphasis="hold", mounts=["deck"], description=TEXT[:200])),
    "shape_equipment": Case(plain(owner_id=people, family="spear", material="iron", quality=70)),
    "shape_dish": Case(plain(owner_id=people, method="stewed", course="festive", ingredients=["meat", "tubers"])),
    "shape_structure_type": Case(plain(owner_id=people, structure_kind="granary", form="hall", storeys=2, material="stone")),
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
    "hang_star": Case(plain(name="Lamplight", description="A small steady star over the valley.", galaxy_id=created("galaxy")), heavens),
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
    "set_aim": Case(plain(kind="be_worshipped", amount=3)),
    "take_mortal_form": Case(plain(place_id=people, reason=REASON)),
    "ward_against_outer": Case(plain(outsider_id=created("outsider"), reason=REASON), outsider),
    "seal_divine_pact": Case(plain(god_id=god, reason=REASON), pact_friend),
    "mend_wound": Case(plain(wound_id=created("wound"), essence=5), wounded),
    "open_rift": Case(plain(region_id=region, dimension_id=created("dimension"), reason=REASON), heavens),
    "seal_rift": Case(plain(rift_id=created("rift"), reason=REASON), rifted),
    "call_cosmic_being": Case(plain(kind="void_shepherd", region_id=region, reason=REASON)),
    "bind_cosmic_being": Case(plain(being_id=created("being"), reason=REASON), cosmic_being),
    "banish_cosmic_being": Case(plain(being_id=created("being"), reason=REASON), cosmic_being),
    "strike_being": Case(plain(being_id=created("being"), force=2, reason=REASON), cosmic_being),
    "contain_phenomenon": Case(plain(phenomenon_id=created("phenomenon"), reason=REASON), phenomenon),
    "turn_region_climate": Case(plain(region_id=region, turn="warmer", reason=REASON), surveyed),
    "claim_galaxy": Case(plain(galaxy_id=created("galaxy"), reason=REASON), heavens),
    "rule_dimension": Case(plain(dimension_id=created("prime"), reason=REASON), heavens),
    "create_galaxy": Case(plain(name="Second Wheel", galaxy_type="spiral", description="A wide galaxy far from the first.")),
    "create_cluster": Case(plain(name="Far Gathering", kind="filament", dimension_id=created("prime"), description="A long line of galaxies."), heavens),
    "create_dimension": Case(
        plain(name="Quiet Deep", kind="astral", parent_dimension_id=created("prime"), description="A still place beside the first."), heavens
    ),
    "shape_galactic_structure": Case(plain(galaxy_id=created("galaxy"), kind="dark_nebula", name="Dark Lane", reason=REASON), heavens),
    "stir_galaxy": Case(plain(galaxy_id=created("galaxy"), kind="starburst", reason=REASON), heavens),
    "stir_dimension": Case(plain(dimension_id=created("prime"), kind="veil_thinning", reason=REASON), heavens),
    "bind_law_across_dimension": Case(plain(dimension_id=created("prime"), law_id=created("law"), reason=REASON), ruled_law),
    "set_cosmic_feature": Case(plain(kind="asteroid_field", name="Near Belt", star_id=created("star"), reason=REASON), home_star),
    "gather_star_system": Case(plain(name="Twin Hearth", star_ids=lambda _realm, ids: [ids["first_star"], ids["second_star"]], reason=REASON), two_stars),
    "raise_phenomenon": Case(plain(kind="singing_stones", region_id=region, reason=REASON)),
    "open_breach": Case(plain(being_id=created("outsider"), region_id=region, reason=REASON), outsider),
    "forge_ley_line": Case(plain(first_region_id=region, second_region_id=created("region"), reason=REASON), combined(second_region, surveyed)),
    "add_season": Case(plain(world_id=world, name="Long Thaw"), sky_son),
    "open_road": Case(plain(first_world_id=world, second_world_id=lambda realm, _ids: realm.other_world_id, method="light_sail", reason=REASON)),
    "raise_throne": Case(plain(place_id=place, reason=REASON)),
    "lay_magic_site": Case(plain(place_id=place, kind="source", school="earth", reason=REASON)),
    "carry_species": Case(plain(species_id=species, region_id=created("region"), reason=REASON), second_region),
    "seed_life": Case(plain(world_id=world, reason=REASON)),
    "call_up_soul": Case(plain(mortal_id=created("dead"), reason=REASON), dead_creation),
    "crown_ruler": Case(plain(community_id=other_people, reason=REASON)),
    "found_house": Case(plain(mortal_id=mortal, reason=REASON)),
    "bless_host": Case(
        plain(army_id=created("army"), aspect="morale", reason=REASON), prelude=(Step("raise_host", plain(community_id=people, soldiers=40)),), lookup=last_war
    ),
    "claim_star": Case(plain(star_id=created("star"), reason=REASON), home_star),
    "call_impact": Case(plain(region_id=region, reason=REASON)),
    "deflect_impact": Case(plain(impact_id=created("impact"), reason=REASON), falling_body),
    "terraform_world": Case(plain(world_id=world, aim="warm", reason=REASON), world_body),
    "break_moon": Case(plain(moon_id=created("moon"), reason=REASON), near_moon),
    "shape_blood": Case(plain(mortal_id=mortal, locus="height", allele="tall", reason=REASON)),
    "reveal_true_name": Case(plain(bearer_id=created("spirit"), learner_id=mortal, reason=REASON), named_spirit),
    "answer_offerings": Case(plain(community_id=settlement, generous=True, reason=REASON), offered_town),
    "begin_long_plan": Case(plain(kind="wonder", name="The Long Work", target_id=settlement, steps=5, secrecy=60, reason=REASON)),
    "further_plan": Case(plain(plan_id=created("plan"), reason=REASON), son_plan),
    "shape_kinship": Case(
        plain(people_id=people, descent="matrilineal", residence="matrilocal", preference="cross_cousin", payment="bride_price", reason=REASON)
    ),
    "shape_reproduction": Case(plain(people_id=people, system="sequential", reason=REASON)),
    "try_realm": Case(plain(polity_id=created("polity"), kind="famine", severity=30, reason=REASON), ruled_realm),
    "set_circuit": Case(plain(name="The First Round", stop_ids=lambda realm, ids: [realm.settlement_id, ids["settlement"]], reason=REASON), second_settlement),
    "shape_rule": Case(plain(polity_id=created("polity"), selectorate="council", public_share=60, reason=REASON), ruled_realm),
    "anoint_founder": Case(plain(polity_id=created("polity"), reason=REASON), ruled_realm),
    "free_learning": Case(plain(structure_id=created("structure"), level=70, reason=REASON), learning_house),
    "inspire_school": Case(plain(founder_id=mortal, name="The First School", reason=REASON)),
    "designate_keystone": Case(plain(species_id=lambda realm, ids: realm.species_id, region_id=region, name="The First Yield", use="rite", reason=REASON)),
    "inspire_relief": Case(plain(giver_id=lambda realm, ids: realm.cult_id, settlement_id=settlement, kind="healers", reason=REASON)),
    "send_expedition": Case(plain(leader_id=mortal, target_id=region, reason=REASON)),
    "stock_depot": Case(plain(owner_id=people, region_id=region, reason=REASON)),
    "steer_theatre": Case(plain(theatre_id=created("theatre"), priority=70, reason=REASON), war_theatre),
    "mark_quirk": Case(plain(mortal_id=mortal, kind="hardy", reason=REASON)),
    "limit_fleets": Case(plain(first_id=created("polity"), second_id=created("rival"), tonnage=200, reason=REASON), rival_realm),
    "bind_genius_locus": Case(plain(place_id=place, reason=REASON)),
    "judge_petition": Case(plain(petition_id=created("petition"), granted=True, reason=REASON), spirit_office),
    "appoint_spirit": Case(plain(spirit_id=created("spirit"), rank="province", reason=REASON), spirit_office),
    "answer_mystic": Case(plain(mortal_id=mortal, reason=REASON)),
    "ease_theodicy": Case(plain(crisis_id=created("crisis"), reason=REASON), faith_crisis),
    "teach_sacrament": Case(plain(cult_id=cult, kind="birth_blessing", protection="possession", reason=REASON)),
    "align_afterlife": Case(plain(cult_id=cult, reason=REASON)),
    "sway_diviner": Case(plain(realm_id=created("polity"), question="war", verdict="inauspicious", reason=REASON), court_diviners),
    "grant_foresight": Case(plain(mortal_id=mortal, subject_id=settlement, reason=REASON)),
    "feed_on": Case(plain(emotion="awe", weight=70, reason=REASON)),
    "build_construct": Case(plain(maker_id=mortal, material="stone", source="ley", reason=REASON)),
    "order_construct": Case(plain(construct_id=created("construct"), kind="protect", target_id=mortal, reason=REASON), built_construct),
    "seize_construct": Case(plain(construct_id=created("construct"), reason=REASON), built_construct),
    "expose_forgery": Case(plain(forgery_id=created("forgery"), reason=REASON), forged_work),
    "canonise_work": Case(plain(people_id=people, artwork_id=created("artwork"), reason=REASON), art_work),
    "inspire_movement": Case(plain(town_id=settlement, reason=REASON), art_work),
    "rig_match": Case(plain(home_id=created("home"), away_id=created("away"), winner_id=created("away"), reason=REASON), two_clubs),
    "set_beast_bounty": Case(plain(town_id=settlement, beast_id=created("beast"), reason=REASON), wild_beast),
    "mark_birth": Case(plain(mortal_id=mortal, dreaded=True, reason=REASON)),
    "unsettle_seasons": Case(plain(world_id=world, reason=REASON)),
    "lengthen_winter": Case(plain(world_id=world, epochs=2, reason=REASON), long_winter),
    "press_tale": Case(plain(arc_id=created("arc"), reason=REASON), open_tale),
    "foreshadow": Case(plain(subject_id=mortal, reason=REASON)),
    "echo_life": Case(plain(mortal_id=mortal, reason=REASON), turning_cosmos),
    "nudge_bias": Case(plain(mortal_id=mortal, bias="sunk_cost", weight=80, reason=REASON)),
    "declare_impurity": Case(plain(people_id=people, source="the_dead", reason=REASON)),
    "bless_charm": Case(plain(item_id=created("item"), power="luck", reason=REASON), owned_item),
    "send_misfortune": Case(plain(town_id=settlement, kind="crop_failure", victim_id=mortal, reason=REASON)),
    "stir_witch_hunt": Case(plain(town_id=settlement, reason=REASON)),
    "stir_revival": Case(plain(people_id=people, goal="revive_language", reason=REASON)),
    "proclaim_right": Case(plain(realm_id=created("polity"), category="resident_foreigner", right="arms", granted=True, reason=REASON), ruled_realm),
    "wake_spirit": Case(plain(region_id=region, emotion="awe", reason=REASON)),
    "lay_affinity": Case(plain(resource_id=resource, school="earth", mode="worn", reason=REASON), material_resource),
    "stir_monsoon": Case(plain(world_id=world, strong=False, reason=REASON)),
    "turn_wind": Case(plain(region_id=region, wind_from=4, reason=REASON)),
    "bind_species": Case(
        plain(first_species_id=first_kind, second_species_id=second_kind, kind="mutualism", reason=REASON),
        two_kinds,
    ),
    "sharpen_sense": Case(plain(holder_id=people, sense="smell", reason=REASON)),
    "sabotage_programme": Case(plain(programme_id=lambda _realm, ids: ids["programme"], reason=REASON), realm_programme),
    "stir_identity": Case(plain(community_id=people, layer="faith", reason=REASON)),
}
