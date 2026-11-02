export function councilFrequencyText(
  every: number | null | undefined,
  fallback: number | undefined
): string {
  const interval = every ?? fallback
  if (interval === undefined)
    return 'Sons debate an agenda and vote on a motion.'
  if (interval <= 0)
    return 'Sons debate an agenda and vote on a motion; it convenes only when you call it.'
  return `Sons debate an agenda and vote on a motion; it convenes on its own every ${interval} epochs (change it in Settings, Game).`
}
