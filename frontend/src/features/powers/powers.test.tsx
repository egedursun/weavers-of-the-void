import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HiddenTruthsSection } from './HiddenTruthsSection'
import { MagicSystemsSection } from './MagicSystemsSection'
import { PowersSection } from './PowersSection'
import { SourcesSection } from './SourcesSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SEER = { id: 30, kind: 'entity' as const, name: 'Ila Venn' }
const SON = { id: 2, kind: 'son' as const, name: 'Oren' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }
const TOWN = { id: 12, kind: 'entity' as const, name: 'Harrowmere' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function power(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    holder: SEER,
    system_id: 3,
    system_name: 'The old way',
    source_id: 5,
    source_name: 'The deep well',
    technique: 'perceive',
    form: 'time',
    range_km: 0,
    duration_days: 0,
    on_others: true,
    strength: 4,
    control: 55,
    origin: 'granted',
    state: 'latent',
    visibility: 'subtle',
    strain: 3,
    strain_cap: 30,
    granted_by: SON,
    item: null,
    uses: 2,
    gained_epoch: 3,
    last_used_epoch: 5,
    locked: [],
    restrictions: [
      {
        id: 1,
        kind: 'spoken_vow',
        ref: null,
        detail: 'never before the sun',
        strength_gain_pct: 20,
        broken: false,
        locked: [],
      },
    ],
    triggers: [{ id: 2, trigger: 'stress', locked: [] }],
    spans: [],
    ...overrides,
  }
}

describe('powers, sources, systems and hidden truths', () => {
  beforeEach(() => resetApi())

  it('shows a latent granted power and wakes it', async () => {
    serveBase()
    onApi('GET', '/api/powers/of/30', {
      node: SEER,
      powers: [power()],
      granted: [],
      registry: [],
      attitude: null,
      bloodline_rule: null,
      sources: [{ id: 5, name: 'The deep well' }],
      systems: [{ id: 3, name: 'The old way' }],
      grant_cost: 10,
    })
    onApi('POST', '/api/actions/power:awaken', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PowersSection nodeId={30} />)
    await expect.element(screen.getByText('Perceive time')).toBeVisible()
    await expect.element(screen.getByText(/never before the sun/)).toBeVisible()
    await screen.getByRole('button', { name: 'Wake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/power:awaken'))
      .toHaveLength(1)
  })

  it('keeps the grant control on screen, disabled until a god is chosen', async () => {
    serveBase()
    onApi('GET', '/api/powers/of/30', {
      node: SEER,
      powers: [],
      granted: [],
      registry: [],
      attitude: null,
      bloodline_rule: null,
      sources: [],
      systems: [],
      grant_cost: 10,
    })
    const { screen } = await renderApp(<PowersSection nodeId={30} />)
    await expect.element(screen.getByText('No powers')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Have the god grant it' }))
      .toBeDisabled()
  })

  it('shows a land run thin of its source', async () => {
    serveBase()
    onApi('GET', '/api/sources/of/12', {
      node: TOWN,
      sources: [],
      densities: [
        {
          id: 4,
          source_id: 5,
          source_name: 'The deep well',
          density: 8,
          base_density: 60,
          renewal_pct: 10,
          last_drawn_epoch: 5,
          depleted: true,
          locked: [],
        },
      ],
      knowledge: [],
      laws: [],
      stances: [],
      power_stance: null,
      every_source: [{ id: 5, name: 'The deep well' }],
    })
    const { screen } = await renderApp(<SourcesSection nodeId={12} />)
    await expect
      .element(screen.getByText('The deep well here: density 8 of 60'))
      .toBeVisible()
  })

  it('shapes a system of power for a world', async () => {
    serveBase()
    onApi('GET', '/api/magic-systems/of/4', {
      node: WORLD,
      systems: [],
      every_system: [],
      every_source: [],
    })
    onApi('POST', '/api/actions/magic_system:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MagicSystemsSection nodeId={4} />)
    await screen.getByLabelText('Name of the system').fill('The tide way')
    await screen.getByRole('button', { name: 'Shape it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/magic_system:create'))
      .toHaveLength(1)
  })

  it('reveals a hidden truth to a town', async () => {
    serveBase()
    onApi('GET', '/api/truths/of/30', {
      node: SEER,
      about: [
        {
          id: 9,
          title: 'one who walks unseen',
          description: '',
          subject: SEER,
          kind: 'presence',
          hidden_from: 'everyone',
          scope: null,
          strength: 60,
          methods: ['by_oath'],
          sanity_cost: 0,
          revealed: false,
          founded_epoch: 2,
          tended_epoch: 5,
          locked: [],
          keepers: [],
          seekers: [],
          knowledge: [],
          breaches: [],
        },
      ],
      kept: [],
      sought: [],
      known_here: [],
      methods: ['by_oath', 'by_law'],
    })
    const { screen } = await renderApp(<HiddenTruthsSection nodeId={30} />)
    await expect.element(screen.getByText('one who walks unseen')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Reveal it to them' }))
      .toBeDisabled()
  })
})
