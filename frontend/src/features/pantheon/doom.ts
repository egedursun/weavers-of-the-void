export function doomTone(
  value: number,
  threshold: number | undefined,
  first: number | undefined,
  second: number | undefined
): 'default' | 'warning' | 'destructive' {
  if (threshold === undefined || threshold <= 0) return 'default'
  const ratio = (value / threshold) * 100
  if (second !== undefined && ratio >= second) return 'destructive'
  if (first !== undefined && ratio >= first) return 'warning'
  return 'default'
}
