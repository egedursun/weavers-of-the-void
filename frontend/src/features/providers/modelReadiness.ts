import { type WorldState } from '@/features/overview/api'
import { ROLE_LOOK } from './providerLook'
import { type ModelRole } from './types'

export const MODELS_OFF_REASON =
  'The language model is turned off on this server.'

export function missingRoles(state: WorldState | undefined): ModelRole[] {
  if (!state?.llm_enabled) return []
  return state.role_models
    .filter((entry) => entry.model === '')
    .map((entry) => entry.role)
}

export function rolesNamed(roles: readonly ModelRole[]): string {
  const names = roles.map((role) => ROLE_LOOK[role].label.toLowerCase())
  if (names.length < 2) return names.join('')
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

export function modelBlock(
  state: WorldState | undefined,
  role: ModelRole
): string | null {
  if (!state) return null
  if (!state.llm_enabled) return MODELS_OFF_REASON
  return missingRoles(state).includes(role)
    ? `No model is set for ${rolesNamed([role])}; choose one under Models in the workspace settings.`
    : null
}
