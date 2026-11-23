import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FestivalYearSection } from './FestivalYearSection'

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
  onApi('GET', '/api/custom-kinds', { kinds: [] })
}

function season(position: number, name: string, warmth: string) {
  return {
    id: position + 1,
    position,
    name,
    temperature_shift: 0,
    rain_shift: 0,
    growth: 50,
    travel: 50,
    campaign: 50,
    share_pct: 50,
    warmth,
    water: 'even',
    edited: false,
  }
}

const YEAR = {
  people_id: 9,
  world_id: 2,
  seasons: [season(0, 'Bloom', 'warmest'), season(1, 'Hush', 'coldest')],
  festivals: [
    {
      id: 21,
      name: 'The Gathering of Lights',
      kind: 'festival',
      calendar_slot: 'midsummer',
      season_position: 0,
      in_season: true,
      slot_open: true,
      slot_reason: null,
      held: ['season_position'],
    },
    {
      id: 22,
      name: 'The Silent Count',
      kind: 'rite_of_passage',
      calendar_slot: 'market',
      season_position: null,
      in_season: false,
      slot_open: false,
      slot_reason: 'no market or fair is held there',
      held: [],
    },
  ],
}

describe('year of festivals', () => {
  beforeEach(resetApi)

  it('places festivals on the seasons and moves one to another season', async () => {
    serve()
    onApi('GET', '/api/peoples/9/festival-year', YEAR)
    onApi('POST', '/api/actions/lore:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <FestivalYearSection peopleId={9} readOnlyReason={null} />
    )
    await expect
      .element(screen.getByText('The Gathering of Lights'))
      .toBeVisible()
    await expect.element(screen.getByText('1. Bloom').first()).toBeVisible()
    await expect
      .element(screen.getByText('Its time comes this epoch'))
      .toBeVisible()
    await expect.element(screen.getByText('season held')).toBeVisible()
    await expect
      .element(screen.getByText('At the height of summer').first())
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'Its time does not come: no market or fair is held there'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'The year of 2 seasons' }))
      .toBeVisible()
    await screen
      .getByRole('combobox', { name: 'Season it is kept in' })
      .first()
      .click()
    await screen.getByRole('option', { name: '2. Hush' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/lore:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/lore:edit')[0].body).toEqual({
      entity_id: 21,
      values: { season_position: 1 },
      release: [],
    })
  })

  it('keeps the controls disabled with the reason when the world is read only', async () => {
    serve()
    onApi('GET', '/api/peoples/9/festival-year', YEAR)
    const { screen } = await renderApp(
      <FestivalYearSection
        peopleId={9}
        readOnlyReason='This world is only being viewed'
      />
    )
    await expect
      .element(screen.getByText('This world is only being viewed'))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('combobox', { name: 'Season it is kept in' }).first()
      )
      .toBeDisabled()
  })

  it('shows an empty year when the people keeps no festival', async () => {
    serve()
    onApi('GET', '/api/peoples/9/festival-year', { ...YEAR, festivals: [] })
    const { screen } = await renderApp(
      <FestivalYearSection peopleId={9} readOnlyReason={null} />
    )
    await expect.element(screen.getByText('No festival yet')).toBeVisible()
  })
})
