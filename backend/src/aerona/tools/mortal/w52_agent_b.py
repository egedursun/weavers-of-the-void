from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.finance import COVERS, LOAN_STATES, PLAYS
from aerona.catalog.life.collective import ACCOUNT_KINDS, ACCOUNT_STANCES
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.catalog.urban import MERCHANT_HOUSES
from aerona.constants.tool_inputs import DESCRIPTION_MAX, DESCRIPTION_MIN, NAME_MAX, NAME_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.crafts import InsurancePolicyRow, InsurerRow
from aerona.db.tables.economy import LoanRow, WorkshopRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.finance import SpeculationRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.tongues import LanguagePolicyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.finance import SpeculationStatus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.tongues import LanguagePolicy
from aerona.domain.enums.urban import MarketPlay
from aerona.engine.body.customs import people_of
from aerona.engine.collective.accounts import record as write_account_row
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.finance.speculation import seize_hoard
from aerona.engine.finance.w52_credit import open_loans, repudiate, reschedule, rescue, sell
from aerona.engine.lore.language import learn_second
from aerona.engine.mind.book import skill_level
from aerona.engine.primitives.queries import living_entity, spoken_language
from aerona.engine.recording.record import record as write_record
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.tongues.modality import own_tongue
from aerona.engine.tongues.policy import communities_under
from aerona.engine.tongues.scripts import impose, script_of
from aerona.engine.tongues.stages import made_tongue
from aerona.engine.urban.control import set_play
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.shared_inputs import WordInput, add_words
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import MortalCreation, create_record, name_free
from aerona.tools.mortal.tongues import realm_of
from aerona.tools.mortal.urban_depth import led
from aerona.tools.mortal.works import works_of

FIRST_SHARE = 10
MAX_PUT_OFF = 10
PLAYED = 60


class ConstructLanguageInput(ToolInput):
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    description: Annotated[str, Field(min_length=DESCRIPTION_MIN, max_length=DESCRIPTION_MAX)]
    words: Annotated[list[WordInput], Field(min_length=1)]


class ImposeScriptInput(ToolInput):
    language_id: int


class FoundWorkshopInput(ToolInput):
    kind: WorkshopKind


class ComposeAccountInput(ToolInput):
    incident_id: int
    kind: AccountKind
    stance: AccountStance


async def construct_language(call: MortalCall, args: ConstructLanguageInput) -> str:
    if await skill_level(call.session, call.me.id, SkillKind.LANGUAGES) <= 0:
        fail(MortalResult.CONSTRUCT_REFUSED, why="you know nothing of languages")
    await name_free(call, args.name)
    language = await create_record(call, MortalCreation(args.name, EntityType.LANGUAGE, args.description))
    await made_tongue(call.tick, language, call.me.id)
    added = await add_words(
        call.session, language, args.words[: call.rules.mortal_tools.coin_word_max_words], actor=(ActorKind.MORTAL, call.me.id), epoch=call.epoch
    )
    home = call.me.location_id
    if home is not None:
        await learn_second(call.tick, home, language.id, FIRST_SHARE)
    call.target(language.id)
    await call.record("tools.mortal.construct_language", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PRODUCT: language.id}, facts={"words": len(added)})
    return result(MortalResult.LANGUAGE_CONSTRUCTED, name=language.name, words=len(added))


async def realm_tongue(call: MortalCall, realm: int) -> EntityRow | None:
    official = await call.session.scalar(
        select(LanguagePolicyRow.language_entity_id)
        .where(LanguagePolicyRow.holder_entity_id == realm, LanguagePolicyRow.policy == LanguagePolicy.OFFICIAL)
        .order_by(LanguagePolicyRow.language_entity_id)
        .limit(1)
    )
    if official is not None:
        return await call.session.get(EntityRow, official)
    return await own_tongue(call.session, call.me)


async def impose_script(call: MortalCall, args: ImposeScriptInput) -> str:
    realm = await realm_of(call)
    if realm is None:
        fail(MortalResult.IMPOSE_REFUSED, why="you rule no realm")
    subject = await living_entity(call.session, args.language_id)
    if subject is None or subject.entity_type is not EntityType.LANGUAGE:
        fail(MortalResult.IMPOSE_REFUSED, why="that is not a tongue")
    own = await realm_tongue(call, realm)
    profile = await call.session.get(LanguageProfileRow, own.id) if own is not None else None
    source = await script_of(call.tick, own, profile) if own is not None and profile is not None else None
    if source is None or own is None:
        fail(MortalResult.IMPOSE_REFUSED, why="your realm's own tongue is not written")
    spoken_here = {
        tongue.id for community in await communities_under(call.tick, realm) if (tongue := await spoken_language(call.session, community.id)) is not None
    }
    if subject.id not in spoken_here or subject.id == own.id:
        fail(MortalResult.IMPOSE_REFUSED, why="no subject of yours speaks that tongue")
    row = await impose(call.tick, realm, subject, source, by=call.me.id)
    if row is None:
        fail(MortalResult.IMPOSE_REFUSED, why="that tongue already writes in your script")
    call.target(subject.id)
    await call.record("tools.mortal.impose_script", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: subject.id}, facts={"system": source.system})
    return result(MortalResult.SCRIPT_IMPOSED, name=subject.name, script=row.name)


async def compose_account(call: MortalCall, args: ComposeAccountInput) -> str:
    happening = await call.session.get(IncidentRow, args.incident_id)
    if happening is None or (happening.world_id is not None and happening.world_id != call.me.world_id):
        fail(MortalResult.COMPOSE_REFUSED, why="you know of no such happening")
    told = [
        node
        for node in await call.session.scalars(select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == happening.id))
        if node != call.me.id
    ]
    community = await call.session.get(EntityRow, call.me.location_id) if call.me.location_id is not None else None
    people = await people_of(call.session, community) if community is not None else None
    holder = people or community or call.me
    medium = AccountMedium.PERFORMANCE if ACCOUNT_KINDS[args.kind].sung else AccountMedium.ORAL
    row = await write_account_row(
        call.tick,
        holder,
        args.kind,
        fidelity=call.rules.historiography.folk_fidelity,
        stances=dict.fromkeys(sorted(set(told)), args.stance),
        incident_id=happening.id,
        medium=medium,
        author_id=call.me.id,
    )
    if row is None:
        fail(MortalResult.COMPOSE_REFUSED, why=f"what {holder.name} remembers is held")
    call.target(holder.id)
    await call.record(
        "tools.mortal.compose_account",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: holder.id},
        facts={"kind": args.kind, "stance": args.stance},
    )
    return result(MortalResult.ACCOUNT_COMPOSED, kind=ACCOUNT_KINDS[args.kind].label.lower(), stance=ACCOUNT_STANCES[args.stance].label.lower(), told=len(told))


async def found_workshop(call: MortalCall, args: FoundWorkshopInput) -> str:
    label = WORKSHOP_LABELS[args.kind].lower()
    community = await works_of(call)
    if community is None:
        fail(MortalResult.FOUND_WORKSHOP_REFUSED, workshop=label, why="you belong to no community with works")
    if held(community.id):
        fail(MortalResult.FOUND_WORKSHOP_REFUSED, workshop=label, why="that place is held as it is")
    have = await call.session.scalar(select(WorkshopRow.id).where(WorkshopRow.community_entity_id == community.id, WorkshopRow.kind == args.kind).limit(1))
    if have is not None:
        fail(MortalResult.FOUND_WORKSHOP_REFUSED, workshop=label, why=f"{community.name} has one already")
    row = WorkshopRow(community_entity_id=community.id, kind=args.kind, level=1, built_epoch=max(1, call.epoch), owner_node_id=call.me.id)
    call.session.add(row)
    await call.session.flush()
    await write_record(call.tick, "workshop.founded", roles={IncidentRole.MAKER: community.id}, facts={"workshop": args.kind}, place=community.id)
    call.target(community.id)
    await call.record(
        "tools.mortal.found_workshop",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: community.id},
        facts={"workshop": args.kind},
        place=community.id,
    )
    return result(MortalResult.WORKSHOP_FOUNDED, workshop=label, place=community.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        *finance_specs(),
        ToolSpec(
            MortalToolId.CONSTRUCT_LANGUAGE, mortal, ConstructLanguageInput, ToolMeta(ActionKind.FOUND_LANGUAGE, mortal_standard_action), construct_language
        ),
        ToolSpec(MortalToolId.COMPOSE_ACCOUNT, mortal, ComposeAccountInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), compose_account),
        ToolSpec(MortalToolId.FOUND_WORKSHOP, mortal, FoundWorkshopInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), found_workshop),
        ToolSpec(MortalToolId.IMPOSE_SCRIPT, mortal, ImposeScriptInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), impose_script),
    ]


class RepudiateInput(ToolInput):
    pass


class RescueInput(ToolInput):
    polity_id: int
    terms: Annotated[int, Field(ge=0, le=PERCENT)]


class RescheduleInput(ToolInput):
    loan_id: int
    extra_epochs: Annotated[int, Field(ge=1, le=MAX_PUT_OFF)]


class SellLoanInput(ToolInput):
    loan_id: int
    buyer_id: int


class InsureInput(ToolInput):
    insurer_id: int
    cover: InsuranceCover


class SeizeHoardsInput(ToolInput):
    settlement_id: int


class PlayMarketInput(ToolInput):
    commodity: CommodityKind
    play: MarketPlay


async def repudiate_debts(call: MortalCall, args: RepudiateInput) -> str:
    realm_id = await realm_of(call)
    realm = await call.session.get(EntityRow, realm_id) if realm_id is not None else None
    if realm is None or held(realm.id):
        fail(MortalResult.REPUDIATE_REFUSED, why="you rule no realm")
    if not await open_loans(call.tick, realm.id):
        fail(MortalResult.REPUDIATE_REFUSED, why="your realm owes nothing")
    voided = await repudiate(call.tick, realm, by=call.me.id)
    call.target(realm.id)
    await call.record("tools.mortal.repudiate_debts", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: realm.id}, facts={"voided": voided})
    return result(MortalResult.DEBTS_REPUDIATED, name=realm.name, voided=voided)


async def rescue_polity(call: MortalCall, args: RescueInput) -> str:
    realm_id = await realm_of(call)
    realm = await call.session.get(EntityRow, realm_id) if realm_id is not None else None
    debtor = await living_entity(call.session, args.polity_id)
    if realm is None:
        fail(MortalResult.RESCUE_REFUSED, why="you rule no realm")
    if debtor is None or debtor.entity_type is not EntityType.POLITY or debtor.id == realm.id or held(debtor.id):
        fail(MortalResult.RESCUE_REFUSED, why="that is no other realm you can carry")
    if not await open_loans(call.tick, debtor.id):
        fail(MortalResult.RESCUE_REFUSED, why=f"{debtor.name} owes nothing")
    await rescue(call.tick, debtor, realm, args.terms, by=call.me.id)
    call.target(debtor.id)
    await call.record("tools.mortal.rescue_polity", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: debtor.id}, facts={"terms": args.terms})
    return result(MortalResult.POLITY_RESCUED, name=debtor.name, terms=args.terms)


async def lender_loan(call: MortalCall, loan_id: int, refused: MortalResult) -> LoanRow:
    loan = await call.session.get(LoanRow, loan_id)
    mine = {call.me.id, *(holder for holder in (await realm_of(call), call.me.affiliated_entity_id) if holder is not None)}
    if loan is None or loan.held or not LOAN_STATES[loan.status].owed or loan.lender_entity_id not in mine:
        fail(refused, why="you hold no such loan that is still owed")
    return loan


async def reschedule_loan(call: MortalCall, args: RescheduleInput) -> str:
    loan = await lender_loan(call, args.loan_id, MortalResult.RESCHEDULE_REFUSED)
    await reschedule(call.tick, loan, args.extra_epochs, by=call.me.id)
    call.target(loan.borrower_entity_id)
    await call.record(
        "tools.mortal.reschedule_loan",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: loan.borrower_entity_id},
        facts={"epochs": args.extra_epochs},
    )
    return result(MortalResult.LOAN_RESCHEDULED, epoch=loan.due_epoch)


async def sell_loan(call: MortalCall, args: SellLoanInput) -> str:
    loan = await lender_loan(call, args.loan_id, MortalResult.SALE_REFUSED)
    buyer = await living_entity(call.session, args.buyer_id)
    if buyer is None or buyer.id in (loan.lender_entity_id, loan.borrower_entity_id) or held(buyer.id):
        fail(MortalResult.SALE_REFUSED, why="no such buyer can take it")
    price = await sell(call.tick, loan, buyer, by=call.me.id)
    if price < 0:
        fail(MortalResult.SALE_REFUSED, why=f"{buyer.name} cannot pay its price")
    call.target(buyer.id)
    await call.record("tools.mortal.sell_loan", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BUYER: buyer.id}, facts={"price": price})
    return result(MortalResult.LOAN_SOLD, name=buyer.name, price=price)


async def insure(call: MortalCall, args: InsureInput) -> str:
    row = await call.session.get(InsurerRow, args.insurer_id)
    insurer = await living_entity(call.session, args.insurer_id)
    if row is None or insurer is None or row.ruined or insurer.location_id != call.me.location_id:
        fail(MortalResult.INSURE_REFUSED, why="no insurer of your town goes by that name")
    holder = call.me if args.cover is InsuranceCover.LIFE else await call.session.get(EntityRow, call.me.location_id)
    if holder is None or held(holder.id):
        fail(MortalResult.INSURE_REFUSED, why="there is nothing of yours to insure so")
    table = call.rules.insurance
    premium = max(1, round(table.sum_insured * row.premium_pct / PERCENT * int(getattr(table, COVERS[args.cover].premium_rule)) / PERCENT))
    if await points_of(call.session, call.me) < premium:
        fail(MortalResult.INSURE_REFUSED, why="you cannot pay the first premium")
    await shift_points(call.session, call.me, -premium)
    if "pool" not in row.locked:
        row.pool += premium
    call.session.add(
        InsurancePolicyRow(
            insurer_entity_id=insurer.id,
            holder_node_id=holder.id,
            cover=args.cover,
            premium=premium,
            sum_insured=table.sum_insured,
            since_epoch=call.epoch,
            locked=[],
        )
    )
    await call.session.flush()
    call.target(insurer.id)
    await call.record("tools.mortal.insure", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PATRON: insurer.id}, facts={"cover": args.cover})
    return result(MortalResult.INSURED, cover=COVERS[args.cover].label.lower(), name=insurer.name, premium=premium)


async def seize_hoards(call: MortalCall, args: SeizeHoardsInput) -> str:
    realm_id = await realm_of(call)
    town = await living_entity(call.session, args.settlement_id)
    if realm_id is None:
        fail(MortalResult.SEIZE_REFUSED, why="you rule no realm")
    if town is None or await realm_of_community(call.session, town.id) != realm_id:
        fail(MortalResult.SEIZE_REFUSED, why="that market is not in your realm")
    seized = 0
    for row in list(
        await call.session.scalars(
            select(SpeculationRow)
            .where(SpeculationRow.market_node_id == town.id, SpeculationRow.status == SpeculationStatus.HOARDING)
            .order_by(SpeculationRow.id)
        )
    ):
        seized += await seize_hoard(call.tick, row, realm_id, by=call.me.id)
    if seized == 0:
        fail(MortalResult.SEIZE_REFUSED, why=f"no one hoards in {town.name}")
    call.target(town.id)
    await call.record("tools.mortal.seize_hoards", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"hoards": seized}, place=town.id)
    return result(MortalResult.HOARDS_SEIZED, name=town.name, hoards=seized)


async def play_market(call: MortalCall, args: PlayMarketInput) -> str:
    profile = await led(call, MERCHANT_HOUSES, MortalResult.PLAY_REFUSED, "you lead no merchant house")
    if profile.home_entity_id is None:
        fail(MortalResult.PLAY_REFUSED, why="your house has no home market")
    await set_play(call.tick, profile.faction_entity_id, profile.home_entity_id, args.commodity, args.play, strength=PLAYED)
    call.target(profile.home_entity_id)
    await call.record(
        "tools.mortal.play_market",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: profile.home_entity_id},
        facts={"play": args.play, "good": args.commodity},
        place=profile.home_entity_id,
    )
    return result(MortalResult.MARKET_PLAYED, play=PLAYS[args.play].label.lower(), good=spoken(args.commodity))


def finance_specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.REPUDIATE_DEBTS, mortal, RepudiateInput, meta, repudiate_debts),
        ToolSpec(MortalToolId.RESCUE_POLITY, mortal, RescueInput, meta, rescue_polity),
        ToolSpec(MortalToolId.RESCHEDULE_LOAN, mortal, RescheduleInput, meta, reschedule_loan),
        ToolSpec(MortalToolId.SELL_LOAN, mortal, SellLoanInput, meta, sell_loan),
        ToolSpec(MortalToolId.INSURE, mortal, InsureInput, meta, insure),
        ToolSpec(MortalToolId.SEIZE_HOARDS, mortal, SeizeHoardsInput, meta, seize_hoards),
        ToolSpec(MortalToolId.PLAY_MARKET, mortal, PlayMarketInput, meta, play_market),
    ]
