import { onApi, renderApp, resetApi } from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LoreForge } from './LoreForge'
import { FORGE_KIND, FORGE_KINDS } from './forgeModel'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 12 },
    worlds: [],
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

describe('lore forge layout', () => {
  beforeEach(resetApi)

  it.each(FORGE_KINDS)(
    'gives every %s forge control the same labelled form row',
    async (kind) => {
      serve()
      const { screen } = await renderApp(<LoreForge kind={kind} />)
      const label = `Forge a new ${FORGE_KIND[kind].label.toLowerCase()}`
      await screen.getByRole('button', { name: label }).click()
      const dialog = screen.getByRole('dialog')
      await expect.element(dialog).toBeVisible()
      const controls = [
        ...dialog.getByRole('combobox').elements(),
        ...dialog.getByRole('spinbutton').elements(),
        ...dialog.getByRole('textbox').elements(),
      ]
      expect(controls.length).toBeGreaterThan(0)
      const loose = controls.filter(
        (control) => control.closest('[data-domain="form-row"]') === null
      )
      expect(
        loose.map((control) => control.getAttribute('aria-label'))
      ).toEqual([])
    }
  )
})
