import {
  ACCEPTED_ACTION,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { KinSection } from './MortalSections'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const ME = { id: 5, kind: 'entity' as const, name: 'Iska' }
const SPOUSE = { id: 6, kind: 'entity' as const, name: 'Oru' }

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 5, name: 'Iska', type: 'mortal', world_id: 1 },
    { kind: 'entity', id: 6, name: 'Oru', type: 'mortal', world_id: 1 },
  ])
  onApi('GET', '/api/mortals/5/family', { root: 5, people: [] })
  onApi('GET', '/api/mortals/5/profile', {
    mortal: ME,
    sex: 'bearer',
    life_stage: 'adult',
    fertility: 50,
    health: 80,
    stress: 10,
    wealth: 20,
    renown: 5,
    honour: 50,
    infamy: 0,
    legitimacy: null,
    education: 10,
    polity: null,
    loyalty_liege: 50,
    loyalty_community: 50,
    loyalty_god: 50,
    career: null,
    profession: null,
    last_break: null,
    last_break_epoch: null,
    cause_of_death: null,
    death_place: null,
    social_class: null,
    held: [],
    marriages: [
      {
        id: 9,
        spouse: SPOUSE,
        form: 'plural',
        purpose: 'alliance',
        treaty: null,
        start_epoch: 3,
        end_epoch: null,
        cause_end: null,
        forced: false,
      },
    ],
    kin: [],
    equipment: [],
    stress_threshold: 70,
  })
}

describe('marriages by the axes of union', () => {
  beforeEach(() => resetApi())

  it('shows a marriage by its form and purpose', async () => {
    serve()
    const { screen } = await renderApp(<KinSection mortalId={5} />)
    await expect
      .element(screen.getByText('One partner with several').first())
      .toBeVisible()
    await expect
      .element(screen.getByText('To bind allies').first())
      .toBeVisible()
  })

  it('weds by the form and purpose the god picks', async () => {
    serve()
    onApi('POST', '/api/actions/kin:marry', ACCEPTED_ACTION)
    const { screen } = await renderApp(<KinSection mortalId={5} />)
    await screen.getByRole('button', { name: 'Adjust' }).last().click()
    await screen.getByRole('combobox', { name: 'What it is for' }).click()
    await screen.getByRole('option', { name: 'For love' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Wed' }))
      .toHaveAttribute('aria-disabled', 'true')
  })
})
