import { describe, expect, it } from 'vitest'
import { cn, getDisplayNameInitials } from './utils'

describe('cn', () => {
  it('keeps a text role size next to a text color', () => {
    expect(cn('text-body', 'text-muted-foreground')).toBe(
      'text-body text-muted-foreground'
    )
    expect(cn('text-display', 'text-foreground')).toBe(
      'text-display text-foreground'
    )
  })

  it('lets a later text role replace an earlier one', () => {
    expect(cn('text-body', 'text-caption')).toBe('text-caption')
    expect(cn('text-sm', 'text-control')).toBe('text-control')
  })

  it('merges control heights like any spacing utility', () => {
    expect(cn('h-control-md', 'h-control-sm')).toBe('h-control-sm')
  })
})

describe('getDisplayNameInitials', () => {
  it('takes the first letters of the first and last word', () => {
    expect(getDisplayNameInitials('Ithren the Unbowed')).toBe('IU')
  })

  it('takes two letters of a single word', () => {
    expect(getDisplayNameInitials('orvael')).toBe('OR')
  })

  it('falls back to a question mark', () => {
    expect(getDisplayNameInitials('   ')).toBe('?')
  })
})

describe('class merging knows every theme token', () => {
  it('matches the spacing and text tokens declared in the theme', async () => {
    const { default: theme } = await import('@/styles/theme.css?raw')
    const { SPACING_TOKENS, TEXT_ROLES } = await import('./utils')
    const spacing = [...theme.matchAll(/--spacing-([a-z0-9-]+):/g)].map(
      (match) => match[1]
    )
    const text = [...theme.matchAll(/--text-([a-z]+):/g)].map(
      (match) => match[1]
    )
    expect([...new Set(spacing)].sort()).toEqual([...SPACING_TOKENS].sort())
    expect([...new Set(text)].sort()).toEqual([...TEXT_ROLES].sort())
  })
})
