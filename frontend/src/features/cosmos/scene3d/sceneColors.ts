import { Color } from 'three'

const cache = new Map<string, Color>()

export function tokenColor(token: string): Color {
  const cached = cache.get(token)
  if (cached) return cached
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim()
  const color = new Color()
  if (value) color.setStyle(value)
  cache.set(token, color)
  return color
}

export function tokenString(token: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim()
}

export function paletteColors(palette: string[], fallback: string): Color[] {
  const colors: Color[] = []
  for (let index = 0; index < 10; index += 1) {
    const value = palette[index] ?? palette[palette.length - 1]
    const color = new Color()
    if (value) color.setStyle(value)
    else color.copy(tokenColor(fallback))
    colors.push(color)
  }
  return colors
}
