import {
  Brain,
  Brush,
  CalendarClock,
  CloudFog,
  Flame,
  GalleryHorizontalEnd,
  Gauge,
  Gem,
  Ghost,
  HandHeart,
  Heart,
  HeartPulse,
  type LucideIcon,
  Maximize2,
  Orbit,
  PersonStanding,
  Radio,
  ScanEye,
  Skull,
  Smile,
  Sparkles,
  Star,
  Tornado,
  Zap,
} from 'lucide-react'
import { RARITY_LABEL, type Rarity } from '@/constants/rarity'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { ENTRY_KIND_ICON } from '@/components/domain/entryKindIcon'
import { type EntryRef } from '@/components/layout/entry/entryStack'
import { STATS } from '@/features/pantheon/labels'
import {
  type CardFilters,
  type CardOrder,
  type CharacterCard,
  type CharacterCardStat,
  type CharacterDeckCount,
  type EntityType,
  type NodeKind,
} from './api'

export type CardFrame =
  | 'creator'
  | 'son'
  | 'foreign_god'
  | 'mortal'
  | 'beast'
  | 'spirit'
  | 'outer_being'
  | 'cosmic_being'

export type DeckKey = 'all' | CardFrame

export type Deck = {
  key: DeckKey
  label: string
  icon: LucideIcon
  nodeKind: NodeKind | null
  entityType: EntityType | null
}

export const FRAME_ICON: Record<CardFrame, LucideIcon> = {
  creator: ENTRY_KIND_ICON.creator,
  son: ENTRY_KIND_ICON.son,
  foreign_god: ENTRY_KIND_ICON['foreign-god'],
  mortal: ENTITY_TYPE_ICON.mortal,
  beast: ENTITY_TYPE_ICON.beast,
  spirit: ENTITY_TYPE_ICON.spirit,
  outer_being: ENTITY_TYPE_ICON.outer_being,
  cosmic_being: ENTITY_TYPE_ICON.cosmic_being,
}

export const DECKS: readonly Deck[] = [
  {
    key: 'all',
    label: 'Every card',
    icon: GalleryHorizontalEnd,
    nodeKind: null,
    entityType: null,
  },
  {
    key: 'creator',
    label: 'The Creator',
    icon: FRAME_ICON.creator,
    nodeKind: 'creator',
    entityType: null,
  },
  {
    key: 'son',
    label: 'Children',
    icon: FRAME_ICON.son,
    nodeKind: 'son',
    entityType: null,
  },
  {
    key: 'foreign_god',
    label: 'Foreign gods',
    icon: FRAME_ICON.foreign_god,
    nodeKind: 'foreign_god',
    entityType: null,
  },
  {
    key: 'mortal',
    label: 'Mortals',
    icon: FRAME_ICON.mortal,
    nodeKind: 'entity',
    entityType: 'mortal',
  },
  {
    key: 'beast',
    label: 'Beasts',
    icon: FRAME_ICON.beast,
    nodeKind: 'entity',
    entityType: 'beast',
  },
  {
    key: 'spirit',
    label: 'Spirits',
    icon: FRAME_ICON.spirit,
    nodeKind: 'entity',
    entityType: 'spirit',
  },
  {
    key: 'outer_being',
    label: 'Outer beings',
    icon: FRAME_ICON.outer_being,
    nodeKind: 'entity',
    entityType: 'outer_being',
  },
  {
    key: 'cosmic_being',
    label: 'Cosmic beings',
    icon: FRAME_ICON.cosmic_being,
    nodeKind: 'entity',
    entityType: 'cosmic_being',
  },
]

export const DIVINE_DECKS: ReadonlySet<DeckKey> = new Set([
  'creator',
  'son',
  'foreign_god',
])

export const ORDERS: readonly CardOrder[] = ['power', 'name', 'newest']

export const ORDER_LABEL: Record<CardOrder, string> = {
  power: 'Mightiest first',
  name: 'By name',
  newest: 'Newest first',
}

export type CardState = 'living' | 'fallen' | 'all'

export const CARD_STATES: readonly CardState[] = ['living', 'fallen', 'all']

export const STATE_LABEL: Record<CardState, string> = {
  living: 'Living',
  fallen: 'Fallen',
  all: 'Living and fallen',
}

export function deckOf(key: DeckKey): Deck {
  return DECKS.find((deck) => deck.key === key) ?? DECKS[0]
}

export function deckTotal(counts: CharacterDeckCount[], deck: Deck): number {
  return counts
    .filter(
      (count) =>
        (deck.nodeKind === null || count.node_kind === deck.nodeKind) &&
        (deck.entityType === null || count.entity_type === deck.entityType)
    )
    .reduce((sum, count) => sum + count.total, 0)
}

export function fallenOf(state: CardState): boolean | null {
  if (state === 'all') return null
  return state === 'fallen'
}

export function filtersOf(
  query: string,
  deck: DeckKey,
  rarity: CardFilters['rarity'],
  worldId: number | null,
  state: CardState,
  order: CardOrder
): CardFilters {
  const chosen = deckOf(deck)
  return {
    q: query.trim(),
    nodeKind: chosen.nodeKind,
    entityType: chosen.entityType,
    rarity,
    worldId,
    fallen: fallenOf(state),
    order,
  }
}

const CHARACTER_FRAMES: ReadonlySet<string> = new Set([
  'mortal',
  'beast',
  'spirit',
  'outer_being',
  'cosmic_being',
])

function isFrame(value: string): value is CardFrame {
  return CHARACTER_FRAMES.has(value)
}

export function frameOf(card: CharacterCard): CardFrame {
  if (card.node_kind === 'creator') return 'creator'
  if (card.node_kind === 'son') return 'son'
  if (card.node_kind === 'foreign_god') return 'foreign_god'
  return card.entity_type && isFrame(card.entity_type)
    ? card.entity_type
    : 'mortal'
}

export function kindLabel(
  card: CharacterCard,
  entityTypeLabel: (key: string) => string
): string {
  if (card.node_kind === 'creator') return 'The Creator'
  if (card.node_kind === 'son') return 'Child of the Creator'
  if (card.node_kind === 'foreign_god') return 'Foreign god'
  return card.entity_type ? entityTypeLabel(card.entity_type) : 'Being'
}

export type CardMaterial = Rarity | 'sovereign' | 'obsidian'

export const MATERIAL_LABEL: Record<CardMaterial, string> = {
  common: 'Slate',
  uncommon: 'Verdant bronze',
  rare: 'Silver',
  epic: 'Amethyst',
  legendary: 'Gold',
  mythic: 'Prismatic',
  sovereign: 'White gold',
  obsidian: 'Obsidian',
}

export function materialOf(card: CharacterCard): CardMaterial {
  if (card.node_kind === 'creator') return 'sovereign'
  if (card.node_kind === 'foreign_god' || !card.rarity) return 'obsidian'
  return card.rarity
}

export function isDivine(card: CharacterCard): boolean {
  return DIVINE_DECKS.has(frameOf(card))
}

export function tierLabel(card: CharacterCard): string {
  if (card.rarity) return RARITY_LABEL[card.rarity]
  return card.node_kind === 'creator' ? 'Divine' : 'Foreign'
}

export function typeLine(
  card: CharacterCard,
  entityTypeLabel: (key: string) => string,
  domainLabel: (key: string) => string
): string {
  const parts = [
    kindLabel(card, entityTypeLabel),
    card.subtype,
    ...card.domains.map(domainLabel),
  ]
  return parts.filter((part): part is string => Boolean(part)).join(' · ')
}

export function rarityHint(card: CharacterCard): string {
  if (card.node_kind === 'son') return 'The rarity this child was born with.'
  if (card.power_level !== null)
    return `Read from power level ${card.power_level} against the rarity tiers in the world rules.`
  return card.node_kind === 'creator'
    ? 'The Creator stands above every tier.'
    : 'Foreign gods are measured by their power, not by a tier.'
}

export function rankOf(
  card: CharacterCard
): { value: number; label: string } | null {
  if (card.level !== null) return { value: card.level, label: 'Level' }
  if (card.power_level !== null)
    return { value: card.power_level, label: 'Power level' }
  return null
}

export function epochLine(card: CharacterCard): string {
  if (card.born_epoch === null) return 'Before every epoch'
  if (card.ended_epoch !== null)
    return `Born in epoch ${card.born_epoch}, fell in epoch ${card.ended_epoch}`
  return `Born in epoch ${card.born_epoch}`
}

export type StatGroupKey = 'Body' | 'Mind' | 'Soul' | 'Vitals' | 'Traits'

export type StatMeta = {
  icon: LucideIcon
  abbr: string
  group: StatGroupKey
  effect: string | null
}

const OWN_META: Record<string, Omit<StatMeta, 'effect'>> = {
  sanity: { icon: CloudFog, abbr: 'SAN', group: 'Mind' },
  hp: { icon: Heart, abbr: 'HP', group: 'Vitals' },
  essence: { icon: Sparkles, abbr: 'ESS', group: 'Vitals' },
  existence: { icon: Orbit, abbr: 'EXI', group: 'Vitals' },
  faith: { icon: HandHeart, abbr: 'FAI', group: 'Vitals' },
  fame: { icon: Star, abbr: 'FAM', group: 'Vitals' },
  power: { icon: Zap, abbr: 'POW', group: 'Vitals' },
  intellect: { icon: Brain, abbr: 'INT', group: 'Traits' },
  age: { icon: CalendarClock, abbr: 'AGE', group: 'Traits' },
  lifespan: { icon: HeartPulse, abbr: 'LIF', group: 'Traits' },
  danger: { icon: Skull, abbr: 'DGR', group: 'Traits' },
  renown: { icon: Star, abbr: 'REN', group: 'Traits' },
  terror: { icon: Ghost, abbr: 'TER', group: 'Traits' },
  unrest: { icon: Tornado, abbr: 'UNR', group: 'Traits' },
  size: { icon: Maximize2, abbr: 'SIZ', group: 'Traits' },
  interest: { icon: ScanEye, abbr: 'INR', group: 'Traits' },
  influence: { icon: Radio, abbr: 'INF', group: 'Traits' },
  mood_contentment: { icon: Smile, abbr: 'CON', group: 'Traits' },
  mood_anger: { icon: Flame, abbr: 'ANG', group: 'Traits' },
  mood_interest: { icon: ScanEye, abbr: 'INR', group: 'Traits' },
  mood_loneliness: { icon: CloudFog, abbr: 'LON', group: 'Traits' },
  mood_temperament: { icon: Gauge, abbr: 'TEM', group: 'Traits' },
}

const GOD_META: Record<string, StatMeta> = Object.fromEntries(
  STATS.map((stat) => [
    stat.key,
    {
      icon: stat.icon,
      abbr: stat.abbr,
      group: stat.group,
      effect: stat.effect,
    },
  ])
)

export function statMeta(stat: CharacterCardStat, divine: boolean): StatMeta {
  const god = GOD_META[stat.key]
  const own = OWN_META[stat.key]
  if (god)
    return divine
      ? god
      : { icon: god.icon, abbr: god.abbr, group: 'Traits', effect: null }
  if (own) return { ...own, effect: null }
  return {
    icon: Gem,
    abbr: stat.label.slice(0, 3).toUpperCase(),
    group: 'Traits',
    effect: null,
  }
}

export const STAT_GROUP_ORDER: readonly StatGroupKey[] = [
  'Vitals',
  'Body',
  'Mind',
  'Soul',
  'Traits',
]

export const STAT_GROUP_ICON: Record<StatGroupKey, LucideIcon> = {
  Vitals: HeartPulse,
  Body: PersonStanding,
  Mind: Brain,
  Soul: Brush,
  Traits: Gem,
}

export function statGroups(
  card: CharacterCard
): { group: StatGroupKey; stats: CharacterCardStat[] }[] {
  const divine = isDivine(card)
  return STAT_GROUP_ORDER.map((group) => ({
    group,
    stats: card.stats.filter((stat) => statMeta(stat, divine).group === group),
  })).filter((entry) => entry.stats.length > 0)
}

export function statFill(stat: CharacterCardStat): number | null {
  if (stat.maximum === null || stat.maximum <= 0) return null
  return Math.max(0, Math.min(1, Math.abs(stat.value) / stat.maximum))
}

export function statText(stat: CharacterCardStat): string {
  return stat.maximum === null || stat.key !== 'hp'
    ? String(stat.value)
    : `${stat.value}/${stat.maximum}`
}

export function entryOf(card: CharacterCard): EntryRef {
  if (card.node_kind === 'creator') return { kind: 'creator' }
  if (card.node_kind === 'son') return { kind: 'son', id: String(card.node_id) }
  if (card.node_kind === 'foreign_god')
    return { kind: 'foreign-god', id: String(card.node_id) }
  return { kind: 'entity', id: String(card.node_id) }
}

export function cardFileName(card: CharacterCard, side: CardSide): string {
  const slug = card.name
    .normalize('NFKD')
    .replace(/\p{M}+/gu, '')
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
  return `${slug || 'card'}-${side}.png`
}

export type CardSide = 'front' | 'back'

export const FOOT_VALUES = 4

export function footValues(card: CharacterCard): CharacterCardStat[] {
  const divine = isDivine(card)
  const vitals = card.stats.filter(
    (stat) => statMeta(stat, divine).group === 'Vitals'
  )
  const picked: CharacterCardStat[] = []
  for (const stat of [...card.headline, ...vitals, ...card.stats]) {
    if (picked.length === FOOT_VALUES) break
    if (!picked.some((line) => line.key === stat.key)) picked.push(stat)
  }
  return picked
}
