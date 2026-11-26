import { formatDecimal, formatInteger } from './format'

const SECONDS_PER_MINUTE = 60
const SECONDS_PER_HOUR = 3600
const SECONDS_PER_DAY = 86_400
const MILLISECONDS = 1000
const KIBIBYTE = 1024
const MEBIBYTE = KIBIBYTE * KIBIBYTE
const GIBIBYTE = MEBIBYTE * KIBIBYTE
const PAD = 2

export function formatDuration(seconds: number): string {
  const total = Math.max(0, seconds)
  if (total >= SECONDS_PER_DAY) {
    const days = Math.floor(total / SECONDS_PER_DAY)
    const hours = Math.floor((total % SECONDS_PER_DAY) / SECONDS_PER_HOUR)
    return `${days} d ${hours} h`
  }
  if (total >= SECONDS_PER_HOUR) {
    const hours = Math.floor(total / SECONDS_PER_HOUR)
    const minutes = Math.floor((total % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE)
    return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`
  }
  if (total >= SECONDS_PER_MINUTE) {
    const minutes = Math.floor(total / SECONDS_PER_MINUTE)
    const rest = Math.floor(total % SECONDS_PER_MINUTE)
    return rest === 0 ? `${minutes} min` : `${minutes} min ${rest} s`
  }
  return `${formatDecimal(total, 1)} s`
}

export function formatMilliseconds(milliseconds: number): string {
  return formatDuration(milliseconds / MILLISECONDS)
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(total / SECONDS_PER_MINUTE)
  const rest = String(total % SECONDS_PER_MINUTE).padStart(PAD, '0')
  return `${minutes}:${rest}`
}

export function formatBytes(bytes: number): string {
  if (bytes >= GIBIBYTE) return `${formatDecimal(bytes / GIBIBYTE, 1)} GB`
  if (bytes >= MEBIBYTE) return `${formatDecimal(bytes / MEBIBYTE, 1)} MB`
  if (bytes >= KIBIBYTE) return `${formatInteger(bytes / KIBIBYTE)} KB`
  return `${formatInteger(bytes)} B`
}

export function agree(
  count: number,
  singular: string,
  many = `${singular}s`
): string {
  return count === 1 ? singular : many
}

export function plural(
  count: number,
  singular: string,
  many = `${singular}s`
): string {
  return `${count.toLocaleString('en-US')} ${agree(count, singular, many)}`
}
