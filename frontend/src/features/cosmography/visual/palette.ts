import { Color, SRGBColorSpace } from 'three'
import { type Palette, type Rgb } from './galaxyForm'

const HEX_SHORT = 3
const CHANNEL = 255
const screen = new Map<string, Rgb>()
const light = new Map<string, Rgb>()

function tokenValue(token: string): string {
  if (typeof document === 'undefined') return ''
  return getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim()
}

function parseHex(value: string): Rgb {
  const digits = value.replace('#', '')
  const full =
    digits.length === HEX_SHORT
      ? digits
          .split('')
          .map((digit) => digit + digit)
          .join('')
      : digits
  const number = Number.parseInt(full.slice(0, 6), 16)
  if (Number.isNaN(number)) return [1, 1, 1]
  return [
    ((number >> 16) & CHANNEL) / CHANNEL,
    ((number >> 8) & CHANNEL) / CHANNEL,
    (number & CHANNEL) / CHANNEL,
  ]
}

export const screenPalette: Palette = (token) => {
  const cached = screen.get(token)
  if (cached) return cached
  const rgb = parseHex(tokenValue(token))
  screen.set(token, rgb)
  return rgb
}

export const scenePalette: Palette = (token) => {
  const cached = light.get(token)
  if (cached) return cached
  const [r, g, b] = screenPalette(token)
  const color = new Color().setRGB(r, g, b, SRGBColorSpace)
  const rgb: Rgb = [color.r, color.g, color.b]
  light.set(token, rgb)
  return rgb
}

function pair(value: number): string {
  return Math.round(Math.min(Math.max(value, 0), 1) * CHANNEL)
    .toString(16)
    .padStart(2, '0')
}

export function mixColor(r: number, g: number, b: number, alpha = 1): string {
  return `#${pair(r)}${pair(g)}${pair(b)}${pair(alpha)}`
}

export function cssColor(token: string, alpha = 1): string {
  const [r, g, b] = screenPalette(token)
  return mixColor(r, g, b, alpha)
}

export function tokenHex(token: string): string {
  return tokenValue(token) || tokenValue('--cosmos-bone')
}
