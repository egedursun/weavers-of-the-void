import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { cssColor, tokenHex } from './palette'

const HEX = /^#[0-9a-f]{6}$/

function raw(token: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim()
}

function channels(hex: string): number[] {
  return [1, 3, 5].map((at) => Number.parseInt(hex.slice(at, at + 2), 16))
}

describe('scene palette', () => {
  it('turns a modern colour token into a hex colour three.js can read', () => {
    expect(raw('--success')).not.toBe('')
    expect(raw('--success').startsWith('#')).toBe(false)
    const green = tokenHex('--success')
    expect(green).toMatch(HEX)
    const [r, g, b] = channels(green)
    expect(g).toBeGreaterThan(r)
    expect(g).toBeGreaterThan(b)
    expect(cssColor('--success').slice(0, 7)).toBe(green)
  })

  it('keeps a hex token as it is', () => {
    expect(tokenHex('--cosmos-void')).toBe(raw('--cosmos-void').toLowerCase())
  })
})
