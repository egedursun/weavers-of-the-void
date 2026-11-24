import { renderApp } from '@/test-utils/fakeApi'
import { describe, expect, it, vi } from 'vitest'
import { MapToolbar } from './MapToolbar'

const BASE = {
  mode: 'terrain' as const,
  onMode: () => undefined,
  overlays: {
    roads: true,
    trade: true,
    outbreaks: true,
    military: true,
    faith: true,
    lore: true,
    beasts: true,
    ties: true,
    wars: true,
    events: true,
    labels: true,
    fog: true,
  },
  onOverlay: () => undefined,
  worlds: [],
  worldId: 1,
  onWorld: () => undefined,
  legendOpen: false,
  onLegend: () => undefined,
  noteMode: false,
  onNoteMode: () => undefined,
  past: false,
  findable: [],
  onFind: () => undefined,
  onZoom: () => undefined,
  onRegenerate: () => undefined,
  regenerating: false,
  mobile: false,
}

describe('map depth', () => {
  it('switches the depth and disables the layers of the surface below', async () => {
    const onDepth = vi.fn()
    const { screen } = await renderApp(
      <MapToolbar
        {...BASE}
        depth='cavern_upper'
        depths={[{ stratum: 'cavern_upper', cells: 3, depth: 2 }]}
        onDepth={onDepth}
      />
    )
    await expect
      .element(screen.getByRole('group', { name: 'Map depth' }))
      .toBeVisible()
    await screen.getByRole('radio', { name: 'Surface' }).click()
    expect(onDepth).toHaveBeenCalledWith(null)
    await expect
      .element(screen.getByRole('radio', { name: 'Soil', exact: true }))
      .toHaveAttribute('title', 'Reads the soil and fields of the surface')
  })

  it('says why the depth cannot be chosen on a world with nothing below', async () => {
    const { screen } = await renderApp(
      <MapToolbar
        {...BASE}
        depth={null}
        depths={[]}
        onDepth={() => undefined}
      />
    )
    await expect
      .element(
        screen.getByText(
          'No world below: this world has no strata beneath its regions'
        )
      )
      .toBeVisible()
  })
})
