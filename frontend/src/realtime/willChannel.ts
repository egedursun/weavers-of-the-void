const WILL_CHANNEL_PREFIX = 'divine_will:'

export function willCycleOf(payload: Record<string, unknown>): number | null {
  const channel = payload['channel']
  if (typeof channel !== 'string' || !channel.startsWith(WILL_CHANNEL_PREFIX))
    return null
  const id = Number(channel.slice(WILL_CHANNEL_PREFIX.length))
  return Number.isInteger(id) && id > 0 ? id : null
}
