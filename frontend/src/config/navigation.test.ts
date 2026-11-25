import { createRouter } from '@tanstack/react-router'
import { routeTree } from '@/routeTree.gen'
import { describe, expect, it } from 'vitest'
import {
  allNavItems,
  isNavItemActive,
  navItem,
  SHORTCUT_KEYS,
  shortcutItems,
} from './navigation'

describe('navigation', () => {
  it('has unique ids and unique shortcuts', () => {
    const ids = allNavItems().map((item) => item.id)
    expect(new Set(ids).size).toBe(ids.length)
    const shortcuts = shortcutItems().map((item) => item.shortcut)
    expect(new Set(shortcuts).size).toBe(shortcuts.length)
    expect(shortcuts).toEqual(SHORTCUT_KEYS)
  })

  it('numbers the sidebar top to bottom without jumps', () => {
    const inSidebarOrder = allNavItems()
      .map((item) => item.shortcut)
      .filter((shortcut) => shortcut !== undefined)
    expect(inSidebarOrder).toEqual(SHORTCUT_KEYS)
  })

  it('points every item at a real route', () => {
    const router = createRouter({
      routeTree,
      context: { queryClient: undefined as never },
    })
    const paths = Object.keys(router.routesByPath)
    for (const item of allNavItems()) expect(paths).toContain(item.to)
  })

  it('marks sections active by their own path and its children', () => {
    expect(isNavItemActive('/overview', navItem('overview'))).toBe(true)
    expect(isNavItemActive('/', navItem('overview'))).toBe(false)
    expect(isNavItemActive('/atlas', navItem('overview'))).toBe(false)
    expect(
      isNavItemActive('/settings/world-rules', navItem('settings-world-rules'))
    ).toBe(true)
  })

  it('throws for an unknown item', () => {
    expect(() => navItem('nowhere')).toThrow()
  })
})
