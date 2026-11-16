from pydantic import Field

from aerona.catalog.genetics import GIFT_STANCE_LABELS, LOCI
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GENOME_FIELDS, AllelePoolRow, GenomeRow, HouseResemblanceRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import GiftStance, Locus
from aerona.domain.enums.mortal import Ability
from aerona.engine.body.customs import people_of
from aerona.engine.genetics.genome import drawn_genes
from aerona.engine.genetics.life import found_genome
from aerona.engine.genetics.pools import normalised, seed_pool
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
GENES = "genes"
FREQUENCIES = "frequencies"


POTENTIAL = "potential"


class GenomeTarget(Command):
    mortal_id: int


class SetGene(Command):
    mortal_id: int
    locus: Locus
    first: str
    second: str
    hold: bool = True


class EditGenome(Command):
    mortal_id: int
    beauty: int | None = Field(default=None, ge=0, le=SPAN)
    inbreeding: int | None = Field(default=None, ge=0, le=SPAN)
    recognisability: int | None = Field(default=None, ge=0, le=SPAN)
    potential: dict[Ability, int] | None = None
    divine_son_id: int | None = None
    clear_divine: bool = False
    hold: bool = True


class PoolTarget(Command):
    people_id: int


class SetFrequency(Command):
    people_id: int
    locus: Locus
    allele: str
    frequency: int = Field(ge=0, le=SPAN)
    hold: bool = True


class SetGiftStance(Command):
    people_id: int
    stance: GiftStance
    hold: bool = True


class EditGiftShare(Command):
    people_id: int
    gifted_share: int | None = Field(default=None, ge=0, le=SPAN)
    cohort: str | None = None
    cohort_share: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class SetResemblance(Command):
    house_id: int
    locus: Locus
    allele: str
    share: int = Field(default=60, ge=0, le=SPAN)
    hold: bool = True


class ResemblanceTarget(Command):
    house_id: int


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


def allele_of(locus: Locus, key: str) -> str:
    spec = LOCI[locus]
    if key not in spec.keys:
        raise ValidationFailedError(f"{spec.label} has no allele '{key}'; choose one of {', '.join(spec.keys)}.")
    return key


async def mortal(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal carries a genome.")
    return found


async def people(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.PEOPLE:
        raise ValidationFailedError("Only a people keeps an allele pool.")
    return found


async def genome(scope: PlayerScope, node_id: int) -> GenomeRow:
    holder = await mortal(scope, node_id)
    found = await scope.session.get(GenomeRow, holder.id)
    if found is None:
        found = await found_genome(await manual_context(scope.session, "genome"), holder)
    return found


async def pool(scope: PlayerScope, node_id: int) -> AllelePoolRow:
    folk = await people(scope, node_id)
    found = await scope.session.get(AllelePoolRow, folk.id)
    if found is None:
        found = await seed_pool(await manual_context(scope.session, "pool"), folk)
    return found


@player_action("genome:found", ActionKind.EDIT_RECORD)
async def found(scope: PlayerScope, command: GenomeTarget) -> Effect:
    holder = await mortal(scope, command.mortal_id)
    row = await genome(scope, holder.id)
    return Effect(f"The genome of {holder.name} is written down, locus by locus.", target_node_id=holder.id, values={"loci": len(row.genes)})


@player_action("genome:gene", ActionKind.EDIT_RECORD)
async def set_gene(scope: PlayerScope, command: SetGene) -> Effect:
    row = await genome(scope, command.mortal_id)
    genes = {key: list(value) for key, value in row.genes.items()}
    genes[command.locus.value] = [allele_of(command.locus, command.first), allele_of(command.locus, command.second)]
    row.genes = genes
    row.locked = held(row.locked, [GENES], command.hold)
    await scope.session.flush()
    spec = LOCI[command.locus]
    return Effect(
        f"{spec.label}: {spec.allele(command.first).label} and {spec.allele(command.second).label} now run in this genome.", target_node_id=command.mortal_id
    )


@player_action("genome:edit", ActionKind.EDIT_RECORD)
async def edit(scope: PlayerScope, command: EditGenome) -> Effect:
    row = await genome(scope, command.mortal_id)
    touched = [name for name in GENOME_FIELDS if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if command.potential:
        if any(not 0 <= value <= SPAN for value in command.potential.values()):
            raise ValidationFailedError(f"Potential runs from 0 to {SPAN}.")
        row.potential = {**row.potential, **{ability.value: value for ability, value in command.potential.items()}}
        touched.append(POTENTIAL)
    if command.divine_son_id is not None:
        if await scope.session.get(SonRow, command.divine_son_id) is None:
            raise ValidationFailedError("No such son.")
        row.divine_son_id = command.divine_son_id
    elif command.clear_divine:
        row.divine_son_id = None
    if not touched and command.divine_son_id is None and not command.clear_divine:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"Beauty {row.beauty}, inbreeding {row.inbreeding}, recognisability {row.recognisability}.", target_node_id=command.mortal_id)


@player_action("genome:redraw", ActionKind.EDIT_RECORD)
async def redraw(scope: PlayerScope, command: GenomeTarget) -> Effect:
    holder = await mortal(scope, command.mortal_id)
    row = await genome(scope, holder.id)
    folk = await people_of(scope.session, holder)
    source = await scope.session.get(AllelePoolRow, folk.id) if folk is not None else None
    context = await manual_context(scope.session, "genome.redraw")
    row.genes = drawn_genes(context.rng(f"genome.redraw.{holder.id}.{await scope.epoch()}"), source.frequencies if source is not None else None)
    row.locked = held(row.locked, [GENES], True)
    await scope.session.flush()
    return Effect(f"The genome of {holder.name} was drawn anew from the pool of its people.", target_node_id=holder.id)


@player_action("genome:remove", ActionKind.EDIT_RECORD)
async def remove(scope: PlayerScope, command: GenomeTarget) -> Effect:
    row = await scope.session.get(GenomeRow, command.mortal_id)
    if row is None:
        raise NotFoundError("That mortal carries no written genome.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The written genome was struck; it is drawn again next epoch.", target_node_id=command.mortal_id)


@player_action("allele_pool:found", ActionKind.EDIT_RECORD)
async def found_pool(scope: PlayerScope, command: PoolTarget) -> Effect:
    row = await pool(scope, command.people_id)
    return Effect("The allele pool of the people is written down.", target_node_id=command.people_id, values={"loci": len(row.frequencies)})


@player_action("allele_pool:frequency", ActionKind.EDIT_RECORD)
async def set_frequency(scope: PlayerScope, command: SetFrequency) -> Effect:
    row = await pool(scope, command.people_id)
    key = allele_of(command.locus, command.allele)
    others = {name: float((row.frequencies.get(command.locus.value) or {}).get(name, 0)) for name in LOCI[command.locus].keys if name != key}
    rest = float(SPAN - command.frequency)
    total = sum(others.values())
    shared = {name: (value * rest / total if total else rest / max(1, len(others))) for name, value in others.items()}
    shared[key] = float(command.frequency)
    frequencies = dict(row.frequencies)
    frequencies[command.locus.value] = normalised(shared)
    row.frequencies = frequencies
    row.locked = held(row.locked, [FREQUENCIES], command.hold)
    await scope.session.flush()
    return Effect(f"{LOCI[command.locus].allele(key).label} now runs in {command.frequency}% of the people's pool.", target_node_id=command.people_id)


@player_action("allele_pool:stance", ActionKind.EDIT_RECORD)
async def set_stance(scope: PlayerScope, command: SetGiftStance) -> Effect:
    row = await pool(scope, command.people_id)
    row.gift_stance = command.stance
    row.locked = held(row.locked, ["gift_stance"], command.hold)
    await scope.session.flush()
    return Effect(f"The people now hold the magical gift {GIFT_STANCE_LABELS[command.stance].lower()}.", target_node_id=command.people_id)


@player_action("allele_pool:share", ActionKind.EDIT_RECORD)
async def edit_share(scope: PlayerScope, command: EditGiftShare) -> Effect:
    row = await pool(scope, command.people_id)
    touched: list[str] = []
    if command.gifted_share is not None:
        row.gifted_share = command.gifted_share
        touched.append("gifted_share")
    if command.cohort is not None and command.cohort_share is not None:
        row.cohort_shares = {**row.cohort_shares, command.cohort: command.cohort_share}
        touched.append("cohort_shares")
    if not touched:
        raise ValidationFailedError("Set the gifted share or a cohort's share.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{row.gifted_share}% of the people are born gifted.", target_node_id=command.people_id)


@player_action("allele_pool:remove", ActionKind.EDIT_RECORD)
async def remove_pool(scope: PlayerScope, command: PoolTarget) -> Effect:
    row = await scope.session.get(AllelePoolRow, command.people_id)
    if row is None:
        raise NotFoundError("That people keeps no written allele pool.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The allele pool was struck; it is drawn again next epoch.", target_node_id=command.people_id)


@player_action("resemblance:set", ActionKind.EDIT_RECORD)
async def set_resemblance(scope: PlayerScope, command: SetResemblance) -> Effect:
    house = await scope.session.get(EntityRow, command.house_id)
    if house is None or house.entity_type is not EntityType.HOUSE or house.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living house carries a family likeness.")
    spec = LOCI[command.locus]
    if spec.group.value != "looks":
        raise ValidationFailedError("A family likeness is a matter of looks.")
    key = allele_of(command.locus, command.allele)
    row = await scope.session.get(HouseResemblanceRow, house.id)
    if row is None:
        row = HouseResemblanceRow(house_node_id=house.id, locus=command.locus, allele=key, share=command.share, since_epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    row.locus, row.allele, row.share = command.locus, key, command.share
    row.locked = held(row.locked, ["allele", "share"], command.hold)
    await scope.session.flush()
    return Effect(f"{house.name} is known by {spec.allele(key).label}.", target_node_id=house.id)


@player_action("resemblance:remove", ActionKind.EDIT_RECORD)
async def remove_resemblance(scope: PlayerScope, command: ResemblanceTarget) -> Effect:
    row = await scope.session.get(HouseResemblanceRow, command.house_id)
    if row is None:
        raise NotFoundError("That house carries no family likeness.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The family likeness was struck.", target_node_id=command.house_id)
