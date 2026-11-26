import { type components } from '@/api/generated/schema'

type Schemas = components['schemas']

export type ProvidersView = Schemas['ProvidersView']
export type ProviderKindView = Schemas['ProviderKindView']
export type ProviderConnection = Schemas['ProviderConnectionView']
export type ChainEntry = Schemas['ChainEntryView']
export type RoleView = Schemas['ModelRoleView']
export type LoginView = Schemas['ProviderLoginView']
export type ProviderKind = Schemas['ProviderKind']
export type ProviderFamily = Schemas['ProviderFamily']
export type ModelRole = Schemas['ModelRole']
export type LoginState = Schemas['LoginState']
export type ConnectionDraft = Schemas['ConnectionCreate']
export type ConnectionChange = Schemas['ConnectionEdit']
export type ChainLink = Schemas['ChainLinkBody']

export type ProviderScope = { workspaceId: number } | 'server'
