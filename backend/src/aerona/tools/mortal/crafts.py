from typing import Any

from sqlalchemy import select

from aerona.catalog.kinds.crafts_labels import GAME_LABELS
from aerona.db.tables.crafts import InsurancePolicyRow, InsurerRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.kind_crafts import GameCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.crafts import control
from aerona.engine.crafts.games import made_by, shaped
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.language.generator import NameKind
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class BuyInsuranceInput(ToolInput):
    insurer_id: int


class InventGameInput(ToolInput):
    kind: GameCategory


async def buy_insurance(call: MortalCall, args: BuyInsuranceInput) -> str:
    row = await call.session.get(InsurerRow, args.insurer_id)
    insurer = await living_entity(call.session, args.insurer_id)
    if row is None or insurer is None or row.ruined:
        fail(MortalResult.INSURANCE_DECLINED, why="no one insures by that name")
    if insurer.location_id != call.me.location_id:
        fail(MortalResult.INSURANCE_DECLINED, why="it insures in another town")
    taken = await call.session.scalar(
        select(InsurancePolicyRow.id)
        .where(InsurancePolicyRow.holder_node_id == call.me.id, InsurancePolicyRow.cover == InsuranceCover.LIFE, InsurancePolicyRow.active.is_(True))
        .limit(1)
    )
    if taken is not None:
        fail(MortalResult.INSURANCE_DECLINED, why="your life is insured already")
    table = call.tick.rules.insurance
    premium = max(1, round(table.sum_insured * row.premium_pct / 100))
    if await points_of(call.session, call.me) < premium:
        fail(MortalResult.INSURANCE_DECLINED, why="you cannot pay the first premium")
    await shift_points(call.session, call.me, -premium)
    row.pool += premium
    await control.set_record(
        call.tick,
        "insurance_policy",
        {},
        {
            "insurer_entity_id": insurer.id,
            "holder_node_id": call.me.id,
            "cover": InsuranceCover.LIFE,
            "premium": premium,
            "sum_insured": table.sum_insured,
            "since_epoch": call.tick.epoch,
        },
    )
    call.target(insurer.id)
    await call.record(
        "tools.mortal.buy_insurance",
        roles={IncidentRole.BUYER: call.me.id, IncidentRole.SELLER: insurer.id},
        facts={"cover": InsuranceCover.LIFE, "premium": premium, "sum_insured": table.sum_insured},
    )
    return result(MortalResult.INSURANCE_BOUGHT, insurer=insurer.name, premium=premium)


async def invent_game(call: MortalCall, args: InventGameInput) -> str:
    people = await people_of(call.session, call.me)
    if people is None:
        fail(MortalResult.GAME_DECLINED, why="you belong to no people to play it")
    if held(people.id):
        fail(MortalResult.GAME_DECLINED, why="your people is held as it is")
    name = await Namer(call.session, call.tick.rules).from_speaker(people.id, seed_of("game.tool", call.me.id, call.tick.epoch), NameKind.GENERAL)
    if name is None:
        fail(MortalResult.GAME_DECLINED, why="your people has no tongue to name it in")
    game = shaped(name, args.kind, people, call.tick.epoch)
    call.session.add(game)
    await call.session.flush()
    call.session.add(made_by(game, people.id, call.tick.epoch))
    call.target(people.id)
    await call.record(
        "tools.mortal.invent_game", roles={IncidentRole.MAKER: call.me.id, IncidentRole.MEMBER: people.id}, facts={"game": name, "category": args.kind}
    )
    return result(MortalResult.GAME_INVENTED, game=name, people=people.name, sort=GAME_LABELS[args.kind.value].lower())


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BUY_INSURANCE, mortal, BuyInsuranceInput, meta, buy_insurance),
        ToolSpec(MortalToolId.INVENT_GAME, mortal, InventGameInput, meta, invent_game),
    ]
