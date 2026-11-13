from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.equipment import FAMILIES
from aerona.catalog.structures import STRUCTURES
from aerona.catalog.units import UNITS
from aerona.catalog.vehicles import FRAMES
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cuisine import CommunityDishRow, DishIngredientRow, DishRow
from aerona.db.tables.equipment import EquipmentModelRow, UnitDesignEquipmentRow, UnitDesignTechniqueRow
from aerona.db.tables.integrity import StructureDesignSectionRow
from aerona.db.tables.military import ArmyUnitRow, UnitDesignRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.tables.vehicles import DesignMountRow, DesignSectionRow, DesignTechniqueRow, VehicleGroupRow

NONE = "none"


@dataclass
class KindFact:
    label: str
    value: str


@dataclass
class KindTable:
    title: str
    headers: list[str]
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class KindArticle:
    name: str
    kind: str
    maker: str
    description: str | None
    facts: list[KindFact] = field(default_factory=list)
    tables: list[KindTable] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)


@dataclass
class KindGroup:
    title: str
    articles: list[KindArticle]


@dataclass
class MadeWorld:
    name: str
    groups: list[KindGroup]


def words(value: object) -> str:
    text = str(getattr(value, "value", value)).replace("_", " ")
    return text[:1].upper() + text[1:]


def lower(value: object) -> str:
    return words(value).lower()


def facts(*pairs: tuple[str, object]) -> list[KindFact]:
    return [KindFact(label, str(value)) for label, value in pairs if value is not None and value != ""]


def grouped[Row](rows: list[Row], key: str) -> dict[int, list[Row]]:
    found: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        found[getattr(row, key)].append(row)
    return found


class MadeBook:
    def __init__(self, session: AsyncSession, names: dict[int, str]) -> None:
        self.session = session
        self.names = names

    def maker(self, node_id: int | None) -> str:
        return self.names.get(node_id, "no maker") if node_id is not None else "no maker"

    async def vehicles(self, world_id: int) -> list[KindArticle]:
        designs = list(await self.session.scalars(select(DesignRow).where(DesignRow.world_id == world_id).order_by(DesignRow.name, DesignRow.id)))
        ids = [row.id for row in designs]
        sections = grouped(
            list(await self.session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id.in_(ids)).order_by(DesignSectionRow.section))),
            "design_id",
        )
        mounts = grouped(
            list(await self.session.scalars(select(DesignMountRow).where(DesignMountRow.design_id.in_(ids)).order_by(DesignMountRow.slot))), "design_id"
        )
        techniques = grouped(list(await self.session.scalars(select(DesignTechniqueRow).where(DesignTechniqueRow.design_id.in_(ids)))), "design_id")
        models = {row.id: row.name for row in await self.session.scalars(select(EquipmentModelRow).where(EquipmentModelRow.world_id == world_id))}
        built_rows = await self.session.execute(
            select(VehicleGroupRow.design_id, func.sum(VehicleGroupRow.count)).where(VehicleGroupRow.design_id.in_(ids)).group_by(VehicleGroupRow.design_id)
        )
        built = {design_id: int(total or 0) for design_id, total in built_rows}
        found: list[KindArticle] = []
        for row in designs:
            frame = FRAMES[row.frame].label if row.frame is not None else "No frame"
            article = KindArticle(
                row.name,
                f"{frame}{' · superseded' if row.obsolete else ''}",
                self.maker(row.origin_node_id),
                row.description,
                facts(
                    ("Family", words(row.family) if row.family else NONE),
                    ("Goes by", words(row.domain) if row.domain else NONE),
                    ("Moved by", words(row.propulsion) if row.propulsion else NONE),
                    ("Size", words(row.size_class)),
                    ("Speed", row.speed),
                    ("Reach", row.range),
                    ("Seaworthiness", row.seaworthiness),
                    ("Cargo", row.cargo),
                    ("Arms", row.armament),
                    ("Crew", row.crew),
                    ("Troops carried", row.troops),
                    ("Armour", row.armour),
                    ("Structure", row.structure),
                    ("Fuel", f"{lower(row.fuel)}, {row.fuel_use} an epoch" if row.fuel else NONE),
                    ("Cost and upkeep", f"{row.cost} and {row.upkeep}"),
                    ("Knowledge it needs", f"level {row.tech_level}"),
                    ("Strangeness", row.strangeness),
                    ("Weapons aimed", lower(row.fire_control)),
                    ("Held by", self.maker(row.owner_entity_id)),
                    ("Drawn by", self.names.get(row.designer_entity_id, "its makers") if row.designer_entity_id is not None else "its makers"),
                    ("Drawn in epoch", row.epoch),
                    ("Vehicles built to it", built.get(row.id, 0)),
                ),
            )
            parts = sections.get(row.id, [])
            if parts:
                article.tables.append(
                    KindTable(
                        "Sections",
                        ["Section", "Serves", "Criticality", "Share", "Exposure", "Armour", "When it fails", "Spreads to"],
                        [
                            [
                                words(part.section),
                                lower(part.function),
                                lower(part.criticality),
                                f"{part.share}%",
                                f"{part.exposure}%",
                                str(part.armour),
                                lower(part.hazard),
                                ", ".join(lower(item) for item in part.neighbours) or NONE,
                            ]
                            for part in parts
                        ],
                    )
                )
            fitted = mounts.get(row.id, [])
            if fitted:
                article.tables.append(
                    KindTable(
                        "Weapon mounts",
                        ["Mount", "How many", "On", "Arc", "Weapon"],
                        [
                            [
                                words(mount.mount),
                                str(mount.count),
                                lower(mount.section) if mount.section else NONE,
                                lower(mount.arc),
                                models.get(mount.model_id, NONE) if mount.model_id is not None else NONE,
                            ]
                            for mount in fitted
                        ],
                    )
                )
            needed = sorted(lower(item.technique) for item in techniques.get(row.id, []))
            if needed:
                article.lines.append(f"Its builders must know: {', '.join(needed)}.")
            found.append(article)
        return found

    async def units(self, world_id: int) -> list[KindArticle]:
        designs = list(
            await self.session.scalars(select(UnitDesignRow).where(UnitDesignRow.world_id == world_id).order_by(UnitDesignRow.name, UnitDesignRow.id))
        )
        ids = [row.id for row in designs]
        loadouts = grouped(list(await self.session.scalars(select(UnitDesignEquipmentRow).where(UnitDesignEquipmentRow.design_id.in_(ids)))), "design_id")
        techniques = grouped(list(await self.session.scalars(select(UnitDesignTechniqueRow).where(UnitDesignTechniqueRow.design_id.in_(ids)))), "design_id")
        models = {row.id: row for row in await self.session.scalars(select(EquipmentModelRow).where(EquipmentModelRow.world_id == world_id))}
        vehicles = {row.id: row.name for row in await self.session.scalars(select(DesignRow).where(DesignRow.world_id == world_id))}
        fielded_rows = await self.session.execute(
            select(ArmyUnitRow.design_id, func.sum(ArmyUnitRow.count)).where(ArmyUnitRow.design_id.in_(ids)).group_by(ArmyUnitRow.design_id)
        )
        fielded = {design_id: int(total or 0) for design_id, total in fielded_rows}
        found: list[KindArticle] = []
        for row in designs:
            article = KindArticle(
                row.name,
                f"{UNITS[row.base_kind].label}{' · retired' if row.retired else ''}",
                self.maker(row.origin_node_id),
                row.description,
                facts(
                    ("Family", words(row.family)),
                    ("Melee", row.melee),
                    ("Missile", row.missile),
                    ("Defence", row.defence),
                    ("Speed", row.speed),
                    ("Mass", row.mass),
                    ("Armour and shield", f"{lower(row.armour)} and {lower(row.shield)}"),
                    ("Reach and volleys", f"{row.reach} and {row.volleys}"),
                    ("Accuracy and piercing", f"{row.accuracy} and {row.piercing}"),
                    ("Terror", row.terror),
                    ("Discipline", row.discipline),
                    ("Doctrine", lower(row.doctrine) if row.doctrine else NONE),
                    ("Formation", lower(row.formation) if row.formation else NONE),
                    ("Epochs of training", row.training_epochs),
                    ("Cost and upkeep", f"{row.cost} and {row.upkeep}"),
                    ("Drawn from", lower(row.social_class) if row.social_class else "any class"),
                    ("Stands against charges", "yes" if row.counters_charge else "no"),
                    ("Flies", "yes" if row.flying else "no"),
                    ("Rides", self.names.get(row.mount_species_id, NONE) if row.mount_species_id is not None else NONE),
                    (
                        "Crews",
                        f"{vehicles.get(row.vehicle_design_id, 'a vehicle')}, {row.crew_per_vehicle} to each" if row.vehicle_design_id is not None else NONE,
                    ),
                    ("Fielded by", self.maker(row.owner_entity_id)),
                    ("Soldiers in the field", fielded.get(row.id, 0)),
                    ("Raised since epoch", row.created_epoch),
                ),
            )
            pieces = [item for item in loadouts.get(row.id, []) if item.model_id in models]
            if pieces:
                article.tables.append(
                    KindTable(
                        "Loadout",
                        ["Model", "Kind", "Carried as", "Pieces each"],
                        [
                            [models[item.model_id].name, FAMILIES[models[item.model_id].family].label, lower(models[item.model_id].slot), str(item.count)]
                            for item in pieces
                        ],
                    )
                )
            needed = sorted(lower(item.technique) for item in techniques.get(row.id, []))
            if needed:
                article.lines.append(f"Its makers must know: {', '.join(needed)}.")
            found.append(article)
        return found

    async def equipment(self, world_id: int) -> list[KindArticle]:
        rows = await self.session.scalars(
            select(EquipmentModelRow).where(EquipmentModelRow.world_id == world_id).order_by(EquipmentModelRow.name, EquipmentModelRow.id)
        )
        return [
            KindArticle(
                row.name,
                f"{FAMILIES[row.family].label}{' · retired' if row.retired else ''}",
                self.maker(row.origin_node_id),
                row.description,
                facts(
                    ("Carried as", lower(row.slot)),
                    ("Material", lower(row.material) if row.material else "its makers' own"),
                    ("Quality", row.quality),
                    ("Damage", f"{row.damage}, {lower(row.damage_type)}"),
                    ("Piercing", row.piercing),
                    ("Reach, rate and accuracy", f"{row.reach}, {row.rate} and {row.accuracy}"),
                    ("Protection and coverage", f"{row.protection} and {row.coverage}"),
                    ("Ammunition", lower(row.ammunition) if row.ammunition else NONE),
                    ("Crew", row.crew),
                    ("Weight and cost", f"{row.weight} and {row.cost}"),
                    ("Knowledge it needs", f"level {row.tech_level}" + (f", {lower(row.technique)}" if row.technique else "")),
                    ("Renown", row.renown),
                    ("Made since epoch", row.created_epoch),
                ),
            )
            for row in rows
        ]

    async def dishes(self, world_id: int) -> list[KindArticle]:
        rows = list(await self.session.scalars(select(DishRow).where(DishRow.world_id == world_id).order_by(DishRow.name, DishRow.id)))
        ids = [row.id for row in rows]
        foods = grouped(
            list(await self.session.scalars(select(DishIngredientRow).where(DishIngredientRow.dish_id.in_(ids)).order_by(DishIngredientRow.share.desc()))),
            "dish_id",
        )
        kitchens = grouped(
            list(await self.session.scalars(select(CommunityDishRow).where(CommunityDishRow.dish_id.in_(ids)).order_by(CommunityDishRow.popularity.desc()))),
            "dish_id",
        )
        found: list[KindArticle] = []
        for row in rows:
            article = KindArticle(
                row.name,
                f"{words(row.course)}, {lower(row.method)}{' · forgotten' if row.retired else ''}",
                self.maker(row.origin_node_id),
                row.description,
                facts(
                    ("Nourishment", row.nourishment),
                    ("Delight", row.delight),
                    ("Keeps", f"{row.keeps} epochs"),
                    ("Prestige", row.prestige),
                    ("Technique it needs", lower(row.technique) if row.technique else NONE),
                    ("First cooked in epoch", row.created_epoch),
                ),
            )
            made = foods.get(row.id, [])
            if made:
                article.lines.append("Made of " + ", ".join(f"{lower(item.commodity)} ({item.share}%)" for item in made) + ".")
            cooked = kitchens.get(row.id, [])
            if cooked:
                article.tables.append(
                    KindTable(
                        "Cooked in",
                        ["Community", "Popularity", "Times cooked", "Since epoch"],
                        [[self.maker(item.community_entity_id), str(item.popularity), str(item.cooked), str(item.since_epoch)] for item in cooked],
                    )
                )
            found.append(article)
        return found

    async def buildings(self, world_id: int) -> list[KindArticle]:
        rows = list(
            await self.session.scalars(
                select(StructureDesignRow).where(StructureDesignRow.world_id == world_id).order_by(StructureDesignRow.name, StructureDesignRow.id)
            )
        )
        ids = [row.id for row in rows]
        parts = grouped(
            list(
                await self.session.scalars(
                    select(StructureDesignSectionRow).where(StructureDesignSectionRow.design_id.in_(ids)).order_by(StructureDesignSectionRow.section)
                )
            ),
            "design_id",
        )
        used_rows = await self.session.execute(
            select(StructureProfileRow.design_id, func.count()).where(StructureProfileRow.design_id.in_(ids)).group_by(StructureProfileRow.design_id)
        )
        used = {design_id: int(count) for design_id, count in used_rows if design_id is not None}
        found: list[KindArticle] = []
        for row in rows:
            article = KindArticle(
                row.name,
                f"{STRUCTURES[row.base_kind].label}{' · retired' if row.retired else ''}",
                self.maker(row.origin_node_id),
                row.description,
                facts(
                    ("Form", lower(row.form) if row.form else "its kind's"),
                    ("Storeys", row.storeys if row.storeys is not None else "its kind's"),
                    ("Material", lower(row.material) if row.material else "its kind's"),
                    ("Capacity, cost and upkeep", f"{row.capacity_pct}%, {row.cost_pct}% and {row.upkeep_pct}%"),
                    ("Function and staff", f"{row.function_pct}% and {row.staff_pct}%"),
                    ("Staffed by", lower(row.staff_class) if row.staff_class else "its kind's class"),
                    ("Hands it needs", lower(row.staff_scale) if row.staff_scale else "its kind's"),
                    ("Scale", lower(row.scale) if row.scale else "its kind's"),
                    ("Upkeep paid in", lower(row.upkeep_commodity) if row.upkeep_commodity else "its kind's goods"),
                    ("Smallest place", lower(row.min_tier) if row.min_tier else "its kind's"),
                    ("Ley lines", NONE if row.ley is None else ("draws on them" if row.ley else "ignores them")),
                    ("Works built to it", used.get(row.id, 0)),
                    ("Drawn in epoch", row.created_epoch),
                ),
            )
            own = parts.get(row.id, [])
            if own:
                article.tables.append(
                    KindTable(
                        "Sections of its own",
                        ["Section", "Criticality", "Share", "Material"],
                        [
                            [words(part.section), lower(part.criticality), f"{part.share}%", lower(part.material) if part.material else "the type's"]
                            for part in own
                        ],
                    )
                )
            found.append(article)
        return found

    async def worlds(self) -> list[MadeWorld]:
        found: list[MadeWorld] = []
        for world in await self.session.scalars(select(WorldRow).order_by(WorldRow.id)):
            groups = [
                KindGroup("Vehicle types", await self.vehicles(world.id)),
                KindGroup("Kinds of soldier", await self.units(world.id)),
                KindGroup("Equipment models", await self.equipment(world.id)),
                KindGroup("Dishes", await self.dishes(world.id)),
                KindGroup("Building types", await self.buildings(world.id)),
            ]
            kept = [group for group in groups if group.articles]
            if kept:
                found.append(MadeWorld(world.name, kept))
        return found


async def made_kinds(session: AsyncSession, names: dict[int, str]) -> list[MadeWorld]:
    return await MadeBook(session, names).worlds()
