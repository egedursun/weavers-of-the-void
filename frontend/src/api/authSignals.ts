export type AuthSignal =
  'signed_out' | 'password_change_required' | 'setup_required'

const listeners = new Set<(signal: AuthSignal) => void>()

export function onAuthSignal(
  listener: (signal: AuthSignal) => void
): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function raiseAuthSignal(signal: AuthSignal): void {
  for (const listener of listeners) listener(signal)
}
