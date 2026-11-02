export type SkyCalendar = {
  epoch: number
  period: number
  aligned: boolean
  forced: boolean
  nextCycle: number
  opensEpoch: number | null
  closesEpoch: number | null
}

export function skyCalendar(
  epoch: number,
  alignmentPeriod: number,
  alignmentUntil: number | null
): SkyCalendar {
  const period = Math.max(1, alignmentPeriod)
  const cycleAligned = epoch % period === 0
  const forced = alignmentUntil !== null && epoch < alignmentUntil
  const aligned = cycleAligned || forced
  const nextCycle = epoch + (period - (epoch % period))
  let closesEpoch: number | null = null
  if (aligned && period > 1) {
    closesEpoch = Math.max(
      epoch + 1,
      forced && alignmentUntil !== null ? alignmentUntil : epoch + 1
    )
    if (closesEpoch % period === 0) closesEpoch += 1
  }
  return {
    epoch,
    period,
    aligned,
    forced,
    nextCycle,
    opensEpoch: aligned ? null : nextCycle,
    closesEpoch,
  }
}

export function skyCalendarText(calendar: SkyCalendar): string {
  if (calendar.aligned)
    return calendar.closesEpoch !== null
      ? `Slingshot routes open · until the start of epoch ${calendar.closesEpoch}`
      : 'Slingshot routes open'
  return `Slingshot routes closed · open at the start of epoch ${calendar.opensEpoch}`
}
