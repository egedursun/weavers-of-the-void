from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.law_grammar import LawExceptionView, LawGrammarView, LawTargetFields, LawTheoryView
from aerona.api.views.common import node_refs
from aerona.catalog.law_grammar import LEGACY_GRAMMAR, ROW_TARGETS, working_text
from aerona.core.errors import NotFoundError
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_grammar import LawExceptionRow, LawTheoryRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_grammar import LawCondition, LawTarget
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.divine.law_grammar import gap_of, grammar_of

router = APIRouter(tags=["natural-laws"])
Id = Annotated[int, Path(ge=1)]


def keys_for(target: LawTarget) -> list[str]:
    spec = ROW_TARGETS[target]
    if spec is not None:
        return list(spec.fields)
    return sorted({grammar.key for grammar in LEGACY_GRAMMAR.values() if grammar is not None and grammar.target is target})


@router.get("/natural-laws/{law_id}/grammar", response_model=LawGrammarView)
async def law_grammar(law_id: Id, services: ServicesDep) -> LawGrammarView:
    async with reader(services) as session:
        law = await session.get(EntityRow, law_id)
        if law is None or law.entity_type is not EntityType.NATURAL_LAW:
            raise NotFoundError("No such natural law.")
        row = await session.get(NaturalLawProfileRow, law_id)
        grammar = grammar_of(row) if row is not None else LEGACY_GRAMMAR[law.natural_law or NaturalLaw.NONE]
        exceptions = list(await session.scalars(select(LawExceptionRow).where(LawExceptionRow.law_entity_id == law_id).order_by(LawExceptionRow.id)))
        theories = list(await session.scalars(select(LawTheoryRow).where(LawTheoryRow.law_entity_id == law_id).order_by(LawTheoryRow.id)))
        refs = await node_refs(
            session, [law_id, *(item.node_id for item in exceptions if item.node_id is not None), *(item.holder_node_id for item in theories)]
        )
        condition = row.condition if row is not None else LawCondition.ALWAYS
        written = working_text(grammar, condition) or "It has no working yet."
        truth = (grammar.operator, grammar.value) if grammar is not None else None
        return LawGrammarView(
            law=refs[law_id],
            preset=law.natural_law or NaturalLaw.NONE,
            target=grammar.target if grammar is not None else None,
            operator=grammar.operator if grammar is not None else None,
            key=grammar.key if grammar is not None else None,
            value=grammar.value if grammar is not None else 100,
            condition=condition,
            until_epoch=row.until_epoch if row is not None else None,
            suspended=row.suspended if row is not None else False,
            contested=row.contested if row is not None else False,
            written=written,
            exceptions=[
                LawExceptionView(
                    id=item.id,
                    kind=item.kind,
                    node=refs.get(item.node_id) if item.node_id is not None else None,
                    entity_type=item.entity_type,
                    locked=list(item.locked),
                )
                for item in exceptions
            ],
            theories=[
                LawTheoryView(
                    id=item.id,
                    holder=refs[item.holder_node_id],
                    believed_operator=item.believed_operator,
                    believed_value=item.believed_value,
                    confidence=item.confidence,
                    adapted_epochs=item.adapted_epochs,
                    gap=gap_of(item, truth) if truth is not None else 0,
                    updated_epoch=item.updated_epoch,
                    locked=list(item.locked),
                )
                for item in theories
            ],
            targets=[LawTargetFields(target=target, keys=keys_for(target)) for target in LawTarget],
            locked=list(row.locked) if row is not None else [],
        )
