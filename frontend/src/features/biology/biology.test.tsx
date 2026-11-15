import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BiologySection } from './BiologySection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PEOPLE = { id: 12, kind: 'entity' as const, name: 'Orrin' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Duneford' }
const EFFECTS = {
  food_need_pct: 130,
  fertility_pct: 144,
  death_pct: 120,
  disease_pct: 130,
  morale_loss_pct: 50,
  fire_harm_pct: 100,
  storm_harm_pct: 150,
  breathes: true,
  drinks: true,
  ages: true,
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('biology', () => {
  beforeEach(() => resetApi())

  it('shows the variants of a body and gives it a new one', async () => {
    serveBase()
    onApi('GET', '/api/biology/of/40', {
      node: TOWN,
      holder: PEOPLE,
      variants: ['aerial', 'hive'],
      body_variants: ['aerial'],
      effects: EFFECTS,
      derived: EFFECTS,
      leanings: [
        { bias: 'groupthink', shift: 50, damped: false },
        { bias: 'overconfidence', shift: 0, damped: true },
      ],
      body: {
        bleeds: false,
        heals: true,
        infects: true,
        material: true,
        tissue: 'crystal',
      },
      seeded: true,
      updated_epoch: 5,
      locked: ['variants'],
      absent_reason: null,
    })
    onApi('POST', '/api/actions/biology_variant:add', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BiologySection nodeId={40} />)
    await expect
      .element(screen.getByText('Harm from storms: 150%, its variants 150%'))
      .toBeVisible()
    await expect.element(screen.getByText('Groupthink: +50')).toBeVisible()
    await expect.element(screen.getByText('Bleeds: no')).toBeVisible()
    await expect.element(screen.getByText('Tissue: Crystal')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Hive' }))
      .toHaveAttribute('aria-pressed', 'true')
    await screen.getByRole('button', { name: 'Undead' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/biology_variant:add'))
      .toHaveLength(1)
    onApi('POST', '/api/actions/biology:edit', ACCEPTED_ACTION)
    await screen
      .getByRole('button', { name: 'Let the sons reshape its variants' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/biology:edit'))
      .toHaveLength(1)
  })

  it('keeps the controls on screen for a thing of no kind and says why', async () => {
    serveBase()
    onApi('GET', '/api/biology/of/1', {
      node: { id: 1, kind: 'creator', name: 'The Creator' },
      holder: null,
      variants: [],
      body_variants: [],
      effects: null,
      derived: null,
      leanings: [],
      body: null,
      seeded: false,
      updated_epoch: null,
      locked: [],
      absent_reason: 'It belongs to no people or species.',
    })
    const { screen } = await renderApp(<BiologySection nodeId={1} />)
    await expect
      .element(screen.getByText('No biology reaches this'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Undead' }))
      .toBeDisabled()
    await expect
      .element(
        screen.getByRole('button', { name: 'Return it to what its body shows' })
      )
      .toBeDisabled()
  })
})
