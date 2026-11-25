export type TeamView = 'queue' | 'team'

const listeners = new Set<(view: TeamView) => void>()

export function onTeamView(listener: (view: TeamView) => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function openTeamView(view: TeamView): void {
  for (const listener of listeners) listener(view)
}
