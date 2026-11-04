export type RangeShade = {
  peak: number
  cells: ReadonlyMap<number, number>
}

export const RANGE_BANDS = [
  { key: 'trace', label: 'A trace of them', share: 0.2 },
  { key: 'scattered', label: 'Scattered herds', share: 0.4 },
  { key: 'common', label: 'Common', share: 0.6 },
  { key: 'abundant', label: 'Abundant', share: 0.8 },
  { key: 'teeming', label: 'Teeming', share: Number.POSITIVE_INFINITY },
] as const

const BASE_ALPHA = 0.16
const ALPHA_STEP = 0.11

export function rangeBand(abundance: number, peak: number): string | null {
  if (abundance <= 0 || peak <= 0) return null
  const share = abundance / peak
  return RANGE_BANDS.find((band) => share < band.share)?.key ?? 'teeming'
}

export function rangeAlpha(band: string): number {
  const index = RANGE_BANDS.findIndex((item) => item.key === band)
  return BASE_ALPHA + Math.max(0, index) * ALPHA_STEP
}

export function rangeLabel(band: string): string {
  return RANGE_BANDS.find((item) => item.key === band)?.label ?? band
}

export function rangeShade(
  cells: readonly { region: { id: number }; abundance: number }[],
  peak: number
): RangeShade {
  return {
    peak,
    cells: new Map(cells.map((cell) => [cell.region.id, cell.abundance])),
  }
}

export function speciesRangeSearch(worldId: number | null, speciesId: number) {
  return worldId === null
    ? { species: speciesId }
    : { world: worldId, species: speciesId }
}
