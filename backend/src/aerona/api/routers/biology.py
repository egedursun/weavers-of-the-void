from typing import Annotated

from fastapi import APIRouter, Path

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.biology import BiologyBodyView, BiologyEffectsView, BiologyLeaningView, BiologyNodeView
from aerona.api.views.common import node_refs
from aerona.catalog.biology import BIOLOGY_VARIANTS
from aerona.core.errors import NotFoundError
from aerona.db.tables.biology import BIOLOGY_EFFECTS, BiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.folkways import DecisionBias
from aerona.engine.body.variants import body_variants, derived_effects, holder_of, variants_of

router = APIRouter(tags=["biology"])
NodeId = Annotated[int, Path(ge=1)]
NO_BODY = "It belongs to no people or species: gods, worlds, stars and things without a living kind carry no biology."


def effects_of(values: dict[str, object]) -> BiologyEffectsView:
    return BiologyEffectsView.model_validate({key: values[key] for key in BIOLOGY_EFFECTS})


def leanings(variants: tuple[BiologyVariant, ...]) -> list[BiologyLeaningView]:
    found = []
    for bias in DecisionBias:
        shift = sum(BIOLOGY_VARIANTS[variant].shifts.get(bias, 0) for variant in variants)
        damped = any(bias in BIOLOGY_VARIANTS[variant].damped for variant in variants)
        if shift or damped:
            found.append(BiologyLeaningView(bias=bias, shift=shift, damped=damped))
    return found


def body_of(variants: tuple[BiologyVariant, ...]) -> BiologyBodyView:
    specs = [BIOLOGY_VARIANTS[variant] for variant in variants]
    return BiologyBodyView(
        bleeds=all(spec.bleeds for spec in specs),
        heals=all(spec.heals for spec in specs),
        infects=all(spec.infects for spec in specs),
        material=all(spec.material for spec in specs),
        tissue=next((spec.tissue for spec in specs if spec.tissue is not None), None),
    )


@router.get("/biology/of/{node_id}", response_model=BiologyNodeView)
async def node_biology(services: ServicesDep, node_id: NodeId) -> BiologyNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        holder = await holder_of(session, await session.get(EntityRow, node_id))
        if holder is None:
            return BiologyNodeView(
                node=own[node_id],
                holder=None,
                variants=[],
                body_variants=[],
                effects=None,
                derived=None,
                leanings=[],
                body=None,
                partner=None,
                seeded=False,
                updated_epoch=None,
                locked=[],
                absent_reason=NO_BODY,
            )
        row = await session.get(BiologyRow, holder.id)
        partner_id = row.partner_species_id if row is not None else None
        refs = await node_refs(session, [holder.id, *([partner_id] if partner_id is not None else [])])
        shown = await body_variants(session, holder.id)
        variants = variants_of(row.variants) if row is not None else tuple(shown)
        derived = derived_effects(variants)
        return BiologyNodeView(
            node=own[node_id],
            holder=refs.get(holder.id),
            variants=list(variants),
            body_variants=shown,
            effects=effects_of({key: getattr(row, key) for key in BIOLOGY_EFFECTS} if row is not None else derived),
            derived=effects_of(derived),
            leanings=leanings(variants),
            body=body_of(variants),
            partner=refs.get(partner_id) if partner_id is not None else None,
            seeded=row is not None,
            updated_epoch=row.updated_epoch if row is not None else None,
            locked=list(row.locked) if row is not None else [],
            absent_reason=None,
        )
