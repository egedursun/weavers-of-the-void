import { type components } from '@/api/generated/schema'
import {
  type PresenceEvent,
  type PresenceExchange,
  type PresenceSessionSummary,
  type PresenceSessionView,
  type SpeakerCard,
  type SpeakerSummary,
  type SpeakerView,
} from './types'

const AT = '2026-11-25T10:00:00Z'

type SpeakerPage = components['schemas']['PresenceSpeakerPage']

let nextEvent = 500

export function presenceEvent(
  kind: PresenceEvent['kind'],
  payload: Record<string, unknown>,
  tool = ''
): PresenceEvent {
  nextEvent += 1
  return {
    id: nextEvent,
    ordinal: nextEvent,
    kind,
    tool,
    payload,
    created_at: AT,
  }
}

export function speakerSummary(
  change: Partial<SpeakerSummary> = {}
): SpeakerSummary {
  return {
    node_id: 7,
    name: 'Ithren',
    kind: 'son',
    entity_type: null,
    group: 'sons',
    dead: false,
    cover: null,
    open_session_id: null,
    ...change,
  }
}

export function speakerPage(speakers: SpeakerSummary[]): SpeakerPage {
  return {
    speakers,
    total: speakers.length,
    offset: 0,
    limit: 24,
    has_more: false,
  }
}

export function presenceSession(
  change: Partial<PresenceSessionSummary> = {}
): PresenceSessionSummary {
  return {
    id: 3,
    node_id: 7,
    guise: 'creator',
    record: 'on_record',
    status: 'open',
    dead_when_summoned: false,
    title: '',
    opened_epoch: 4,
    opened_at: AT,
    closed_at: null,
    exchange_count: 0,
    ...change,
  }
}

export function speakerCard(change: Partial<SpeakerCard> = {}): SpeakerCard {
  return {
    node_id: 7,
    name: 'Ithren',
    epithet: 'Keeper of the first law',
    kind: 'son',
    entity_type: null,
    group: 'sons',
    son_status: 'active',
    foreign_god_status: null,
    entity_status: null,
    place_name: '',
    world_name: 'Aster',
    patron_name: '',
    faith: 40,
    languages: ['Common tongue'],
    dead: false,
    death_epoch: null,
    son_death_cause: null,
    mortal_death_cause: null,
    death_line: '',
    cover: null,
    can_act: true,
    ...change,
  }
}

export function speakerView(change: Partial<SpeakerView> = {}): SpeakerView {
  return {
    card: speakerCard(),
    open_session: null,
    past_sessions: [],
    model_enabled: true,
    remembered_exchanges: 10,
    ...change,
  }
}

export function presenceExchange(
  change: Partial<PresenceExchange> = {}
): PresenceExchange {
  return {
    id: 1,
    session_id: 3,
    ordinal: 1,
    epoch: 4,
    player_text: 'What do you seek?',
    reply_text: 'Only your word, Creator.',
    remember_text: 'The Creator asked what I seek.',
    status: 'done',
    error: '',
    model: 'claude-haiku-5-5',
    input_tokens: 900,
    output_tokens: 120,
    steps: 1,
    started_at: AT,
    finished_at: AT,
    events: [],
    ...change,
  }
}

export function sessionView(
  change: Partial<PresenceSessionView> = {}
): PresenceSessionView {
  return {
    session: presenceSession(),
    exchanges: [],
    memory_boundary: 1,
    remembered_exchanges: 10,
    running_exchange_id: null,
    ...change,
  }
}
