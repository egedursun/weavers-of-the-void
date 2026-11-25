import { type components } from '@/api/generated/schema'

type Schemas = components['schemas']

export type PresenceGuise = Schemas['PresenceGuise']
export type PresenceRecord = Schemas['PresenceRecord']
export type PresenceExchangeStatus = Schemas['PresenceExchangeStatus']
export type SpeakerGroup = Schemas['SpeakerGroup']

export type SpeakerSummary = Schemas['PresenceSpeakerItem']
export type SpeakerCard = Schemas['PresenceSpeakerCard']
export type SpeakerView = Schemas['PresenceSpeakerView']
export type PresenceSessionSummary = Schemas['PresenceSessionSummary']
export type PresenceSessionView = Schemas['PresenceSessionView']
export type PresenceExchange = Schemas['PresenceExchangeView']
export type PresenceEvent = Schemas['PresenceEventView']

export type AudienceSpeaker = {
  name: string
  cover: string | null
  deathEpoch: number | null
  deathLine: string
}
