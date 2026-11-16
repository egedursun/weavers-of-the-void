import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LivingSection } from './LivingSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const BREEDER = { id: 30, kind: 'entity' as const, name: 'Ila Venn' }
const KIND = { id: 41, kind: 'entity' as const, name: 'Marsh striders' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function line(overrides: Record<string, unknown> = {}) {
  return {
    id: 9,
    name: 'The long-legged line',
    method: 'selective_breeding',
    outcome: 'as_meant',
    stability: 64,
    generation: 3,
    drift_pct: 12,
    fertility: 'breeds_true',
    metabolism: 'feeding',
    owner: BREEDER,
    maker: BREEDER,
    species: KIND,
    drifted_from_id: null,
    drifted_from_name: null,
    licensed: false,
    escaped: false,
    founded_epoch: 2,
    living_count: 5,
    locked: [],
    traits: [
      { id: 1, trait: 'speed', strength: 30, side_effect: false, locked: [] },
    ],
    sources: [{ id: 2, organism: KIND, locked: [] }],
    ...overrides,
  }
}

function view(overrides: Record<string, unknown> = {}) {
  return {
    node: BREEDER,
    alive_reason: null,
    clone_reason: null,
    profile: null,
    lines: [line()],
    symbionts: [],
    banks: [],
    clone_of: [],
    clones: [],
    stances: null,
    every_line: [{ id: 9, name: 'The long-legged line' }],
    ...overrides,
  }
}

describe('living craft', () => {
  beforeEach(() => resetApi())

  it('shows a line with its traits and lets it loose', async () => {
    serveBase()
    onApi('GET', '/api/living/of/30', view())
    onApi('POST', '/api/actions/line:escape', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LivingSection nodeId={30} />)
    await expect
      .element(screen.getByText('The long-legged line').first())
      .toBeVisible()
    await expect.element(screen.getByText('Speed +30')).toBeVisible()
    await screen.getByRole('button', { name: 'Let it loose' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/line:escape'))
      .toHaveLength(1)
  })

  it('keeps the hold-in control on screen, disabled until the line is loose', async () => {
    serveBase()
    onApi('GET', '/api/living/of/30', view())
    const { screen } = await renderApp(<LivingSection nodeId={30} />)
    await expect
      .element(
        screen.getByRole('button', { name: 'Hunt it down and hold it in' })
      )
      .toBeDisabled()
  })

  it('shows a living thing and ends its life', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/living/of/30',
      view({
        lines: [],
        profile: {
          line_id: 9,
          line_name: 'The long-legged line',
          metabolism: 'feeding',
          feed_commodity: 'fodder',
          feed_per_season: 1,
          growth_stage: 'prime',
          size_pct: 100,
          regeneration: 30,
          health: 88,
          temperament: 'placid',
          bonded_to: BREEDER,
          bond: 60,
          fertility: 'breeds_true',
          lifespan_years: 40,
          age_seasons: 24,
          designed_by: BREEDER,
          planted_epoch: 1,
          locked: [],
        },
      })
    )
    onApi('POST', '/api/actions/living:end', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LivingSection nodeId={30} />)
    await expect
      .element(screen.getByText('In its prime, health 88'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'End its life' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/living:end'))
      .toHaveLength(1)
  })

  it('says why a world cannot carry a living profile and keeps the control disabled', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/living/of/4',
      view({
        node: WORLD,
        lines: [],
        alive_reason: 'Only a thing of the world can carry a living profile.',
        clone_reason: 'Only a mortal with a body can be cloned.',
      })
    )
    const { screen } = await renderApp(<LivingSection nodeId={4} />)
    await expect
      .element(screen.getByRole('button', { name: 'Give it life' }))
      .toBeDisabled()
    await expect
      .element(
        screen.getByRole('button', { name: 'Grow a clone of this body' })
      )
      .toBeDisabled()
  })
})
