import { type components, type paths } from '@/api/generated/schema'

type Schemas = components['schemas']

export {
  permissionValues,
  universeRoleValues,
  workspaceKindValues,
  workspaceRoleValues,
} from '@/api/generated/schema'

export type WorkspaceKind = Schemas['WorkspaceKind']
export type WorkspaceRole = Schemas['WorkspaceRole']
export type UniverseRole = Schemas['UniverseRole']
export type Permission = Schemas['Permission']
export type Workspace = Schemas['WorkspaceView']
export type Member =
  paths['/api/workspaces/{workspace_id}/members']['get']['responses'][200]['content']['application/json'][number]
export type MemberDraft = Schemas['MemberAdd']
export type MemberAdded = Schemas['MemberAdded']
export type AccessPerson = Schemas['PersonAccess']
export type PermissionRow = Schemas['PermissionRow']
export type UniverseAccess = Schemas['UniverseAccessView']
export type TunedRole = 'editor' | 'viewer'
