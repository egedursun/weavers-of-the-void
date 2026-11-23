from typing import Any

from aerona.catalog.identity import IDENTITY_LAYERS
from aerona.core.grammar import spoken
from aerona.db.tables.belonging import HeldIdentityRow, SatireRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.belonging import IdentityLayer, SatireSource
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.belonging import control
from aerona.engine.belonging.refuge import refuge_of
from aerona.engine.belonging.sanctuary import fugitives, host_for
from aerona.engine.belonging.satire import SatireTally, judge
from aerona.engine.belonging.values import mortal_values
from aerona.engine.collective.book import ruler_id
from aerona.engine.cycles.book import realm_of
from aerona.engine.mind.book import skills_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class SeekSanctuaryInput(ToolInput):
    pass


class MockTheRulerInput(ToolInput):
    pass


class ClaimIdentityInput(ToolInput):
    layer: IdentityLayer
    loosen: bool = False


async def seek_sanctuary(call: MortalCall, args: SeekSanctuaryInput) -> str:
    me = call.me
    if await refuge_of(call.session, me.id) is not None:
        fail(MortalResult.SANCTUARY_DENIED, why="you already have sanctuary")
    hunted = next((item for item in await fugitives(call.tick) if item.mortal.id == me.id), None)
    if hunted is None:
        fail(MortalResult.SANCTUARY_DENIED, why="no one hunts you")
    found = await host_for(call.tick, hunted)
    if found is None:
        fail(MortalResult.SANCTUARY_DENIED, why="no temple or welcoming host in your town will take you in")
    host, kind = found
    await control.set_record(
        call.tick,
        "sanctuary",
        {},
        {
            "fugitive_entity_id": me.id,
            "host_entity_id": host.id,
            "kind": kind,
            "fugitive_kind": hunted.kind,
            "pursuer_entity_id": hunted.pursuer,
            "fee": call.tick.rules.sanctuary.fee,
        },
    )
    call.target(host.id)
    await call.record(
        "tools.mortal.seek_sanctuary",
        roles={IncidentRole.ACTOR: me.id, IncidentRole.HOST: host.id, IncidentRole.OPPONENT: hunted.pursuer},
        facts={"fee": call.tick.rules.sanctuary.fee},
    )
    return result(MortalResult.SANCTUARY_FOUND, host=host.name)


async def mock_the_ruler(call: MortalCall, args: MockTheRulerInput) -> str:
    me = call.me
    realm = await realm_of(call.session, me.location_id) if me.location_id is not None else None
    ruler = await ruler_id(call.tick, realm) if realm is not None else None
    if realm is None or ruler is None:
        fail(MortalResult.SATIRE_DECLINED, why="your town answers to no ruler")
    if ruler == me.id:
        fail(MortalResult.SATIRE_DECLINED, why="you cannot mock yourself as ruler")
    oratory = (await skills_of(call.session, me.id)).get(SkillKind.ORATORY)
    bite = clamp_int(call.tick.rules.satire.bite + (oratory.level if oratory is not None else 0) * 2, 0, 100)
    row = await control.set_record(
        call.tick,
        "satire",
        {},
        {"satirist_entity_id": me.id, "target_entity_id": ruler, "polity_entity_id": realm, "source": SatireSource.MORTAL, "bite": bite},
    )
    if isinstance(row, SatireRow):
        await judge(call.tick, row, SatireTally())
    call.target(ruler)
    await call.record("tools.mortal.mock_the_ruler", roles={IncidentRole.ACTOR: me.id, IncidentRole.TARGET: ruler}, facts={"bite": bite}, place=me.location_id)
    return result(MortalResult.SATIRE_TOLD, bite=bite, tolerated=isinstance(row, SatireRow) and row.tolerated)


async def claim_identity(call: MortalCall, args: ClaimIdentityInput) -> str:
    me = call.me
    layer = spoken(args.layer)
    if held(me.id):
        fail(MortalResult.IDENTITY_UNCLAIMED, why="your sense of self is held")
    value_node_id, value_label = (await mortal_values(call.session, await RegionAtlas.load(call.session), me))[args.layer]
    if value_node_id is None and value_label is None:
        fail(MortalResult.IDENTITY_UNCLAIMED, why=f"you have no {layer} to claim")
    row = await call.session.get(HeldIdentityRow, (me.id, args.layer))
    if row is not None and "strength" in row.locked:
        fail(MortalResult.IDENTITY_UNCLAIMED, why=f"how much your {layer} counts is held")
    step = call.tick.rules.identities.rhetoric
    current = row.strength if row is not None else 50
    strength = clamp_int(current - step if args.loosen else current + step, 0, 100)
    fresh = (
        {} if row is not None else {"value_node_id": value_node_id, "value_label": value_label, "salience": IDENTITY_LAYERS[args.layer].base(call.tick.rules)}
    )
    await control.set_record(call.tick, "held_identity", {"holder_entity_id": me.id, "layer": args.layer}, {"strength": strength, **fresh})
    call.target(me.id)
    await call.record(
        "tools.mortal.claim_identity", roles={IncidentRole.SUBJECT: me.id}, facts={"layer": args.layer, "strength": strength}, place=me.location_id
    )
    return result(MortalResult.IDENTITY_CLAIMED, layer=layer, strength=strength)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SEEK_SANCTUARY, mortal, SeekSanctuaryInput, meta, seek_sanctuary),
        ToolSpec(MortalToolId.MOCK_THE_RULER, mortal, MockTheRulerInput, meta, mock_the_ruler),
        ToolSpec(MortalToolId.CLAIM_IDENTITY, mortal, ClaimIdentityInput, meta, claim_identity),
    ]
