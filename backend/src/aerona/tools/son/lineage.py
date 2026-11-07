from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.genetics import LOCI
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import Locus
from aerona.engine.genetics.life import express, found_genome
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

GENES = "genes"


class ShapeBloodInput(ToolInput):
    mortal_id: int
    locus: Locus
    allele: str
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def shape_blood(call: SonCall, args: ShapeBloodInput) -> str:
    mortal = require_type(await require_canon(call.session, args.mortal_id), {EntityType.MORTAL}, SonResult.NOT_A_MORTAL, name=str(args.mortal_id))
    await ensure_in_reach(call, mortal)
    spec = LOCI[args.locus]
    if args.allele not in spec.keys:
        fail(SonResult.NO_SUCH_ALLELE, locus=spec.label, alleles=", ".join(spec.keys))
    cost = call.rules.costs.influence
    require_essence(call, cost)
    genome = await found_genome(call.tick, mortal)
    if GENES in (genome.locked or []):
        fail(SonResult.BLOOD_HELD, name=mortal.name)
    before = {key: list(value) for key, value in genome.genes.items()}
    genes = {key: list(value) for key, value in genome.genes.items()}
    genes[args.locus.value] = [args.allele, args.allele]
    genome.genes = genes
    if args.locus is Locus.DIVINE_BLOOD and args.allele == "divine":
        genome.divine_son_id = call.son.id
    express(call.rules, mortal, genes, before)
    call.spend_essence(cost)
    call.target(mortal.id)
    label = spec.allele(args.allele).label
    await call.chronicle(ChronicleKind.WORLD, lines.SHAPE_BLOOD, entity_ids=[mortal.id], son=call.son.name, mortal=mortal.name, trait=label, reason=args.reason)
    return result(SonResult.BLOOD_SHAPED, name=mortal.name, locus=spec.label, trait=label)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.SHAPE_BLOOD,
            AgentKind.SON,
            ShapeBloodInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            shape_blood,
        ),
    ]
