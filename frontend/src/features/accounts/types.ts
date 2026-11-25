import { type components, type paths } from '@/api/generated/schema'

type Schemas = components['schemas']

export {
  accountStatusValues,
  avatarToneValues,
  serverRoleValues,
} from '@/api/generated/schema'

export type ServerRole = Schemas['ServerRole']
export type AccountStatus = Schemas['AccountStatus']
export type AvatarTone = Schemas['AvatarTone']
export type Account =
  paths['/api/accounts']['get']['responses'][200]['content']['application/json'][number]
export type AuthState = Schemas['AuthState']
export type SessionView = Schemas['SessionView']
export type IssuedPassword = Schemas['IssuedPassword']
export type SetupDraft = Schemas['SetupRequest']
export type ProfileDraft = Schemas['ProfilePatch']
export type AccountDraft = Schemas['AccountCreate']
