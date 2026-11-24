import {
  Ban,
  Bird,
  BookX,
  Church,
  CircleSlash,
  Crown,
  Dices,
  DoorClosed,
  DoorOpen,
  Droplet,
  Feather,
  Fence,
  Flame,
  Gem,
  GraduationCap,
  Handshake,
  HeartCrack,
  HeartHandshake,
  Home,
  House,
  Landmark,
  Link,
  MessageSquareWarning,
  PawPrint,
  Pickaxe,
  Rabbit,
  Shovel,
  Skull,
  Snowflake,
  Sprout,
  Store,
  Swords,
  Syringe,
  Unlink,
  UserMinus,
  UserX,
  Wheat,
  Wine,
  Book,
  Droplets,
  FlaskRound,
  Sword,
  Users,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type LoreNamed, TRADITION_TERMS, VALUES, lookup } from './model'

type Schemas = components['schemas']
export type ActKind = NonNullable<Schemas['TraditionCard']['taboo_act']>
export type TraditionEffect = Schemas['TraditionEffectView']
export type RegisterKind = Schemas['RegisterView']['kind']

export const REGISTERS: Record<RegisterKind, LoreNamed> = {
  court: {
    label: 'Court',
    icon: Crown,
    tone: 'gold',
    hint: 'The tongue of rulers: treaties are read in it.',
  },
  common: {
    label: 'Hearth',
    icon: Home,
    tone: 'info',
    hint: 'The tongue spoken at home and in the street.',
  },
  liturgical: {
    label: 'Liturgy',
    icon: Church,
    tone: 'verdigris',
    hint: 'The holy tongue: preachers are heard in it.',
  },
  trade: {
    label: 'Market',
    icon: Store,
    tone: 'warning',
    hint: 'The tongue of bargains: traders use it.',
  },
}

export const TRADITION_EFFECTS: Record<TraditionEffect['effect'], LoreNamed> = {
  cohesion: TRADITION_TERMS.cohesion,
  healing: TRADITION_TERMS.healing,
  bonding: TRADITION_TERMS.bonding,
  satisfaction: TRADITION_TERMS.satisfaction,
  piety: TRADITION_TERMS.piety,
  value: { label: 'A value pressed', icon: Feather, tone: 'info' },
  fertility: TRADITION_TERMS.fertility,
  martial: TRADITION_TERMS.martial,
  placation: TRADITION_TERMS.placation,
  harvest: { label: 'Harvest', icon: Wheat, tone: 'gold' },
  safety: TRADITION_TERMS.hospitality,
  food_saved: TRADITION_TERMS.food_saved,
  rest: TRADITION_TERMS.rest,
  vigil: TRADITION_TERMS.vigil,
  trade: { label: 'Fair trade', icon: Store, tone: 'warning' },
  forage: { label: 'Wild food gathered', icon: Sprout, tone: 'success' },
}

export const ACTS: Record<ActKind, LoreNamed> = {
  execution: { label: 'Execution', icon: UserX, tone: 'danger' },
  mutilation: { label: 'Mutilation', icon: Droplet, tone: 'danger' },
  betrayal: { label: 'Betrayal', icon: Unlink, tone: 'danger' },
  mercy_to_enemy: {
    label: 'Mercy to a foe',
    icon: HeartHandshake,
    tone: 'success',
  },
  sacrifice_of_people: {
    label: 'Sacrifice of people',
    icon: Flame,
    tone: 'danger',
  },
  trade_with_outsiders: {
    label: 'Trade with outsiders',
    icon: Handshake,
    tone: 'warning',
  },
  building_temples: { label: 'Building temples', icon: Landmark, tone: 'gold' },
  burning_books: { label: 'Burning books', icon: BookX, tone: 'danger' },
  conquest: { label: 'Conquest', icon: Sword, tone: 'danger' },
  raiding: { label: 'Raiding', icon: Swords, tone: 'warning' },
  duelling: { label: 'Duelling', icon: Swords, tone: 'warning' },
  ransom: { label: 'Ransom', icon: Link, tone: 'warning' },
  taking_captives: { label: 'Taking captives', icon: Link, tone: 'danger' },
  oathbreaking: { label: 'Oathbreaking', icon: HeartCrack, tone: 'danger' },
  learning: { label: 'Learning', icon: Book, tone: 'info' },
  hospitality: { label: 'Hospitality', icon: DoorOpen, tone: 'success' },
  winter_fighting: { label: 'War in winter', icon: Snowflake, tone: 'info' },
  guest_killing: { label: 'Killing a guest', icon: Ban, tone: 'danger' },
  ritual_scarring: { label: 'Ritual scarring', icon: Droplet, tone: 'muted' },
  killing_kin: { label: 'Killing kin', icon: UserX, tone: 'danger' },
  killing_outsider: {
    label: 'Killing an outsider',
    icon: UserX,
    tone: 'danger',
  },
  killing_in_war: { label: 'Killing in war', icon: Swords, tone: 'warning' },
  killing_captive: { label: 'Killing a captive', icon: Link, tone: 'danger' },
  regicide: { label: 'Killing a ruler', icon: Landmark, tone: 'danger' },
  duel_to_death: { label: 'A duel to the death', icon: Swords, tone: 'danger' },
  revenge_killing: {
    label: 'Killing for revenge',
    icon: Flame,
    tone: 'danger',
  },
  theft: { label: 'Theft', icon: Unlink, tone: 'warning' },
  treason: { label: 'Treason', icon: Unlink, tone: 'danger' },
  cowardice: { label: 'Cowardice', icon: HeartCrack, tone: 'warning' },
  desecration: { label: 'Desecration', icon: BookX, tone: 'danger' },
  bribery: { label: 'Bribery', icon: Handshake, tone: 'warning' },
  suicide: { label: "Taking one's own life", icon: HeartCrack, tone: 'info' },
  torture: { label: 'Torture', icon: Droplet, tone: 'danger' },
  eating_sapients: {
    label: 'Eating thinking beings',
    icon: Droplet,
    tone: 'danger',
  },
  iconoclasm: { label: 'Breaking images', icon: BookX, tone: 'warning' },
  conversion_by_force: {
    label: 'Conversion by force',
    icon: Flame,
    tone: 'danger',
  },
  polygamy: { label: 'Several spouses', icon: HeartHandshake, tone: 'info' },
  incest: { label: 'Marrying close kin', icon: HeartCrack, tone: 'warning' },
  magic_use: { label: 'Using magic', icon: GraduationCap, tone: 'info' },
  blood_magic: { label: 'Blood magic', icon: Droplet, tone: 'danger' },
  void_magic: { label: 'Void magic', icon: Flame, tone: 'danger' },
  necromancy: { label: 'Necromancy', icon: UserX, tone: 'danger' },
  hoarding_in_famine: {
    label: 'Hoarding in famine',
    icon: Link,
    tone: 'warning',
  },
  slavery: { label: 'Keeping slaves', icon: Link, tone: 'danger' },
  adultery: {
    label: 'Love outside a marriage',
    icon: HeartCrack,
    tone: 'warning',
  },
  usury: { label: 'Lending at interest', icon: Landmark, tone: 'warning' },
  infanticide: { label: 'Killing an infant', icon: UserX, tone: 'danger' },
  abandoning_elders: {
    label: 'Leaving the old to fend alone',
    icon: DoorOpen,
    tone: 'danger',
  },
  forced_labour: {
    label: 'Forcing folk to labour unpaid',
    icon: Pickaxe,
    tone: 'danger',
  },
  selling_offices: {
    label: 'Selling the offices of the realm',
    icon: Landmark,
    tone: 'warning',
  },
  poaching: {
    label: 'Poaching game reserved for another',
    icon: Rabbit,
    tone: 'warning',
  },
  enclosing: {
    label: 'Enclosing the common land of the folk',
    icon: Fence,
    tone: 'danger',
  },
  lying: { label: 'Lying', icon: MessageSquareWarning, tone: 'warning' },
  drunkenness: { label: 'Drunkenness', icon: Wine, tone: 'warning' },
  tomb_robbing: {
    label: 'Robbing graves and hoards',
    icon: Shovel,
    tone: 'danger',
  },
  using_charms: { label: 'Using charms', icon: Gem, tone: 'verdigris' },
  feeding_on_hosts: {
    label: 'Feeding on a living host',
    icon: Droplets,
    tone: 'danger',
  },
  killing_sacred_animal: {
    label: 'Killing a sacred animal',
    icon: Bird,
    tone: 'danger',
  },
  fixing_contests: {
    label: 'Fixing a contest',
    icon: Dices,
    tone: 'danger',
  },
  abandoning_the_sick: {
    label: 'Abandoning the sick',
    icon: UserMinus,
    tone: 'danger',
  },
  apologising: { label: 'Apologising', icon: Users, tone: 'success' },
  breaking_hospitality: {
    label: 'Breaking hospitality',
    icon: DoorClosed,
    tone: 'danger',
  },
  cruelty_to_animals: {
    label: 'Cruelty to animals',
    icon: PawPrint,
    tone: 'danger',
  },
  enhancing_contestants: {
    label: 'Enhancing contestants',
    icon: Syringe,
    tone: 'warning',
  },
  laying_curses: { label: 'Laying curses', icon: Skull, tone: 'danger' },
  sheltering_strangers: {
    label: 'Sheltering strangers',
    icon: House,
    tone: 'success',
  },
  poison_wells: { label: 'Poisoning wells', icon: FlaskRound, tone: 'danger' },
}

export function effectLabel(effect: TraditionEffect): string {
  const base = lookup(TRADITION_EFFECTS, effect.effect).label
  if (effect.effect === 'value' && effect.target)
    return `${lookup(VALUES, effect.target).label} pressed`
  if (effect.target)
    return `${base} of the ${effect.target.replaceAll('_', ' ')}`
  return base
}

export function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

export const NONE = 'none'
const NOTHING: LoreNamed = { label: 'None', icon: CircleSlash, tone: 'muted' }

export function withNone(
  table: Record<string, LoreNamed>,
  label = 'None'
): Record<string, LoreNamed> {
  return { [NONE]: { ...NOTHING, label }, ...table }
}
