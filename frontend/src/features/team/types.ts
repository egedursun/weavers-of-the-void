import { type components } from '@/api/generated/schema'

type Schemas = components['schemas']

export type TeamView = Schemas['TeamView']
export type PresentView = Schemas['PresentView']
export type AuthorView = Schemas['AuthorView']
export type QueuedActView = Schemas['QueuedActView']
export type QueuedActStatus = Schemas['QueuedActStatus']
export type QueuedActSource = Schemas['QueuedActSource']
export type CanonProposalView = Schemas['CanonProposalView']
export type ProposalStatus = Schemas['ProposalStatus']
export type CanonTouch = Schemas['CanonTouch']
export type EditConflictChange = Schemas['EditConflictChange']
export type ConflictChangeView = Schemas['ConflictChangeView']
export type NodeRevisionView = Schemas['NodeRevisionView']
