import {
  Anvil,
  ArrowRightLeft,
  Ban,
  Banknote,
  Binoculars,
  Bird,
  Bomb,
  BookOpen,
  Bot,
  BowArrow,
  BrickWall,
  Castle,
  ChessKing,
  ChessKnight,
  ChessPawn,
  ChessRook,
  ChevronsUp,
  Church,
  Cloud,
  Coins,
  Columns3,
  Crosshair,
  Crown,
  Disc3,
  Eclipse,
  Eye,
  Feather,
  Fence,
  Flag,
  Flame,
  Footprints,
  Frown,
  Ghost,
  Grid3x3,
  Hammer,
  HandCoins,
  HandFist,
  Handshake,
  HeartCrack,
  Hexagon,
  Hourglass,
  KeyRound,
  Landmark,
  LandPlot,
  Layers,
  Link,
  Lock,
  LockOpen,
  Medal,
  Megaphone,
  Meh,
  Merge,
  Moon,
  Mountain,
  PawPrint,
  Pickaxe,
  RotateCcw,
  Route,
  Rows3,
  Sailboat,
  Scale,
  ScrollText,
  Shell,
  Shield,
  ShieldCheck,
  ShieldHalf,
  ShieldPlus,
  Ship,
  ShipWheel,
  Shovel,
  Signpost,
  Skull,
  Slash,
  Smile,
  Snowflake,
  Sparkles,
  Sword,
  Swords,
  ThumbsDown,
  Triangle,
  Trophy,
  Users,
  Undo2,
  VenetianMask,
  WandSparkles,
  Waves,
  Wheat,
  Wind,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type Named, named } from '@/features/entity/environment/labels'

export { named, type Named }

type Schemas = components['schemas']

export const PERCENT = 100
export const WORKING = 'Working…'

export const SIDE: Record<string, Named> = {
  attacker: { label: 'Attackers', icon: Swords, tone: 'danger' },
  defender: { label: 'Defenders', icon: Shield, tone: 'info' },
}

export const STANCE: Record<string, Named> = {
  march: { label: 'On the march', icon: Footprints, tone: 'gold' },
  forage: { label: 'Foraging', icon: Wheat, tone: 'success' },
  entrench: { label: 'Entrenched', icon: Shovel, tone: 'verdigris' },
  besiege: { label: 'Besieging', icon: ChessRook, tone: 'danger' },
  garrison: { label: 'In garrison', icon: Castle, tone: 'info' },
  raid: { label: 'Raiding', icon: Flame, tone: 'warning' },
  retreat: { label: 'Retreating', icon: Undo2, tone: 'muted' },
}

export const DOCTRINE: Record<Schemas['MartialStyle'], Named> = {
  shieldwall: { label: 'Shield wall', icon: Shield, tone: 'info' },
  horse_archer: { label: 'Horse archers', icon: BowArrow, tone: 'warning' },
  skirmisher: { label: 'Skirmishers', icon: Crosshair, tone: 'gold' },
  chariot: { label: 'Chariots', icon: Disc3, tone: 'gold' },
  phalanx: { label: 'Phalanx', icon: Fence, tone: 'info' },
  berserker: { label: 'Berserkers', icon: HandFist, tone: 'danger' },
  naval_raider: { label: 'Sea raiders', icon: Sailboat, tone: 'info' },
  siege_engineer: { label: 'Siege engineers', icon: Anvil, tone: 'muted' },
  war_magic: { label: 'War magic', icon: WandSparkles, tone: 'verdigris' },
  beast_war: { label: 'Beast war', icon: PawPrint, tone: 'danger' },
}

export const AIM: Record<string, Named> = {
  conquer_region: { label: 'Conquer a land', icon: LandPlot, tone: 'danger' },
  seize_settlement: {
    label: 'Seize a settlement',
    icon: Castle,
    tone: 'danger',
  },
  press_claim: { label: 'Press a claim', icon: Crown, tone: 'gold' },
  convert: { label: 'Convert the faithful', icon: Church, tone: 'verdigris' },
  tribute: { label: 'Exact tribute', icon: HandCoins, tone: 'gold' },
  vassalise: { label: 'Make a vassal', icon: ChessKing, tone: 'gold' },
  liberate: { label: 'Liberate', icon: LockOpen, tone: 'success' },
  destroy_cult: { label: 'Destroy a cult', icon: Flame, tone: 'danger' },
  seize_resource: {
    label: 'Seize a resource',
    icon: Pickaxe,
    tone: 'warning',
  },
  seize_nexus: { label: 'Seize a nexus', icon: Sparkles, tone: 'verdigris' },
  humiliate: { label: 'Humiliate', icon: ThumbsDown, tone: 'warning' },
  revenge: { label: 'Revenge', icon: Skull, tone: 'danger' },
  loot: { label: 'Loot', icon: Coins, tone: 'warning' },
  change_government: {
    label: 'Overthrow the rulers',
    icon: Landmark,
    tone: 'info',
  },
  seize_route: {
    label: 'Seize a trade road',
    icon: Signpost,
    tone: 'gold',
  },
}

export const FATE: Record<string, Named> = {
  held: { label: 'Held', icon: Lock, tone: 'warning' },
  ransomed: { label: 'Ransomed', icon: HandCoins, tone: 'gold' },
  enslaved: { label: 'Enslaved', icon: Link, tone: 'danger' },
  sacrificed: { label: 'Sacrificed', icon: Skull, tone: 'danger' },
  labour: { label: 'Forced labour', icon: Pickaxe, tone: 'warning' },
  exchanged: { label: 'Exchanged', icon: ArrowRightLeft, tone: 'info' },
  released: { label: 'Released', icon: LockOpen, tone: 'success' },
}

export const TRAIT: Record<Schemas['CommanderTrait'], Named> = {
  aggressive_assaulter: {
    label: 'Aggressive assaulter',
    icon: Swords,
    tone: 'danger',
  },
  defensive_genius: {
    label: 'Defensive genius',
    icon: ShieldCheck,
    tone: 'info',
  },
  cavalry_master: { label: 'Cavalry master', icon: ChessKnight, tone: 'gold' },
  winter_campaigner: {
    label: 'Winter campaigner',
    icon: Snowflake,
    tone: 'info',
  },
  hill_fighter: { label: 'Hill fighter', icon: Mountain, tone: 'verdigris' },
  siege_expert: { label: 'Siege expert', icon: ChessRook, tone: 'warning' },
  reckless: { label: 'Reckless', icon: Zap, tone: 'danger' },
  cautious: { label: 'Cautious', icon: Hourglass, tone: 'muted' },
  inspiring: { label: 'Inspiring', icon: Megaphone, tone: 'gold' },
  brutal: { label: 'Brutal', icon: Skull, tone: 'danger' },
}

export const FAMILY: Record<string, Named> = {
  infantry: { label: 'Infantry', icon: ChessPawn, tone: 'gold' },
  missile: { label: 'Missile troops', icon: BowArrow, tone: 'info' },
  mounted: { label: 'Mounted', icon: ChessKnight, tone: 'warning' },
  beast: { label: 'Beasts', icon: PawPrint, tone: 'danger' },
  engineer: { label: 'Engineers', icon: Anvil, tone: 'success' },
  magic: { label: 'Magic', icon: WandSparkles, tone: 'verdigris' },
  naval: { label: 'Naval', icon: Sailboat, tone: 'info' },
  exotic: { label: 'Exotic', icon: Sparkles, tone: 'verdigris' },
}

export const UNIT_ICON: Record<string, LucideIcon> = {
  levy: ChessPawn,
  spearmen: Slash,
  heavy_infantry: ShieldHalf,
  shield_wall: Shield,
  pikemen: Fence,
  skirmishers: Crosshair,
  berserkers: HandFist,
  temple_guard: Church,
  slingers: Disc3,
  archers: BowArrow,
  crossbowmen: Crosshair,
  horse_archers: BowArrow,
  javelineers: Slash,
  light_cavalry: ChessKnight,
  heavy_cavalry: ChessKnight,
  beast_riders: PawPrint,
  chariots: Disc3,
  war_beasts: PawPrint,
  bound_beasts: Link,
  sky_mounts: Bird,
  sappers: Shovel,
  siege_engines: Anvil,
  war_mages: WandSparkles,
  priests: Church,
  necromancers: Skull,
  galleys: Ship,
  longships: Sailboat,
  warships: ShipWheel,
  fire_ships: Flame,
  skyships: Cloud,
  golems: Bot,
  void_spawn: Eclipse,
  ghost_host: Ghost,
}

export const ARMOUR: Record<string, Named & { rank: number }> = {
  none: { label: 'No armour', icon: Ban, tone: 'muted', rank: 0 },
  hide: { label: 'Hide', icon: Shell, tone: 'muted', rank: 1 },
  padded: { label: 'Padded cloth', icon: Layers, tone: 'muted', rank: 2 },
  mail: { label: 'Mail', icon: Link, tone: 'info', rank: 3 },
  scale: { label: 'Scale', icon: Hexagon, tone: 'info', rank: 4 },
  plate: { label: 'Plate', icon: ShieldHalf, tone: 'gold', rank: 5 },
  enchanted: {
    label: 'Enchanted',
    icon: Sparkles,
    tone: 'verdigris',
    rank: 6,
  },
}

export const SHIELD: Record<string, Named & { rank: number }> = {
  none: { label: 'No shield', icon: Ban, tone: 'muted', rank: 0 },
  small: { label: 'Small shield', icon: ShieldHalf, tone: 'info', rank: 1 },
  large: { label: 'Large shield', icon: Shield, tone: 'info', rank: 2 },
  tower: { label: 'Tower shield', icon: ShieldPlus, tone: 'gold', rank: 3 },
}

export const WEAPON: Record<string, Named> = {
  spear: { label: 'Spear', icon: Slash },
  blade: { label: 'Blade', icon: Sword },
  bow: { label: 'Bow', icon: BowArrow },
  blunt: { label: 'Hammer', icon: Hammer },
  claw: { label: 'Claw and fang', icon: PawPrint },
  staff: { label: 'Staff', icon: WandSparkles },
}

export const COVER: Record<string, Named> = {
  merchant: { label: 'Merchants', icon: Coins, tone: 'gold' },
  priest: { label: 'Priests', icon: Church, tone: 'verdigris' },
  envoy: { label: 'Envoys', icon: ScrollText, tone: 'info' },
  beggar: { label: 'Beggars', icon: VenetianMask, tone: 'muted' },
}

export const OPERATION: Record<string, Named> = {
  steal_knowledge: { label: 'Stole knowledge', icon: BookOpen, tone: 'info' },
  sabotage: { label: 'Sabotage', icon: Bomb, tone: 'danger' },
  assassinate: { label: 'Assassination', icon: Skull, tone: 'danger' },
  incite: { label: 'Incited unrest', icon: Megaphone, tone: 'warning' },
  intel: { label: 'Gathered intelligence', icon: Binoculars, tone: 'info' },
  blackmail: { label: 'Blackmail', icon: KeyRound, tone: 'warning' },
  counterfeit: { label: 'Counterfeit coin', icon: Banknote, tone: 'warning' },
}

export const SIEGE_STATUS: Record<string, Named> = {
  ongoing: { label: 'Under siege', icon: ChessRook, tone: 'warning' },
  breached: { label: 'Walls breached', icon: BrickWall, tone: 'danger' },
  repulsed: { label: 'Siege repulsed', icon: ShieldCheck, tone: 'success' },
  lifted: { label: 'Siege lifted', icon: Flag, tone: 'muted' },
}

export const STARVATION: Record<string, Named> = {
  none: { label: 'Fed', icon: Wheat, tone: 'success' },
  rationing: { label: 'Rationing', icon: Scale, tone: 'warning' },
  famine: { label: 'Famine', icon: HeartCrack, tone: 'danger' },
  taboo_broken: { label: 'Taboo broken', icon: Skull, tone: 'danger' },
}

export const SIEGE_ACTION: Record<string, Named> = {
  blockade: { label: 'Blockade', icon: Fence, tone: 'warning' },
  bombard: { label: 'Bombardment', icon: Bomb, tone: 'danger' },
  mine: { label: 'Mining the walls', icon: Pickaxe, tone: 'warning' },
  assault: { label: 'Assault', icon: Swords, tone: 'danger' },
  negotiate: { label: 'Parley', icon: Handshake, tone: 'info' },
}

export const DEFENCE: Record<string, Named> = {
  sally: { label: 'Sally', icon: Swords, tone: 'danger' },
  repair: { label: 'Repairing walls', icon: Hammer, tone: 'info' },
  ration: { label: 'Rationing', icon: Scale, tone: 'warning' },
  seek_relief: { label: 'Seeking relief', icon: Megaphone, tone: 'gold' },
}

export const WORKS: Record<string, Named> = {
  famine: { label: 'Seasons of famine', icon: HeartCrack, tone: 'danger' },
  mines: { label: 'Mines dug', icon: Pickaxe, tone: 'warning' },
}

export const OUTCOME: Record<string, Named> = {
  field_victory: { label: 'Field victory', icon: Swords, tone: 'danger' },
  great_victory: { label: 'Great victory', icon: Trophy, tone: 'gold' },
  siege_repulsed: { label: 'Siege repulsed', icon: ShieldCheck, tone: 'info' },
  siege_breached: { label: 'Walls breached', icon: Castle, tone: 'danger' },
  siege_starvation: { label: 'Starved out', icon: Hourglass, tone: 'warning' },
  refused: { label: 'Battle refused', icon: Shield, tone: 'muted' },
}

export const OUTCOME_CLASS: Record<string, Named> = {
  decisive: { label: 'Decisive', icon: Trophy, tone: 'gold' },
  victory: { label: 'Victory', icon: Medal, tone: 'success' },
  pyrrhic: { label: 'Pyrrhic', icon: HeartCrack, tone: 'warning' },
  stalemate: { label: 'Stalemate', icon: Scale, tone: 'muted' },
  rout: { label: 'Rout', icon: Footprints, tone: 'danger' },
  massacre: { label: 'Massacre', icon: Skull, tone: 'danger' },
  refused: { label: 'Battle refused', icon: Ban, tone: 'muted' },
}

export const TACTIC: Record<string, Named> = {
  hold_line: { label: 'Hold the line', icon: Fence },
  frontal_assault: { label: 'Frontal assault', icon: Swords },
  double_envelopment: { label: 'Double envelopment', icon: Merge },
  feigned_retreat: { label: 'Feigned retreat', icon: Undo2 },
  flank_cavalry: { label: 'Cavalry on the flank', icon: ChessKnight },
  missile_attrition: { label: 'Arrow storm', icon: BowArrow },
  shield_wall: { label: 'Shield wall', icon: Shield },
  wedge: { label: 'Wedge', icon: ChevronsUp },
  night_raid: { label: 'Night raid', icon: Moon },
  ambush: { label: 'Ambush', icon: Eye },
  skirmish_harass: { label: 'Skirmish and harass', icon: Crosshair },
  river_defence: { label: 'River defence', icon: Waves },
  siege_assault: { label: 'Storm the walls', icon: ChessRook },
  feint: { label: 'Feint', icon: ArrowRightLeft },
}

export const PHASE: Record<string, Named> = {
  scouting: { label: 'Scouting', icon: Binoculars, tone: 'info' },
  plan: { label: 'Battle plans', icon: ScrollText, tone: 'gold' },
  command: { label: 'Orders', icon: Megaphone, tone: 'gold' },
  missile: { label: 'Volleys', icon: BowArrow, tone: 'warning' },
  charge: { label: 'Charge', icon: ChessKnight, tone: 'warning' },
  melee: { label: 'Melee', icon: Swords, tone: 'danger' },
  reserves: { label: 'Reserves', icon: Layers, tone: 'info' },
  rites: { label: 'Rites', icon: Sparkles, tone: 'verdigris' },
  pursuit: { label: 'Pursuit', icon: Footprints, tone: 'danger' },
  salvage: { label: 'Salvage', icon: Hammer, tone: 'success' },
  aftermath: { label: 'Aftermath', icon: Skull, tone: 'muted' },
}

export const PHASE_DETAIL: Record<string, string> = {
  margin: 'Scouting edge',
  attacker: 'Attacker plan',
  defender: 'Defender plan',
  wounded: 'Wounded',
  maimed: 'Maimed',
}

export const FIELD: Record<string, string> = {
  organisation: 'Organisation',
  discipline: 'Discipline',
  ammunition: 'Volleys carried',
  missing: 'Stragglers',
  contact_seasons: 'Seasons in contact',
  supply_days: 'Supplies (days)',
  war_chest: 'War chest',
  cohesion: 'Cohesion',
  disease: 'Camp sickness',
  entrenchment: 'Earthworks',
  loot: 'Loot carried',
  baggage: 'Baggage',
  stance: 'Stance',
  doctrine: 'Way of war',
  forced_march: 'Forced march',
  target_id: 'March target',
  count: 'Soldiers',
  quality: 'Quality',
  experience: 'Experience',
  morale: 'Morale',
  fatigue: 'Fatigue',
  wounded: 'Wounded',
  condition: 'Gear condition',
  supplies: 'Food (days)',
  water: 'Water (days)',
  breaches: 'Breaches',
  walls_level: 'Wall strength',
  disease_inside: 'Sickness inside',
  disease_outside: 'Sickness outside',
  sallies: 'Sallies',
  agents: 'Agents',
  depth: 'Depth',
  exposure: 'Exposure',
  intel: 'Intelligence',
}

export function fieldLabel(key: string): string {
  return (
    FIELD[key] ??
    key.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase())
  )
}

export function labelsOf(table: Record<string, Named>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}

export function wearinessLevel(value: number): Named {
  if (value >= 70) return { label: 'Broken', icon: HeartCrack, tone: 'danger' }
  if (value >= 45) return { label: 'Weary', icon: Hourglass, tone: 'warning' }
  if (value >= 20) return { label: 'Tiring', icon: Footprints, tone: 'gold' }
  return { label: 'Eager', icon: Flame, tone: 'success' }
}

export function percentTone(
  value: number,
  harmful = false
): 'success' | 'warning' | 'destructive' {
  const good = harmful ? PERCENT - value : value
  if (good >= 60) return 'success'
  if (good >= 30) return 'warning'
  return 'destructive'
}

export const PROGRESS_TONE: Record<
  KpiTone,
  | 'default'
  | 'verdigris'
  | 'info'
  | 'success'
  | 'warning'
  | 'destructive'
  | 'muted'
> = {
  gold: 'default',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
}

export const BADGE_TONE: Record<
  KpiTone,
  'default' | 'info' | 'success' | 'warning' | 'destructive' | 'secondary'
> = {
  gold: 'default',
  verdigris: 'success',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'secondary',
}

const ICON_TONE: Record<KpiTone, string> = {
  gold: 'text-primary',
  verdigris: 'text-brand-verdigris',
  info: 'text-info',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
  muted: 'text-muted-foreground',
}

const FRAME_TONE: Record<KpiTone, string> = {
  gold: 'border-primary/30 bg-primary/5',
  verdigris: 'border-brand-verdigris/30 bg-brand-verdigris/5',
  info: 'border-info/30 bg-info/5',
  success: 'border-success/30 bg-success/5',
  warning: 'border-warning/30 bg-warning/5',
  danger: 'border-destructive/30 bg-destructive/5',
  muted: 'border-border bg-muted/20',
}

export function iconTone(tone: KpiTone | undefined): string {
  return ICON_TONE[tone ?? 'muted']
}

export function frameTone(tone: KpiTone | undefined): string {
  return FRAME_TONE[tone ?? 'muted']
}

export function busyOf(
  blocked: string | null,
  ...pending: boolean[]
): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

export function whole(value: string, max?: number, min = 0): number {
  const parsed = Math.round(Number(value) || 0)
  return Math.max(min, max === undefined ? parsed : Math.min(max, parsed))
}

export function cardGrid(count: number): string {
  return count === 1
    ? 'grid min-w-0 grid-cols-1 gap-3'
    : 'grid min-w-0 grid-cols-1 gap-3 @2xl/mil:grid-cols-2 @6xl/mil:grid-cols-3'
}

export const FORMATION: Record<Schemas['Formation'], Named> = {
  line: { label: 'Line', icon: Rows3, tone: 'gold' },
  column: { label: 'Column', icon: Columns3, tone: 'muted' },
  wedge: { label: 'Wedge', icon: Triangle, tone: 'warning' },
  square: { label: 'Square', icon: Grid3x3, tone: 'info' },
  loose: { label: 'Loose order', icon: Feather, tone: 'verdigris' },
  shieldwall: { label: 'Shield wall', icon: BrickWall, tone: 'gold' },
}

export const MORALE_STATE: Record<Schemas['MoraleState'], Named> = {
  steady: { label: 'Steady', icon: Smile, tone: 'success' },
  shaken: { label: 'Shaken', icon: Meh, tone: 'warning' },
  wavering: { label: 'Wavering', icon: Frown, tone: 'warning' },
  routing: { label: 'Routing', icon: Wind, tone: 'danger' },
  broken: { label: 'Broken', icon: Skull, tone: 'danger' },
  rallied: { label: 'Rallied', icon: RotateCcw, tone: 'gold' },
}

export const TARGET_CLASS: Record<Schemas['TargetClass'], Named> = {
  soft: { label: 'Soft target', icon: Feather, tone: 'muted' },
  hard: { label: 'Hard target', icon: ShieldHalf, tone: 'gold' },
}

export const CASUS_BELLI: Record<Schemas['CasusBelliKind'], Named> = {
  claim: { label: 'A claim', icon: Crown, tone: 'gold' },
  holy_war: { label: 'Holy war', icon: Church, tone: 'verdigris' },
  vendetta: { label: 'Vendetta for killed kin', icon: Swords, tone: 'danger' },
  broken_treaty: { label: 'A broken treaty', icon: ScrollText, tone: 'danger' },
  insult: { label: 'An insult', icon: Megaphone, tone: 'warning' },
  liberation: { label: 'Liberation of kin', icon: Users, tone: 'info' },
  trade_dispute: { label: 'A trade dispute', icon: Banknote, tone: 'warning' },
  debt_default: { label: 'A defaulted debt', icon: Coins, tone: 'warning' },
  resource_need: {
    label: 'Need of land and food',
    icon: Wheat,
    tone: 'warning',
  },
  conquest: { label: 'Conquest', icon: Flag, tone: 'muted' },
}

export const WAR_GOODS: Record<string, Named> = {
  weapons: { label: 'Weapons', icon: Swords, tone: 'danger' },
  armour: { label: 'Armour', icon: Shield, tone: 'info' },
  siege_materiel: { label: 'Siege materiel', icon: Castle, tone: 'warning' },
}

export const COMMAND_AREA: Record<Schemas['CommandArea'], Named> = {
  fire: { label: 'Fire', icon: Crosshair, tone: 'info' },
  shock: { label: 'Shock', icon: Swords, tone: 'danger' },
  manoeuvre: { label: 'Manoeuvre', icon: Route, tone: 'gold' },
  siege: { label: 'Siege', icon: Castle, tone: 'warning' },
  logistics: { label: 'Logistics', icon: Wheat, tone: 'success' },
}
