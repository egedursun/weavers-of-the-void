import {
  BookMarked,
  Crown,
  EyeOff,
  Ghost,
  type LucideIcon,
  Moon,
  Orbit,
  PawPrint,
  Sparkles,
  UserRound,
  UsersRound,
  Wind,
} from 'lucide-react'
import {
  deathCauseValues,
  entityStatusValues,
  sonDeathCauseValues,
} from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { wordOf } from '@/features/entity/affairs/labels'
import {
  FOREIGN_STATUS_LABEL,
  SON_STATUS_LABEL,
} from '@/features/pantheon/labels'
import {
  type AudienceSpeaker,
  type PresenceExchangeStatus,
  type PresenceGuise,
  type PresenceRecord,
  type SpeakerCard,
  type SpeakerGroup,
} from './types'

export type GuiseLook = {
  label: string
  icon: LucideIcon
  tone: KpiTone
  line: string
  heard: string
}

export const GUISE_ORDER: readonly PresenceGuise[] = [
  'creator',
  'unnamed_power',
  'dream_voice',
  'ordinary',
]

export const GUISE_LOOK: Record<PresenceGuise, GuiseLook> = {
  creator: {
    label: 'Creator',
    icon: Crown,
    tone: 'gold',
    line: 'You speak as its Creator, revealed.',
    heard: 'It knows it speaks with its Creator.',
  },
  unnamed_power: {
    label: 'Unnamed power',
    icon: Sparkles,
    tone: 'verdigris',
    line: 'A divine presence speaks, but it cannot tell which one.',
    heard: 'It hears a divine presence it cannot name.',
  },
  dream_voice: {
    label: 'Dream voice',
    icon: Moon,
    tone: 'info',
    line: 'A voice comes to it in a dream; it may doubt it is real.',
    heard: 'It hears a voice in a dream and may doubt it.',
  },
  ordinary: {
    label: 'Ordinary voice',
    icon: UserRound,
    tone: 'muted',
    line: 'An ordinary person of its own world speaks; nothing divine.',
    heard: 'It hears an ordinary person of its own world.',
  },
}

export type RecordLook = {
  label: string
  icon: LucideIcon
  tone: KpiTone
  line: string
  keeps: readonly string[]
}

export const RECORD_ORDER: readonly PresenceRecord[] = [
  'on_record',
  'off_record',
]

export const RECORD_LOOK: Record<PresenceRecord, RecordLook> = {
  on_record: {
    label: 'On the record',
    icon: BookMarked,
    tone: 'gold',
    line: 'The audience becomes part of history.',
    keeps: [
      'Every exchange is kept for good, in its entry, the lore book and the Codex.',
      'It remembers the audience afterwards, as it heard it.',
      'It may act through its own tools, spending its own action points.',
    ],
  },
  off_record: {
    label: 'Off the record',
    icon: EyeOff,
    tone: 'muted',
    line: 'Nothing of it stays once the audience ends.',
    keeps: [
      'Nothing is kept once you begin anew or summon it again.',
      'It remembers nothing of what was said.',
      'It reads the world but never acts.',
    ],
  },
}

export type GroupLook = {
  label: string
  icon: LucideIcon
}

export const GROUP_ORDER: readonly SpeakerGroup[] = [
  'sons',
  'foreign_gods',
  'mortals',
  'spirits',
  'beings',
  'beasts',
]

export const GROUP_LOOK: Record<SpeakerGroup, GroupLook> = {
  sons: { label: 'Sons', icon: Crown },
  foreign_gods: { label: 'Foreign gods', icon: Ghost },
  mortals: { label: 'Mortals', icon: UsersRound },
  spirits: { label: 'Spirits', icon: Wind },
  beings: { label: 'Beings', icon: Orbit },
  beasts: { label: 'Beasts', icon: PawPrint },
}

export const EXCHANGE_STATUS_LABEL: Record<PresenceExchangeStatus, string> = {
  running: 'Answering',
  done: 'Answered',
  failed: 'Failed',
  cancelled: 'Stopped',
}

export const DEAD_SEAL = 'Summoned from death'

export const NO_MODEL =
  'No language model is switched on, so no one can answer. Turn one on in the settings first.'

export function statusLabel(card: SpeakerCard): string {
  if (card.son_status) return SON_STATUS_LABEL[card.son_status]
  if (card.foreign_god_status)
    return FOREIGN_STATUS_LABEL[card.foreign_god_status]
  if (card.entity_status) return wordOf(entityStatusValues, card.entity_status)
  return card.dead ? 'Dead' : 'Living'
}

function causeOf(card: SpeakerCard): string {
  if (card.son_death_cause)
    return wordOf(sonDeathCauseValues, card.son_death_cause)
  if (card.mortal_death_cause)
    return wordOf(deathCauseValues, card.mortal_death_cause)
  return ''
}

export function deathText(card: SpeakerCard): string {
  const when =
    card.death_epoch === null
      ? 'It died'
      : `It died in epoch ${String(card.death_epoch)}`
  const cause = causeOf(card)
  const first = cause ? `${when}: ${cause.toLowerCase()}.` : `${when}.`
  return card.death_line.trim() ? `${first} ${card.death_line.trim()}` : first
}

export function audienceSpeaker(card: SpeakerCard): AudienceSpeaker {
  return {
    name: card.name,
    cover: card.cover,
    deathEpoch: card.death_epoch,
    deathLine: card.dead ? deathText(card) : '',
  }
}
