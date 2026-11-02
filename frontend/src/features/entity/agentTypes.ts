const AGENT_TYPES = new Set([
  'mortal',
  'people',
  'settlement',
  'faction',
  'cult',
])

export function agentTypeOf(entityType: string): boolean {
  return AGENT_TYPES.has(entityType)
}
