import { type PlayerHints } from '@/features/pantheon/api'

export function sonHints(
  hints: PlayerHints | undefined,
  name: string
): string[] {
  if (!hints) return []
  const lines: string[] = []
  if (hints.sons_waiting.includes(name))
    lines.push('He has not acted this epoch yet.')
  if (hints.sons_without_orders.includes(name))
    lines.push('He has no standing order; give him one to steer his turn.')
  if (hints.sleeping_sons.includes(name))
    lines.push('He sleeps; a blessing of life can hasten his return.')
  if (hints.creator.rebel_sons.includes(name))
    lines.push('He is in rebellion: suppress it or forgive him.')
  const fading = hints.creator.fading_sons.find((son) => son.name === name)
  if (fading)
    lines.push(
      `He is being forgotten (existence ${fading.existence}); remember him or win him worshippers.`
    )
  return lines
}
