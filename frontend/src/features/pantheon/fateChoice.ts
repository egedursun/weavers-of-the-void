export const FATE_CHOOSES = 'fate'

export function worldIdOf(value: string): number | null {
  return value === FATE_CHOOSES ? null : Number(value)
}
