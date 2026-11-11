from collections.abc import Mapping
from typing import Any

from aerona.catalog.storylets import STORYLETS
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.base import Base
from aerona.db.tables.collective import (
    ACCOUNT_FIELDS,
    ARMS_FIELDS,
    BIAS_FIELDS,
    COMMEMORATION_FIELDS,
    COMPONENT_FIELDS,
    DATING_FIELDS,
    DESIGN_FIELDS,
    DIASPORA_FIELDS,
    GENERATION_FIELDS,
    LOST_LAND_FIELDS,
    MOB_FIELDS,
    MOOD_FIELDS,
    MOVEMENT_FIELDS,
    MYTH_FIELDS,
    NORM_FIELDS,
    ROLE_FIELDS,
    SEX_RATIO_FIELDS,
    STORYLET_FIELDS,
    STRIKE_FIELDS,
    TRANSITION_FIELDS,
    WEAR_FIELDS,
    AccountRow,
    AccountStanceRow,
    ArmsRow,
    CascadeRow,
    CommemorationRow,
    ComponentWearRow,
    CrowdMoodRow,
    DatingSystemRow,
    DemographicTransitionRow,
    DesignComponentRow,
    DesignRow,
    DiasporaRow,
    FoundingMythRow,
    GenerationRow,
    LearningBiasRow,
    LearningEventRow,
    LostLandRow,
    MemoryStrikeRow,
    MobRow,
    MovementRow,
    NormChangeRow,
    RoleNormRow,
    SexRatioRow,
    SocialNormRow,
    StoryletRunRow,
)
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.collective import (
    AccountKind,
    AccountMedium,
    AccountStance,
    CollectiveActKind,
    CollectiveTrigger,
    DatingSystemKind,
    DesignComponentKind,
    DesignKind,
    FormativeKind,
    HeraldicDivision,
    HeraldryHolderKind,
    MobEnd,
    MobStatus,
    MobTarget,
    NormBehaviour,
    NormSituation,
    PartitionLine,
    RoleEligibility,
    RoleKind,
    StoryletId,
    StoryletStatus,
    Tincture,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import HullClass
from aerona.domain.enums.mind import EthicalStance, ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.engine.collective.accounts import HistoryTally, debunk, expose, keep_anniversary, record, remember_loss, revise, scholar_in, strike
from aerona.engine.collective.crowds import CrowdTally, begin_movement, end_mob, mood_of, spark
from aerona.engine.collective.designs import apply_design, derive, draw_design, hull_sizes
from aerona.engine.collective.heraldry import sync_emblem
from aerona.engine.collective.storylets import CASTERS, StoryletTally, begin, conditions_hold, resolve
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found

TOWNS = frozenset({EntityType.SETTLEMENT})
CULTURES = frozenset({EntityType.PEOPLE, EntityType.CULT})
HISTORY_HOLDERS = frozenset({EntityType.POLITY, EntityType.PEOPLE, EntityType.CULT, EntityType.MORTAL, EntityType.SETTLEMENT})
MYTH_HOLDERS = frozenset({EntityType.PEOPLE, EntityType.POLITY})
CALENDAR_HOLDERS = frozenset({EntityType.POLITY, EntityType.CULT, EntityType.PEOPLE})
COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})
ARMS_TYPES = {
    HeraldryHolderKind.HOUSE: EntityType.HOUSE,
    HeraldryHolderKind.POLITY: EntityType.POLITY,
    HeraldryHolderKind.ARMY: EntityType.ARMY,
    HeraldryHolderKind.GUILD: EntityType.FACTION,
}


async def of_type(ctx: TickContext, entity_id: int, kinds: frozenset[EntityType], label: str) -> Any:
    row = await entity(ctx, entity_id, label)
    if row.entity_type not in kinds:
        raise ValidationFailedError(f"{row.name} is not {label}.")
    return row


async def saved[Row: Base](ctx: TickContext, row: Row) -> Row:
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_row[Row: Base](
    ctx: TickContext, kind: type[Row], key: object, values: Values, release: list[str], *, fields: tuple[str, ...], label: str
) -> Row:
    row = apply(await found(ctx, kind, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def remove_row(ctx: TickContext, kind: type[Base], key: object, label: str) -> None:
    await ctx.session.delete(await found(ctx, kind, key, label))
    await ctx.session.flush()


async def set_mood(ctx: TickContext, town_id: int, values: Values) -> CrowdMoodRow:
    await of_type(ctx, town_id, TOWNS, "a town")
    if await ctx.session.get(SettlementProfileRow, town_id) is None:
        raise ValidationFailedError("That town keeps no profile.")
    row = apply(await mood_of(ctx, town_id), allowed(values, MOOD_FIELDS, "town mood"), [])
    await ctx.session.flush()
    return row


async def spark_cascade(ctx: TickContext, town_id: int, trigger: CollectiveTrigger) -> CascadeRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    row = await spark(ctx, town, trigger, CrowdTally(), forced=True)
    if row is None:
        raise ConflictError(f"{town.name} cannot be stirred now.")
    return row


async def raise_mob(ctx: TickContext, town_id: int, act: CollectiveActKind, target: MobTarget, *, size: int, anger: int, target_id: int | None) -> MobRow:
    await of_type(ctx, town_id, TOWNS, "a town")
    if target_id is not None:
        await entity(ctx, target_id, "target")
    row = MobRow(settlement_entity_id=town_id, act=act, target=target, status=MobStatus.GATHERING, since_epoch=ctx.epoch, locked=[])
    apply(row, {"size": size, "anger": anger}, [])
    row.target_entity_id = target_id
    return await saved(ctx, row)


async def disperse_mob(ctx: TickContext, mob_id: int, by: MobEnd) -> MobRow:
    mob = await found(ctx, MobRow, mob_id, "mob")
    if mob.status is MobStatus.DISPERSED:
        raise ConflictError("That mob has already dispersed.")
    await end_mob(ctx, mob, await entity(ctx, mob.settlement_entity_id, "town"), by, CrowdTally())
    await ctx.session.flush()
    return mob


async def found_movement(ctx: TickContext, town_id: int, act: CollectiveActKind, trigger: CollectiveTrigger, *, members: int, strength: int) -> MovementRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    row = await begin_movement(ctx, town, act, trigger, members=0, share=0)
    apply(row, {"members": members, "strength": strength}, [])
    await ctx.session.flush()
    return row


async def write_account(
    ctx: TickContext,
    holder_id: int,
    kind: AccountKind,
    *,
    medium: AccountMedium,
    collection_id: int | None,
    subject_id: int | None,
    fidelity: int,
    credence: int,
) -> AccountRow:
    holder = await of_type(ctx, holder_id, HISTORY_HOLDERS, "a realm, people, cult, town or mortal")
    if collection_id is None and subject_id is None:
        raise ValidationFailedError("An account must tell of an event or a figure.")
    if collection_id is not None:
        await found(ctx, CollectionRow, collection_id, "event")
    row = await record(ctx, holder, kind, fidelity=fidelity, stances={}, collection_id=collection_id, subject_id=subject_id, medium=medium, credence=credence)
    if row is None:
        raise ConflictError(f"{holder.name} is held against change.")
    return row


async def set_stance(ctx: TickContext, account_id: int, node_id: int, stance: AccountStance) -> AccountStanceRow:
    await found(ctx, AccountRow, account_id, "account")
    row = await ctx.session.get(AccountStanceRow, (account_id, node_id))
    if row is None:
        row = await saved(ctx, AccountStanceRow(account_id=account_id, node_id=node_id, stance=stance))
    row.stance = stance
    await ctx.session.flush()
    return row


async def revise_account(ctx: TickContext, account_id: int, ousted: list[int], new_ruler: int | None) -> AccountRow:
    row = await revise(ctx, await found(ctx, AccountRow, account_id, "account"), ousted, new_ruler)
    if row is None:
        raise ConflictError("That account cannot be rewritten.")
    return row


async def expose_account(ctx: TickContext, account_id: int) -> AccountRow:
    revision = await found(ctx, AccountRow, account_id, "account")
    original = await ctx.session.get(AccountRow, revision.revised_from_id) if revision.revised_from_id is not None else None
    if original is None:
        raise ConflictError("That account was never rewritten.")
    await expose(ctx, revision, original, await scholar_in(ctx, revision.holder_entity_id))
    return revision


async def strike_figure(ctx: TickContext, by_id: int, node_id: int) -> MemoryStrikeRow:
    await of_type(ctx, by_id, frozenset({EntityType.POLITY, EntityType.CULT}), "a realm or cult")
    row = await strike(ctx, by_id, node_id, HistoryTally())
    if row is None:
        raise ConflictError("That memory is held against change.")
    return row


async def set_myth(ctx: TickContext, holder_id: int, credence: int) -> FoundingMythRow:
    holder = await of_type(ctx, holder_id, MYTH_HOLDERS, "a people or realm")
    row = await ctx.session.get(FoundingMythRow, holder.id)
    if row is None:
        account = await record(ctx, holder, AccountKind.FOUNDING_MYTH, fidelity=0, stances={}, subject_id=holder.id, credence=credence)
        row = await saved(ctx, FoundingMythRow(holder_entity_id=holder.id, account_id=account.id if account else None, since_epoch=ctx.epoch, locked=[]))
    apply(row, {"credence": credence}, [])
    row.debunked_epoch = None
    await ctx.session.flush()
    return row


async def debunk_myth(ctx: TickContext, holder_id: int) -> FoundingMythRow:
    row = await found(ctx, FoundingMythRow, holder_id, "founding myth")
    await debunk(ctx, row, await entity(ctx, holder_id, "holder"), HistoryTally())
    await ctx.session.flush()
    return row


async def set_commemoration(ctx: TickContext, holder_id: int, collection_id: int, *, pride: bool, strength: int) -> CommemorationRow:
    await entity(ctx, holder_id, "holder")
    await found(ctx, CollectionRow, collection_id, "event")
    row = await ctx.session.get(CommemorationRow, (holder_id, collection_id))
    if row is None:
        row = await saved(ctx, CommemorationRow(holder_entity_id=holder_id, collection_id=collection_id, since_epoch=ctx.epoch, locked=[]))
    apply(row, {"pride": pride, "strength": strength}, [])
    await ctx.session.flush()
    return row


async def relive_now(ctx: TickContext, holder_id: int, collection_id: int) -> CommemorationRow:
    row = await found(ctx, CommemorationRow, (holder_id, collection_id), "commemoration")
    await keep_anniversary(ctx, row, await found(ctx, CollectionRow, collection_id, "event"), HistoryTally(), forced=True)
    await ctx.session.flush()
    return row


async def set_lost_land(ctx: TickContext, claimant_id: int, region_id: int, strength: int) -> LostLandRow:
    await of_type(ctx, claimant_id, frozenset({EntityType.POLITY}), "a realm")
    await of_type(ctx, region_id, frozenset({EntityType.REGION}), "a region")
    row = await remember_loss(ctx, claimant_id, region_id)
    if row is None:
        raise ConflictError("That realm is held against change.")
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def open_storylet(ctx: TickContext, storylet: StoryletId, world_id: int) -> StoryletRunRow:
    cast = await CASTERS[storylet](ctx, world_id)
    if cast is None or not await conditions_hold(ctx, STORYLETS[storylet], cast):
        raise ConflictError("Nobody in that world fits the storylet's parts now.")
    return await begin(ctx, storylet, world_id, cast)


async def choose_storylet(ctx: TickContext, run_id: int, choice: int) -> StoryletRunRow:
    run = await found(ctx, StoryletRunRow, run_id, "storylet")
    if run.status is not StoryletStatus.OPEN:
        raise ConflictError("That storylet is no longer open.")
    if await resolve(ctx, run, choice, StoryletTally(), by="player") is None:
        raise ValidationFailedError("There is no such choice.")
    return run


async def set_norm(ctx: TickContext, holder_id: int, situation: NormSituation, behaviour: NormBehaviour, stance: EthicalStance) -> SocialNormRow:
    await of_type(ctx, holder_id, CULTURES, "a people or cult")
    row = await ctx.session.get(SocialNormRow, (holder_id, situation, behaviour))
    before = row.stance if row is not None else EthicalStance.ACCEPTABLE
    if row is None:
        row = await saved(
            ctx, SocialNormRow(holder_entity_id=holder_id, situation=situation, behaviour=behaviour, stance=stance, since_epoch=ctx.epoch, locked=[])
        )
    apply(row, {"stance": stance}, [])
    if before is not stance:
        ctx.session.add(
            NormChangeRow(holder_entity_id=holder_id, situation=situation, behaviour=behaviour, before=before, after=stance, cause="the gods", epoch=ctx.epoch)
        )
    await ctx.session.flush()
    return row


async def set_biases(ctx: TickContext, holder_id: int, values: Values) -> LearningBiasRow:
    await of_type(ctx, holder_id, frozenset({EntityType.PEOPLE}), "a people")
    row = await ctx.session.get(LearningBiasRow, holder_id) or await saved(ctx, LearningBiasRow(holder_entity_id=holder_id, locked=[]))
    apply(row, allowed(values, BIAS_FIELDS, "learning bias"), [])
    await ctx.session.flush()
    return row


async def set_generation(ctx: TickContext, community_id: int, generation_epoch: int, values: Values) -> GenerationRow:
    await of_type(ctx, community_id, TOWNS, "a town")
    row = await ctx.session.get(GenerationRow, (community_id, generation_epoch))
    if row is None:
        row = await saved(
            ctx, GenerationRow(community_entity_id=community_id, generation_epoch=generation_epoch, formative=[], value_shifts={}, alive=0, locked=[])
        )
    apply(row, allowed(values, GENERATION_FIELDS, "generation"), [])
    await ctx.session.flush()
    return row


async def shape_generation(
    ctx: TickContext, community_id: int, generation_epoch: int, formative: list[FormativeKind], shifts: dict[ValueAxis, int]
) -> GenerationRow:
    row = await set_generation(ctx, community_id, generation_epoch, {})
    row.formative = [item.value for item in formative]
    row.value_shifts = {axis.value: amount for axis, amount in shifts.items()}
    row.locked = sorted({*row.locked, "formative", "value_shifts"})
    await ctx.session.flush()
    return row


async def set_diaspora(ctx: TickContext, people_id: int, host_id: int, values: Values) -> DiasporaRow:
    await of_type(ctx, people_id, frozenset({EntityType.PEOPLE}), "a people")
    await of_type(ctx, host_id, TOWNS, "a town")
    row = await ctx.session.get(DiasporaRow, (people_id, host_id))
    if row is None:
        row = await saved(ctx, DiasporaRow(people_entity_id=people_id, host_entity_id=host_id, since_epoch=ctx.epoch, locked=[]))
    apply(row, allowed(values, DIASPORA_FIELDS, "diaspora"), [])
    await ctx.session.flush()
    return row


async def set_community_row[Row: Base](ctx: TickContext, kind: type[Row], community_id: int, values: Values, *, fields: tuple[str, ...], label: str) -> Row:
    await of_type(ctx, community_id, COMMUNITIES, "a town or people")
    row = await ctx.session.get(kind, community_id)
    if row is None:
        row = await saved(ctx, kind(community_entity_id=community_id, locked=[]))
    apply(row, allowed(values, fields, label), [])
    await ctx.session.flush()
    return row


async def set_transition(ctx: TickContext, community_id: int, values: Values) -> DemographicTransitionRow:
    return await set_community_row(ctx, DemographicTransitionRow, community_id, values, fields=TRANSITION_FIELDS, label="demographic transition")


async def set_sex_ratio(ctx: TickContext, community_id: int, values: Values) -> SexRatioRow:
    return await set_community_row(ctx, SexRatioRow, community_id, values, fields=SEX_RATIO_FIELDS, label="sex ratio")


async def set_role(
    ctx: TickContext, holder_id: int, role: RoleKind, *, eligibility: RoleEligibility, min_age: int, classes: list[SocialClass], stance: EthicalStance
) -> RoleNormRow:
    await of_type(ctx, holder_id, frozenset({EntityType.PEOPLE}), "a people")
    row = await ctx.session.get(RoleNormRow, (holder_id, role))
    if row is None:
        row = await saved(ctx, RoleNormRow(holder_entity_id=holder_id, role=role, since_epoch=ctx.epoch, locked=[]))
    apply(row, {"eligibility": eligibility, "min_age": min_age, "stance": stance}, [])
    row.classes = [item.value for item in classes]
    await ctx.session.flush()
    return row


async def set_dating(ctx: TickContext, holder_id: int, kind: DatingSystemKind, *, anchor_year: int, label_id: int | None, cycle_years: int) -> DatingSystemRow:
    await of_type(ctx, holder_id, CALENDAR_HOLDERS, "a realm, cult or people")
    if label_id is not None:
        await entity(ctx, label_id, "era name")
    row = await ctx.session.get(DatingSystemRow, holder_id)
    if row is None:
        row = await saved(ctx, DatingSystemRow(holder_entity_id=holder_id, kind=kind, since_epoch=ctx.epoch, locked=[]))
    apply(
        row,
        {"kind": kind, "anchor_year": anchor_year, "label_node_id": label_id or holder_id, "anchor_node_id": label_id or holder_id, "cycle_years": cycle_years},
        [],
    )
    row.reformed_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def set_arms(ctx: TickContext, holder_id: int, holder_kind: HeraldryHolderKind, values: Mapping[str, Any]) -> ArmsRow:
    holder = await entity(ctx, holder_id, "holder")
    wanted = ARMS_TYPES.get(holder_kind)
    if wanted is not None and holder.entity_type is not wanted:
        raise ValidationFailedError(f"{holder.name} is not {an(holder_kind.value)}.")
    row = await ctx.session.get(ArmsRow, holder_id)
    if row is None:
        row = await saved(ctx, ArmsRow(holder_entity_id=holder_id, holder_kind=holder_kind, field=values["field"], since_epoch=ctx.epoch, locked=[]))
    apply(row, {key: value for key, value in values.items() if key in ARMS_FIELDS}, [])
    row.holder_kind = holder_kind
    await sync_emblem(ctx, row)
    await ctx.session.flush()
    return row


async def edit_arms(ctx: TickContext, holder_id: int, values: Values, release: list[str]) -> ArmsRow:
    row = await edit_row(ctx, ArmsRow, holder_id, values, release, fields=ARMS_FIELDS, label="arms")
    await sync_emblem(ctx, row)
    return row


async def quarter_arms(ctx: TickContext, holder_id: int, other_id: int) -> ArmsRow:
    row = await found(ctx, ArmsRow, holder_id, "arms")
    other = await found(ctx, ArmsRow, other_id, "arms")
    apply(row, {"division": HeraldicDivision.QUARTERLY, "second": other.field}, [])
    row.quartered_entity_id = other.holder_entity_id
    await sync_emblem(ctx, row)
    await ctx.session.flush()
    return row


async def difference_arms(ctx: TickContext, holder_id: int, parent_id: int, border: Tincture, line: PartitionLine) -> ArmsRow:
    parent = await found(ctx, ArmsRow, parent_id, "arms")
    row = await ctx.session.get(ArmsRow, holder_id)
    if row is None:
        row = await saved(ctx, ArmsRow(holder_entity_id=holder_id, holder_kind=parent.holder_kind, field=parent.field, since_epoch=ctx.epoch, locked=[]))
    copied = {name: getattr(parent, name) for name in ARMS_FIELDS if name != "motto"}
    apply(row, copied | {"division": HeraldicDivision.BORDURE, "line": line, "second": border}, [])
    row.parent_entity_id = parent.holder_entity_id
    await sync_emblem(ctx, row)
    await ctx.session.flush()
    return row


async def new_design(ctx: TickContext, owner_id: int, kind: DesignKind, *, hull: HullClass | None, name: str | None, quality: int) -> DesignRow:
    owner = await entity(ctx, owner_id, "owner")
    if kind is not DesignKind.SIEGE_ENGINE and hull is None:
        raise ValidationFailedError("A vessel design needs a hull.")
    sizes = hull_sizes(hull) if hull is not None and kind is not DesignKind.SIEGE_ENGINE else None
    return await draw_design(ctx, owner, kind, hull=hull, sizes=sizes, quality=quality, name=name)


async def edit_design(ctx: TickContext, design_id: int, values: Values, release: list[str]) -> DesignRow:
    return await edit_row(ctx, DesignRow, design_id, values, release, fields=DESIGN_FIELDS, label="design")


async def refit_design(ctx: TickContext, design_id: int) -> DesignRow:
    design = await found(ctx, DesignRow, design_id, "design")
    owner = await entity(ctx, design.owner_entity_id, "owner")
    newer = await draw_design(ctx, owner, design.kind, hull=design.hull, parent=design, designer_id=design.designer_entity_id)
    design.obsolete = True
    await ctx.session.flush()
    return newer


async def set_component(ctx: TickContext, design_id: int, component: DesignComponentKind, values: Values) -> DesignComponentRow:
    design = await found(ctx, DesignRow, design_id, "design")
    row = await ctx.session.get(DesignComponentRow, (design_id, component))
    if row is None:
        row = await saved(ctx, DesignComponentRow(design_id=design_id, component=component, size=0, quality=50))
    apply(row, allowed(values, COMPONENT_FIELDS, "component"), [])
    await derive(ctx.session, ctx.rules, design)
    return row


async def delete_component(ctx: TickContext, design_id: int, component: DesignComponentKind) -> None:
    row = await found(ctx, DesignComponentRow, (design_id, component), "component")
    await ctx.session.delete(row)
    await ctx.session.flush()
    await derive(ctx.session, ctx.rules, await found(ctx, DesignRow, design_id, "design"))


async def fit_vessel(ctx: TickContext, vessel_id: int, design_id: int) -> VesselProfileRow:
    vessel = await found(ctx, VesselProfileRow, vessel_id, "vessel")
    apply_design(vessel, await found(ctx, DesignRow, design_id, "design"))
    vessel.locked = [*vessel.locked, "design_id"] if "design_id" not in vessel.locked else vessel.locked
    await ctx.session.flush()
    return vessel


async def set_wear(ctx: TickContext, vessel_id: int, component: DesignComponentKind, wear: int) -> ComponentWearRow:
    await found(ctx, VesselProfileRow, vessel_id, "vessel")
    row = await ctx.session.get(ComponentWearRow, (vessel_id, component))
    if row is None:
        row = await saved(ctx, ComponentWearRow(vessel_entity_id=vessel_id, component=component, wear=0, locked=[]))
    apply(row, {"wear": wear}, [])
    await ctx.session.flush()
    return row


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "crowd_mood": (CrowdMoodRow, MOOD_FIELDS, "town mood"),
    "mob": (MobRow, MOB_FIELDS, "mob"),
    "movement": (MovementRow, MOVEMENT_FIELDS, "movement"),
    "account": (AccountRow, ACCOUNT_FIELDS, "account"),
    "memory_strike": (MemoryStrikeRow, STRIKE_FIELDS, "struck memory"),
    "founding_myth": (FoundingMythRow, MYTH_FIELDS, "founding myth"),
    "commemoration": (CommemorationRow, COMMEMORATION_FIELDS, "commemoration"),
    "lost_land": (LostLandRow, LOST_LAND_FIELDS, "lost land"),
    "storylet": (StoryletRunRow, STORYLET_FIELDS, "storylet"),
    "social_norm": (SocialNormRow, NORM_FIELDS, "norm"),
    "learning_bias": (LearningBiasRow, BIAS_FIELDS, "learning bias"),
    "generation": (GenerationRow, GENERATION_FIELDS, "generation"),
    "diaspora": (DiasporaRow, DIASPORA_FIELDS, "diaspora"),
    "transition": (DemographicTransitionRow, TRANSITION_FIELDS, "demographic transition"),
    "sex_ratio": (SexRatioRow, SEX_RATIO_FIELDS, "sex ratio"),
    "role_norm": (RoleNormRow, ROLE_FIELDS, "role norm"),
    "dating_system": (DatingSystemRow, DATING_FIELDS, "dating system"),
    "component_wear": (ComponentWearRow, WEAR_FIELDS, "wear"),
}
REMOVABLE: dict[str, tuple[type[Base], str]] = {
    "cascade": (CascadeRow, "cascade"),
    "account_stance": (AccountStanceRow, "stance"),
    "norm_change": (NormChangeRow, "norm change"),
    "learning_event": (LearningEventRow, "learning event"),
    "arms": (ArmsRow, "arms"),
    "design": (DesignRow, "design"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    return await edit_row(ctx, table, key, values, release, fields=fields, label=label)


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, label = REMOVABLE[kind] if kind in REMOVABLE else (EDITABLE[kind][0], EDITABLE[kind][2])
    await remove_row(ctx, table, key, label)
