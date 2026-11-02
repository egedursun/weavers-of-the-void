type Band = { label: string; text: string }

export function attitudeBand(
  stance: number,
  warAt: number | undefined,
  friendAt: number | undefined
): Band {
  if (warAt !== undefined && stance <= -warAt)
    return {
      label: 'Hostile',
      text: 'An enemy: sons may go to war against this god.',
    }
  if (stance < 0)
    return {
      label: 'Suspicious',
      text: 'Wary: may steal worshippers or raze temples.',
    }
  if (stance === 0)
    return { label: 'Neutral', text: 'Neither helps nor harms the pantheon.' }
  if (friendAt !== undefined && stance >= friendAt)
    return {
      label: 'Friend',
      text: 'A friend: adds prosperity to the worshippers.',
    }
  return { label: 'Close', text: 'Warming to the pantheon, not yet a friend.' }
}
