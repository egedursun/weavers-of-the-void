import json
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH
from aerona.core.action_text import readable_summary
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.node import ActorKind
from aerona.migration.legacy.source import LegacySource
from aerona.migration.legacy.timestamps import legacy_time

INDENT = 2
ELLIPSIS = "…"

TOOLS: MappingProxyType[str, tuple[str, ActionKind]] = MappingProxyType(
    {
        "ag_onar": ("stitch_leak", ActionKind.CLEANSE_LEAK),
        "ahit_et": ("swear_covenant", ActionKind.COVENANT),
        "armagan_ver": ("give_gift", ActionKind.INFLUENCE),
        "babaya_dua": ("pray_to_father", ActionKind.CHAT),
        "bag_kur": ("make_bond", ActionKind.INFLUENCE),
        "bilgi_gelistir": ("develop_knowledge", ActionKind.ADVANCE_KNOWLEDGE),
        "bilgi_ver": ("teach_knowledge", ActionKind.TEACH_KNOWLEDGE),
        "bolge_yarat": ("create_region", ActionKind.CREATE_ENTITY),
        "capa_sec": ("choose_anchor", ActionKind.CHANGE_ANCHOR),
        "dil_kur": ("found_language", ActionKind.CREATE_ENTITY),
        "dil_yarat": ("create_language", ActionKind.CREATE_ENTITY),
        "diplomasi": ("diplomacy", ActionKind.INFLUENCE),
        "dua": ("pray_to_creator", ActionKind.CHAT),
        "dunyaya_yonel": ("move_to_world", ActionKind.INFLUENCE),
        "efsane_anlat": ("tell_legend", ActionKind.CREATE_ENTITY),
        "eser_yarat": ("create_artwork", ActionKind.CREATE_ENTITY),
        "esya_dov": ("forge_item", ActionKind.CREATE_ENTITY),
        "gelenek_kur": ("found_tradition", ActionKind.CREATE_ENTITY),
        "halk_yarat": ("create_people", ActionKind.CREATE_ENTITY),
        "harita:konum": ("entity:move", ActionKind.EDIT_RECORD),
        "hile:oz": ("cheat:essence", ActionKind.BLESS_ESSENCE),
        "iklim": ("climate", ActionKind.EDIT_RECORD),
        "insa_et": ("build_structure", ActionKind.CREATE_ENTITY),
        "itibar": ("reputation", ActionKind.EDIT_RECORD),
        "kalinti_ara": ("search_ruins", ActionKind.INFLUENCE),
        "kanun_koy": ("decree_law", ActionKind.CREATE_ENTITY),
        "kaynak_kesfet": ("discover_resource", ActionKind.CREATE_ENTITY),
        "kaynak_sag": ("harvest_resource", ActionKind.INFLUENCE),
        "kaynak_yarat": ("create_resource", ActionKind.CREATE_ENTITY),
        "kehanet_et": ("prophesy", ActionKind.CREATE_ENTITY),
        "kehanet_soyle": ("utter_prophecy", ActionKind.CREATE_ENTITY),
        "kelime_tureti": ("coin_words", ActionKind.EDIT_RECORD),
        "kultur_yarat": ("create_culture", ActionKind.CREATE_ENTITY),
        "kutsa": ("bless", ActionKind.BLESS_STAT),
        "meydan_oku": ("challenge", ActionKind.INFLUENCE),
        "mucize": ("miracle", ActionKind.MIRACLE),
        "mudahale:bilgi": ("intervene:knowledge", ActionKind.TEACH_KNOWLEDGE),
        "mudahale:mucize": ("intervene:miracle", ActionKind.MIRACLE),
        "ogren": ("learn_knowledge", ActionKind.TEACH_KNOWLEDGE),
        "olumlu_yarat": ("create_mortal", ActionKind.CREATE_ENTITY),
        "ordu_topla": ("raise_army", ActionKind.CREATE_ENTITY),
        "oz_em:ogul": ("drain:son", ActionKind.DRAIN_ESSENCE),
        "plan_yaz": ("write_plan", ActionKind.EDIT_RECORD),
        "rota:kur": ("route:open", ActionKind.REVEAL_ROUTE),
        "ruh_cagir": ("summon_spirit", ActionKind.CREATE_ENTITY),
        "ruya": ("send_dream", ActionKind.DREAM),
        "ruya_gonder": ("send_dream", ActionKind.DREAM),
        "sahiplen": ("claim_resource", ActionKind.INFLUENCE),
        "secilmis_ilan_et": ("declare_chosen", ActionKind.DECLARE_CHOSEN),
        "tapin": ("worship", ActionKind.INFLUENCE),
        "tarikat_kur": ("found_cult", ActionKind.CREATE_ENTITY),
        "ticaret_kur": ("establish_trade", ActionKind.INFLUENCE),
        "toprak_kesfet": ("explore_land", ActionKind.INFLUENCE),
        "tur_yarat": ("create_species", ActionKind.CREATE_ENTITY),
        "uret": ("produce_item", ActionKind.CREATE_ENTITY),
        "vahiy": ("revelation", ActionKind.REVELATION),
        "varlik:duzenle": ("record:edit", ActionKind.EDIT_RECORD),
        "varlik:hami": ("entity:patron", ActionKind.EDIT_RECORD),
        "varlik:stat": ("entity:stat", ActionKind.EDIT_RECORD),
        "yapit_insa": ("build_structure", ActionKind.CREATE_ENTITY),
        "yaraticiya_dua": ("pray_to_creator", ActionKind.CHAT),
        "yer_yarat": ("create_place", ActionKind.CREATE_ENTITY),
        "yerlesim_kur": ("found_settlement", ActionKind.CREATE_ENTITY),
        "yildiz": ("hang_star", ActionKind.HANG_STAR),
        "yukselis": ("son:ascend", ActionKind.ASCEND),
    }
)
ACTOR_KINDS = frozenset(kind.value for kind in ActorKind)


def ledger_history(source: LegacySource) -> list[dict[str, Any]]:
    vocabulary = source.vocabulary
    entries: list[dict[str, Any]] = []
    for row in source.iterate("ledger", ("id",)):
        stamp = legacy_time(row.raw("created_at"))
        entries.append(
            {
                "legacy_id": row.integer("id"),
                "epoch": row.integer("epoch"),
                "actor_kind": vocabulary.decode("actor_kind", row.text("actor_kind")),
                "actor_name": row.text("actor_name"),
                "tool": row.text("tool"),
                "summary": row.text("summary"),
                "created_at": stamp.isoformat() if stamp is not None else None,
                "undone": row.flag("undone"),
            }
        )
    return entries


def write_ledger_history(source: LegacySource, path: Path) -> int:
    entries = ledger_history(source)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=INDENT), encoding="utf-8")
    return len(entries)


async def _actor_ids(session: AsyncSession) -> dict[tuple[ActorKind, str], int]:
    found: dict[tuple[ActorKind, str], int] = {}
    for son_id, name in await session.execute(select(SonRow.id, SonRow.name)):
        found[(ActorKind.SON, name)] = son_id
    for creator_id, name in await session.execute(select(CreatorRow.id, CreatorRow.name)):
        found[(ActorKind.CREATOR, name)] = creator_id
    for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).order_by(EntityRow.id)):
        found.setdefault((ActorKind.MORTAL, name), entity_id)
    return found


def _summary(text: str | None) -> str | None:
    if not text:
        return None
    clean = readable_summary(" ".join(text.split()))
    if not clean:
        return None
    return clean if len(clean) <= LEDGER_SUMMARY_MAX_LENGTH else clean[: LEDGER_SUMMARY_MAX_LENGTH - 1] + ELLIPSIS


async def import_ledger_history(session: AsyncSession, entries: list[dict[str, Any]]) -> int:
    if await session.scalar(select(func.count()).select_from(LedgerEntryRow)):
        return 0
    actors = await _actor_ids(session)
    rows: list[LedgerEntryRow] = []
    for entry in sorted(entries, key=lambda item: item["legacy_id"]):
        kind = ActorKind(entry["actor_kind"]) if entry.get("actor_kind") in ACTOR_KINDS else ActorKind.SYSTEM
        tool, action = TOOLS.get(entry["tool"], (entry["tool"], ActionKind.INFLUENCE))
        name = entry.get("actor_name") or kind.value
        row = LedgerEntryRow(
            epoch=entry["epoch"],
            actor_kind=kind,
            actor_node_id=actors.get((kind, name)),
            actor_name=name,
            tool=tool,
            action_kind=action,
            input_summary=_summary(entry.get("summary")),
            undone=bool(entry.get("undone")),
        )
        if entry.get("created_at"):
            row.created_at = datetime.fromisoformat(entry["created_at"])
        rows.append(row)
    session.add_all(rows)
    await session.flush()
    return len(rows)
