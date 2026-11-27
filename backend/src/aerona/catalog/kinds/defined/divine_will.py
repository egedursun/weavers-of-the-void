from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.divine_will import ChunkSource

CHUNK_SOURCE = total(
    ChunkSource,
    {
        ChunkSource.ENTITY: Defined(
            "Entity",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.NODE_SOURCES",
                "services.divine_will.follow.entity_change",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.entity_passages",
            ),
        ),
        ChunkSource.TYPED_SECTION: Defined(
            "Typed section",
            checked_by=(
                "services.divine_will.follow.removed_refs",
                "services.divine_will.passages.build_units",
                "services.divine_will.passages.unit_passages",
                "services.divine_will.passages.world_side",
            ),
            used_by=("services.divine_will.follow.take_change", "services.divine_will.passages.build_units", "services.divine_will.passages.typed_passages"),
        ),
        ChunkSource.CHRONICLE: Defined(
            "Chronicle",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.affected_since",
                "services.divine_will.follow.take_edits",
                "services.divine_will.follow.take_ledger",
                "services.divine_will.index.LoreIndex._follow_now",
                "services.divine_will.passages.chronicle_passages",
            ),
        ),
        ChunkSource.INCIDENT: Defined(
            "Incident",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=("services.divine_will.follow.resolve", "services.divine_will.passages.incident_passages"),
        ),
        ChunkSource.SON: Defined(
            "Son",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.NODE_SOURCES",
                "services.divine_will.follow.OWN_SOURCES",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.son_passages",
            ),
        ),
        ChunkSource.FOREIGN_GOD: Defined(
            "Foreign god",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.NODE_SOURCES",
                "services.divine_will.follow.OWN_SOURCES",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.foreign_god_passages",
            ),
        ),
        ChunkSource.WORLD: Defined(
            "World",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.NODE_SOURCES",
                "services.divine_will.follow.OWN_SOURCES",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.world_body_passages",
            ),
        ),
        ChunkSource.STAR: Defined(
            "Star",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.NODE_SOURCES",
                "services.divine_will.follow.OWN_SOURCES",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.star_passages",
            ),
        ),
        ChunkSource.CREATOR: Defined(
            "Creator",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.NODE_SOURCES",
                "services.divine_will.follow.OWN_SOURCES",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.creator_passages",
            ),
        ),
        ChunkSource.WORD: Defined(
            "Word",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=("services.divine_will.follow.OWN_SOURCES", "services.divine_will.index.MEANING_SOURCES", "services.divine_will.passages.word_passages"),
        ),
        ChunkSource.EPOCH: Defined(
            "Epoch",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.epoch_change",
                "services.divine_will.follow.narrative_change",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.epoch_passages",
            ),
        ),
        ChunkSource.NOTE: Defined(
            "Note",
            checked_by=("services.divine_will.passages.note_passages", "services.divine_will.passages.world_side"),
            used_by=(
                "services.divine_will.follow.entity_change",
                "services.divine_will.follow.map_note_change",
                "services.divine_will.follow.take_change",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.passages.entity_passages",
                "services.divine_will.passages.map_note_passages",
            ),
        ),
        ChunkSource.MESSAGE: Defined(
            "Message",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=("services.divine_will.follow.OWN_SOURCES", "services.divine_will.passages.message_passages"),
        ),
        ChunkSource.COUNCIL: Defined(
            "Council",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=("services.divine_will.follow.OWN_SOURCES", "services.divine_will.index.MEANING_SOURCES", "services.divine_will.passages.council_passages"),
        ),
        ChunkSource.ARTIFACT: Defined(
            "Artifact",
            checked_by=("services.divine_will.passages.world_side",),
            used_by=(
                "services.divine_will.follow.OWN_SOURCES",
                "services.divine_will.follow.artifact_part_change",
                "services.divine_will.index.LoreIndex._allowed",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.library.ARTIFACT_SOURCES",
                "services.divine_will.passages.artifact_passages",
                "services.divine_will.store.WordStore._filters",
            ),
        ),
        ChunkSource.ATTACHMENT: Defined(
            "Attachment",
            checked_by=("services.divine_will.index.LoreIndex.refresh_attachments", "services.divine_will.passages.WORLD_SOURCES"),
            used_by=(
                "services.divine_will.index.LoreIndex._allowed",
                "services.divine_will.index.LoreIndex._attachment_passages",
                "services.divine_will.index.MEANING_SOURCES",
                "services.divine_will.store.WordStore._filters",
                "tools.divine_will.attachments.attachment_search",
            ),
        ),
    },
)
