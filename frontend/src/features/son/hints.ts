import { type PlayerHints } from '@/features/pantheon/api'

export function sonHints(
  hints: PlayerHints | undefined,
  name: string
): string[] {
  if (!hints) return []
  const lines: string[] = []
  if (hints.sons_waiting.includes(name))
    lines.push('They have not acted this epoch yet.')
  if (hints.sons_without_orders.includes(name))
    lines.push(
      'They have no standing order; give them one to steer their turn.'
    )
  if (hints.sleeping_sons.includes(name))
    lines.push('They sleep; a blessing of life can hasten their return.')
  if (hints.creator.rebel_sons.includes(name))
    lines.push('They are in rebellion: suppress it or forgive them.')
  const fading = hints.creator.fading_sons.find((son) => son.name === name)
  if (fading)
    lines.push(
      `They are being forgotten (existence ${fading.existence}); remember them or win them worshippers.`
    )
  return lines
}
