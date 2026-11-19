import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FactionSection } from './Faction'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const FACTION = {
  id: 12,
  name: 'Saltreach Guild',
  kind: 'merchant_guild',
  scale: 'company',
  treasury: 140,
  cohesion: 55,
  secrecy: 0,
  armed: false,
  reputation: 60,
  strength: 30,
  wealth: 70,
  sway: 50,
  influence_over: { '3': 40 },
  influence_names: { '3': 'The Salt Kingdom' },
  cohort_share: { merchant: 20 },
  home_id: 30,
  home: 'Saltreach',
  leader_id: 41,
  leader: 'Ama the Weigher',
  outlawed: false,
  chartered_by_id: null,
  chartered_by: null,
  monopoly: 'luxuries',
  employer_id: null,
  employer: null,
  contract_id: null,
  pay: 0,
  loyalty: 50,
  unpaid_epochs: 0,
  locked: [],
  goals: [
    {
      id: 5,
      kind: 'lower_taxes',
      target_id: 3,
      target: 'The Salt Kingdom',
      target_key: null,
      priority: 80,
      progress: 30,
      since_epoch: 50,
      set_by_player: false,
      locked: [],
    },
  ],
  members: [
    {
      id: 41,
      name: 'Ama the Weigher',
      rank: 'leader',
      joined_epoch: 49,
      alive: true,
    },
  ],
  actions: [
    {
      id: 1,
      epoch: 51,
      kind: 'lobby',
      target_id: 44,
      target: 'Chancellor Oro',
      success: true,
      amount: 10,
      note: null,
    },
    {
      id: 2,
      epoch: 51,
      kind: 'strike',
      target_id: 30,
      target: 'Saltreach',
      success: true,
      amount: 0,
      note: null,
    },
  ],
  realm_id: 3,
  balance: [
    { id: 12, name: 'Saltreach Guild', kind: 'merchant_guild', share: 70 },
    { id: 13, name: 'Temple Council', kind: 'priesthood', share: 30 },
  ],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

describe('faction section', () => {
  beforeEach(resetApi)

  it('shows the agenda, the power balance and the deeds in plain words and outlaws the faction', async () => {
    serve()
    onApi('GET', '/api/factions/12', FACTION)
    onApi('POST', '/api/actions/faction:outlaw', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FactionSection factionId={12} />)
    await expect
      .element(screen.getByText('Trade association').first())
      .toBeVisible()
    await expect.element(screen.getByText('Lower taxes')).toBeVisible()
    await expect.element(screen.getByText('Lobbied')).toBeVisible()
    await expect.element(screen.getByText('Struck')).toBeVisible()
    await expect.element(screen.getByText('70%')).toBeVisible()
    expect(screen.getByText('lower_taxes').elements()).toHaveLength(0)
    await screen.getByRole('switch', { name: 'Outlawed' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/faction:outlaw'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/faction:outlaw')[0].body).toEqual({
      faction_id: 12,
      outlawed: true,
    })
  })

  it('strikes a goal from the agenda', async () => {
    serve()
    onApi('GET', '/api/factions/12', FACTION)
    onApi('POST', '/api/actions/faction:goal', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FactionSection factionId={12} />)
    await screen.getByRole('button', { name: 'Strike' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/faction:goal'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/faction:goal')[0].body).toMatchObject({
      faction_id: 12,
      goal_id: 5,
      remove: true,
    })
  })
})
