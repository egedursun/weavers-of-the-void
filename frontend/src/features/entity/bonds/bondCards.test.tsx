import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BondsCard, CirclesCard, ContestsCard } from './cards'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const OSWIN = { id: 501, name: 'Oswin', kind: 'entity', type: 'mortal' }
const HILD = { id: 502, name: 'Hild', kind: 'entity', type: 'mortal' }

const EMPTY = {
  node_id: 501,
  name: 'Oswin',
  applies: true,
  mortal: true,
  place: false,
  reason: null,
  bonds_held: false,
  passions_held: false,
  bonds: [],
  passions: [],
  circles: [],
  ranks: [],
  order: [],
  contests: [],
  persuasions: [],
  circle_kinds: [
    { key: 'study_circle', label: 'Study circle' },
    { key: 'sport_club', label: 'Sport club' },
    { key: 'gaming_circle', label: 'Gaming circle' },
  ],
  passion_kinds: [],
  passion_sources: [],
  appeals: [],
  aims: [],
  contest_kinds: [
    { key: 'riddle_game', label: 'Riddle game' },
    { key: 'race', label: 'Race' },
    { key: 'craft_contest', label: 'Craft contest' },
  ],
  stakes: [
    { key: 'honour', label: 'Honour' },
    { key: 'land', label: 'Land' },
    { key: 'freedom', label: 'Freedom' },
  ],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [
    { ...OSWIN, world_id: 1 },
    { ...HILD, world_id: 1 },
  ])
}

describe('bond cards', () => {
  beforeEach(resetApi)

  it('labels the sworn, betrothed and foster bonds and begins a bond with the right body', async () => {
    serve()
    onApi('POST', '/api/actions/tie:set', ACCEPTED_ACTION)
    const view = {
      ...EMPTY,
      bonds: [
        {
          id: 7,
          subject: HILD,
          friendship: 40,
          romance: 10,
          familiarity: 60,
          rivalry: 0,
          their_friendship: 35,
          their_romance: 5,
          kinds: ['betrothed', 'sworn_kin', 'foster'],
          affair: false,
          affair_known: false,
          since_epoch: 44,
          last_epoch: 50,
          held: [],
        },
      ],
    } as never
    const { screen } = await renderApp(
      <BondsCard view={view} blocked={null} hold={false} />
    )
    await expect.element(screen.getByText('Betrothed')).toBeVisible()
    await expect.element(screen.getByText('Sworn kin')).toBeVisible()
    await expect.element(screen.getByText('Foster kin')).toBeVisible()
    expect(screen.container.textContent).not.toContain('sworn_kin')
    const begin = screen.getByRole('button', { name: 'Begin', exact: true })
    await expect
      .element(begin)
      .toHaveAccessibleDescription('Pick a mortal first.')
    await screen.getByRole('combobox', { name: 'With' }).click()
    await screen.getByRole('option', { name: /Hild/ }).click()
    await begin.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/tie:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/tie:set')[0].body).toEqual({
      holder_id: 501,
      subject_id: 502,
      familiarity: 20,
      friendship: 10,
      mutual: true,
      hold: false,
    })
  })

  it('shows the empty bonds note and keeps Begin disabled with its reason while the world is locked', async () => {
    serve()
    const { screen } = await renderApp(
      <BondsCard view={EMPTY as never} blocked='The epoch is running.' hold />
    )
    await expect.element(screen.getByText(/No bonds yet\./)).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Begin', exact: true }))
      .toHaveAccessibleDescription('The epoch is running.')
  })

  it('shows a sport club by its label and gathers a gaming circle at a place', async () => {
    serve()
    onApi('POST', '/api/actions/circle:found', ACCEPTED_ACTION)
    const view = {
      ...EMPTY,
      node_id: 30,
      place: true,
      circles: [
        {
          circle: {
            id: 80,
            name: 'The Fen Runners',
            kind: 'entity',
            type: 'faction',
          },
          kind: 'sport_club',
          label: 'Sport club',
          taste_key: null,
          axis: null,
          meeting_place: null,
          ideology: null,
          founded_epoch: 47,
          members: [OSWIN, HILD],
          leader: OSWIN,
          held: [],
        },
      ],
    } as never
    const { screen } = await renderApp(
      <CirclesCard view={view} blocked={null} hold={false} place />
    )
    await expect.element(screen.getByText('Sport club · 2')).toBeVisible()
    await expect.element(screen.getByText('since epoch 47')).toBeVisible()
    await screen.getByRole('combobox', { name: 'Kind of circle' }).click()
    await screen.getByRole('option', { name: 'Gaming circle' }).click()
    await screen.getByRole('button', { name: 'Gather', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/circle:found'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/circle:found')[0].body).toEqual({
      place_id: 30,
      kind: 'gaming_circle',
      member_ids: [],
    })
  })

  it('says a mortal belongs to no circle', async () => {
    serve()
    const { screen } = await renderApp(
      <CirclesCard
        view={EMPTY as never}
        blocked={null}
        hold={false}
        place={false}
      />
    )
    await expect
      .element(screen.getByText('Not a member of any circle.'))
      .toBeVisible()
  })

  it('shows a race for land and stages a craft contest for freedom', async () => {
    serve()
    onApi('POST', '/api/actions/contest:hold', ACCEPTED_ACTION)
    const view = {
      ...EMPTY,
      contests: [
        {
          id: 12,
          kind: 'race',
          label: 'Race',
          stake: 'land',
          stake_label: 'Land',
          challenger: OSWIN,
          defender: HILD,
          judge: null,
          stake_node: null,
          place: null,
          wager: 0,
          rounds: [[6, 4]],
          outcome: 'challenger',
          famous: false,
          work: null,
          epoch: 49,
          note: null,
        },
      ],
    } as never
    const { screen } = await renderApp(
      <ContestsCard view={view} blocked={null} hold={false} mortal />
    )
    await expect.element(screen.getByText('Race for land')).toBeVisible()
    await expect.element(screen.getByText('Round 1: 6–4')).toBeVisible()
    const stage = screen.getByRole('button', { name: 'Stage', exact: true })
    await expect
      .element(stage)
      .toHaveAccessibleDescription('Pick an opponent first.')
    await screen.getByRole('combobox', { name: 'Against' }).click()
    await screen.getByRole('option', { name: /Hild/ }).click()
    await screen.getByRole('combobox', { name: 'Contest' }).click()
    await screen.getByRole('option', { name: 'Craft contest' }).click()
    await screen.getByRole('combobox', { name: 'Stake' }).click()
    await screen.getByRole('option', { name: 'Freedom' }).click()
    await stage.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/contest:hold'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/contest:hold')[0].body).toEqual({
      challenger_id: 501,
      defender_id: 502,
      kind: 'craft_contest',
      stake: 'freedom',
      wager: 0,
    })
  })
})
