import {
  Split,
  Link,
  BatteryLow,
  Ban,
  BookMarked,
  Brain,
  CircleDashed,
  Crown,
  Eye,
  EyeOff,
  Flame,
  Gavel,
  Ghost,
  Globe,
  Handshake,
  HeartCrack,
  Hourglass,
  Layers,
  Link2Off,
  Map,
  Moon,
  Orbit,
  ScrollText,
  Shield,
  Skull,
  Sparkles,
  Star,
  Sun,
  Swords,
  Target,
  Telescope,
  Trophy,
  Undo2,
  Users,
  Zap,
  type LucideIcon,
  ShieldAlert,
  Landmark,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import type { KpiTone } from '@/components/domain'

export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

type Schema = components['schemas']

export const GOAL_KINDS: Record<Schema['GodGoalKind'], Named> = {
  be_worshipped: { label: 'Be worshipped', icon: Users, tone: 'gold' },
  found_realm: { label: 'Found a holy world', icon: Globe, tone: 'gold' },
  destroy_rival: { label: 'Destroy a rival', icon: Swords, tone: 'danger' },
  spread_domain: {
    label: 'Spread a domain',
    icon: Sparkles,
    tone: 'verdigris',
  },
  win_war: { label: 'Win a war', icon: Trophy, tone: 'warning' },
  acquire_relic: { label: 'Acquire a relic', icon: BookMarked, tone: 'info' },
  raise_hero: { label: 'Raise a hero', icon: Crown, tone: 'success' },
  awaken_god: { label: 'Awaken a god', icon: Sun, tone: 'info' },
  defeat_foreign_god: {
    label: 'Defeat a foreign god',
    icon: Swords,
    tone: 'danger',
  },
  reconcile: {
    label: 'Reconcile with the Creator',
    icon: Handshake,
    tone: 'success',
  },
  rebel: { label: 'Rebel against the Creator', icon: Flame, tone: 'danger' },
  hold_thrones: {
    label: 'Hold the thrones of power',
    icon: Crown,
    tone: 'gold',
  },
  prevent_mantling: {
    label: "Keep a mortal from taking a god's place",
    icon: ShieldAlert,
    tone: 'warning',
  },
  sponsor_mantling: {
    label: 'Raise a chosen mortal to godhood',
    icon: Crown,
    tone: 'gold',
  },
}

export const GOAL_STATES: Record<Schema['GoalState'], Named> = {
  active: { label: 'Pursued', icon: Target, tone: 'info' },
  done: { label: 'Reached', icon: Trophy, tone: 'success' },
  failed: { label: 'Failed', icon: HeartCrack, tone: 'danger' },
  dropped: { label: 'Set aside', icon: Undo2, tone: 'muted' },
}

export const GOAL_SOURCES: Record<Schema['GoalSource'], string> = {
  engine: 'Chosen by the god itself',
  agent: 'Chosen in the god’s own turn',
  creator: 'Given by the Creator',
}

export const WOUND_KINDS: Record<Schema['DivineWoundKind'], Named> = {
  severed_domain: { label: 'Severed domain', icon: Link2Off, tone: 'danger' },
  shattered_manifestation: {
    label: 'Shattered manifestation',
    icon: Ghost,
    tone: 'warning',
  },
  stolen_name: { label: 'Stolen true name', icon: ScrollText, tone: 'warning' },
  void_wound: {
    label: 'Wound of the void',
    icon: CircleDashed,
    tone: 'danger',
  },
  drained_essence: {
    label: 'Drained essence',
    icon: BatteryLow,
    tone: 'danger',
  },
  lost_worshippers: {
    label: 'Lost worshippers',
    icon: Link2Off,
    tone: 'danger',
  },
  bound: { label: 'Bound', icon: Link, tone: 'danger' },
  split_aspect: { label: 'Split aspect', icon: Split, tone: 'danger' },
  forgotten_name: { label: 'Forgotten name', icon: EyeOff, tone: 'danger' },
}

export const WOUND_CAUSES: Record<Schema['WoundCause'], string> = {
  duel: 'a duel of the gods',
  god_war: 'a war of gods',
  creator: 'the Creator',
  avatar_slain: 'the death of its mortal form',
  outer_bargain: 'a bargain with an outer being',
  neglect: 'neglect',
  betrayal: 'betrayal by one in its service',
  mortal_slayer: "a mortal's deed",
}

export const MOTIONS: Record<Schema['CouncilMotion'], Named> = {
  none: { label: 'No decision', icon: CircleDashed, tone: 'muted' },
  against_doomsday: {
    label: 'Stand against the doom',
    icon: Hourglass,
    tone: 'warning',
  },
  joint_blessing: {
    label: 'Bless one another',
    icon: Sparkles,
    tone: 'success',
  },
  condemn_rebel: { label: 'Condemn a rebel', icon: Gavel, tone: 'danger' },
  call_for_peace: { label: 'Call for peace', icon: Handshake, tone: 'success' },
  war_on_foreign_god: {
    label: 'War on a foreign god',
    icon: Swords,
    tone: 'danger',
  },
  divide_worlds: { label: 'Divide the worlds', icon: Map, tone: 'info' },
  outlaw_rite: { label: 'Outlaw a rite', icon: Ban, tone: 'warning' },
  punish_son: { label: 'Punish a son', icon: Gavel, tone: 'danger' },
  bless_hero: { label: 'Bless a hero', icon: Crown, tone: 'gold' },
  holy_world: { label: 'Declare a holy world', icon: Globe, tone: 'gold' },
  cosmic_truce: { label: 'Set a cosmic truce', icon: Shield, tone: 'success' },
  petition_creator: { label: 'Petition the Creator', icon: Eye, tone: 'info' },
  appoint_office: {
    label: 'Appoint a holder to a cosmic office',
    icon: Landmark,
    tone: 'gold',
  },
  reassign_world: {
    label: 'Give a world to another son',
    icon: Orbit,
    tone: 'info',
  },
  outlaw_power: {
    label: "Outlaw a god's powers",
    icon: Link2Off,
    tone: 'warning',
  },
  outlaw_source: {
    label: 'Close a source of power',
    icon: ShieldAlert,
    tone: 'warning',
  },
  admit_member: {
    label: 'Admit a god to the council',
    icon: Users,
    tone: 'success',
  },
  expel_member: {
    label: 'Put a god out of the council',
    icon: Undo2,
    tone: 'danger',
  },
  recognise_god: { label: 'Recognise a new god', icon: Star, tone: 'gold' },
  essence_tithe: {
    label: 'Levy a tithe of essence for a common work',
    icon: Zap,
    tone: 'warning',
  },
  set_council_rules: {
    label: 'Change how the council decides',
    icon: ScrollText,
    tone: 'info',
  },
  regulate_made_minds: {
    label: 'Regulate made minds',
    icon: Brain,
    tone: 'info',
  },
  regulate_powers: { label: 'Regulate powers', icon: Target, tone: 'info' },
  regulate_living_craft: {
    label: 'Regulate living craft',
    icon: Layers,
    tone: 'info',
  },
}

export const VOTING_RULES: Record<Schema['VotingRule'], Named> = {
  unanimity: { label: 'Every voice agrees', icon: Handshake, tone: 'gold' },
  majority: { label: 'Most voices carry it', icon: Users, tone: 'info' },
  weighted_by_standing: {
    label: 'Voices weighed by standing',
    icon: Trophy,
    tone: 'gold',
  },
  weighted_by_rank: {
    label: 'Voices weighed by rank',
    icon: Crown,
    tone: 'verdigris',
  },
}

export const COUNCIL_SEATS: Record<Schema['CouncilSeat'], Named> = {
  by_right: { label: 'Sits by right', icon: Crown, tone: 'gold' },
  invited: { label: 'Invited', icon: Handshake, tone: 'info' },
  by_pact: { label: 'Sits by a pact', icon: Link, tone: 'verdigris' },
  recognised: { label: 'Recognised by the gods', icon: Star, tone: 'success' },
}

export const ESCALATION_STEPS: Record<Schema['EscalationStep'], Named> = {
  censure: { label: 'Censure', icon: Gavel, tone: 'warning' },
  sanction: { label: 'Sanction', icon: BatteryLow, tone: 'warning' },
  exclusion: { label: 'Exclusion from the council', icon: Ban, tone: 'danger' },
  duel: { label: 'A duel', icon: Swords, tone: 'danger' },
  divine_war: { label: 'A war of gods', icon: Flame, tone: 'danger' },
}

export const PUNISHMENTS: Record<Schema['SonPunishment'], string> = {
  chain: 'Chain',
  exile: 'Exile',
  strip_power: 'Strip a power',
  strip_divinity: 'Strip of divinity',
  penance: 'Bind to a penance',
  essence_fine: 'Fine its essence',
}

export const PENANCE_DEEDS: Record<Schema['PenanceDeed'], string> = {
  restore_world: 'Restore a wounded land',
  raise_hero: 'Raise a hero',
  undo_curse: 'Undo a curse',
}

export const LAW_SCOPES: Record<Schema['LawScope'], Named> = {
  cosmos: { label: 'The whole cosmos', icon: Orbit, tone: 'gold' },
  dimension: { label: 'One dimension', icon: Layers, tone: 'info' },
  world: { label: 'One world', icon: Globe, tone: 'info' },
  region: { label: 'One land', icon: Map, tone: 'verdigris' },
}

export const LAW_EXCEPTIONS: Record<Schema['LawException'], string> = {
  none: 'No exception',
  creator_chosen: 'Except the Creator’s chosen',
  author_worshippers: 'Except the author’s faithful',
  heroes: 'Except heroes',
  avatars: 'Except avatars of the gods',
  named_kind: 'Except one named kind of being',
}

export const HUNGERS: Record<Schema['OuterHunger'], Named> = {
  souls: { label: 'Souls', icon: Skull, tone: 'danger' },
  knowledge: { label: 'Knowledge', icon: Brain, tone: 'warning' },
  light: { label: 'Light', icon: Star, tone: 'warning' },
  names: { label: 'Names', icon: ScrollText, tone: 'danger' },
  memories: { label: 'Memories', icon: Moon, tone: 'warning' },
}

export const GAINS: Record<Schema['BargainGain'], string> = {
  essence: 'Essence',
  power: 'A power',
  might: 'Might',
  knowledge: 'Knowledge out of reach',
  longevity: 'A longer span',
}

export const PRICES: Record<Schema['BargainPrice'], string> = {
  world_sanity: 'A world’s sanity',
  domain: 'One of its domains',
  true_name: 'Its true name',
  worshippers: 'The souls of its faithful',
  descendants: 'Its line, bound for years',
}

export const STANDING_AXES = ['awe', 'love', 'fear', 'neglect'] as const

export const AXIS_LABELS: Record<(typeof STANDING_AXES)[number], Named> = {
  awe: { label: 'Awe', icon: Telescope, tone: 'gold' },
  love: { label: 'Love', icon: Sparkles, tone: 'success' },
  fear: { label: 'Fear', icon: Zap, tone: 'danger' },
  neglect: { label: 'Neglect', icon: EyeOff, tone: 'muted' },
}

export const SCHOOLS: Record<Schema['MagicSchool'], string> = {
  elemental_fire: 'Fire',
  elemental_water: 'Water',
  earth: 'Earth',
  storm: 'Storm',
  life: 'Life',
  death: 'Death',
  mind: 'Mind',
  illusion: 'Illusion',
  divination: 'Divination',
  warding: 'Warding',
  binding: 'Binding',
  summoning: 'Summoning',
  blood: 'Blood',
  void: 'Void',
}

export const HELD_LABELS: Record<string, string> = {
  progress: 'progress',
  state: 'state',
  amount: 'aim',
  awe: 'awe',
  love: 'love',
  fear: 'fear',
  neglect: 'neglect',
  severity: 'severity',
  healed: 'healing',
  attention: 'attention',
  watched: 'watch',
  active: 'standing of the ruling',
  until_epoch: 'end',
  strength: 'strength',
  stability: 'stability',
  scope: 'scope',
  exception: 'exception',
  contested: 'contest',
  hunger: 'hunger',
  reach: 'reach',
  fed: 'feeding',
  deeds: 'deeds',
}

export function heldLabel(key: string): string {
  return HELD_LABELS[key] ?? key.replaceAll('_', ' ')
}

export function option<T extends string>(
  table: Record<T, Named | string>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [
      key,
      typeof value === 'string' ? value : (value as Named).label,
    ])
  )
}

export const EXISTENCE_MODES: Record<Schema['ExistenceMode'], string> = {
  concrete: 'Concrete',
  semi_concrete: 'Half concrete',
  conceptual: 'Conceptual',
  reflection: 'A reflection',
  scattered: 'Scattered',
}
