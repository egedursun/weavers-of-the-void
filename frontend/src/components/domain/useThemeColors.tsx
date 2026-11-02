import { useEffect, useState } from 'react'

export const THEME_COLOR_NAMES = [
  'background',
  'foreground',
  'card',
  'muted',
  'muted-foreground',
  'border',
  'primary',
  'destructive',
  'success',
  'warning',
  'accent',
  'chart-1',
  'chart-2',
  'chart-3',
  'chart-4',
  'chart-5',
  'rarity-common',
  'rarity-uncommon',
  'rarity-rare',
  'rarity-epic',
  'rarity-legendary',
  'rarity-mythic',
  'brand-gold',
  'brand-verdigris',
  'brand-ink',
] as const

export type ThemeColorName = (typeof THEME_COLOR_NAMES)[number]

export type ThemeColors = Record<ThemeColorName, string> & {
  fontBody: string
  fontDisplay: string
  dark: boolean
}

const FALLBACK_COLOR = 'gray'

const DISPLAY_FONT = "'Cinzel', 'Iowan Old Style', Georgia, serif"

export function readThemeColors(): ThemeColors {
  const root = document.documentElement
  const style = getComputedStyle(root)
  const entries = THEME_COLOR_NAMES.map((name) => {
    const value = style.getPropertyValue(`--${name}`).trim()
    return [name, value || FALLBACK_COLOR] as const
  })
  return {
    ...(Object.fromEntries(entries) as Record<ThemeColorName, string>),
    fontBody: getComputedStyle(document.body).fontFamily || 'sans-serif',
    fontDisplay: DISPLAY_FONT,
    dark: root.classList.contains('dark'),
  }
}

export function useThemeColors(): ThemeColors {
  const [tokens, setTokens] = useState<ThemeColors>(readThemeColors)
  useEffect(() => {
    const observer = new MutationObserver(() => setTokens(readThemeColors()))
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'style', 'data-theme'],
    })
    return () => observer.disconnect()
  }, [])
  return tokens
}

const HEX_PREFIX = '#'
const resolved = new Map<string, string>()

export function toHex(color: string): string {
  const known = resolved.get(color)
  if (known) return known
  const canvas = document.createElement('canvas')
  canvas.width = 1
  canvas.height = 1
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context) return color
  context.fillStyle = color
  context.fillRect(0, 0, 1, 1)
  const [red, green, blue] = context.getImageData(0, 0, 1, 1).data
  const hex =
    HEX_PREFIX +
    [red, green, blue]
      .map((channel) => channel.toString(16).padStart(2, '0'))
      .join('')
  resolved.set(color, hex)
  return hex
}
