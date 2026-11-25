const PRESENCE_CHANNEL_PREFIX = 'presence:'

export function presenceExchangeOf(
  payload: Record<string, unknown>
): number | null {
  const channel = payload['channel']
  if (
    typeof channel !== 'string' ||
    !channel.startsWith(PRESENCE_CHANNEL_PREFIX)
  )
    return null
  const id = Number(channel.slice(PRESENCE_CHANNEL_PREFIX.length))
  return Number.isInteger(id) && id > 0 ? id : null
}
