export const REASON_MAX = 500
const ONE_SHOT_MS = 10_000

let oneShot: { text: string; at: number } | null = null
export function giveReason(text: string): void {
  const trimmed = text.trim().slice(0, REASON_MAX)
  oneShot = trimmed ? { text: trimmed, at: Date.now() } : null
}

export function takeReason(now = Date.now()): string | null {
  const given =
    oneShot !== null && now - oneShot.at <= ONE_SHOT_MS ? oneShot.text : null
  oneShot = null
  return given
}
