import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RegionWorksPanel } from '@/features/entity/environment/RegionWorksPanel'
import { SeasonCalendarPanel } from './SeasonCalendarPanel'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SEASONS = {
  world_id: 1,
  climate: null,
  axial_tilt: 20,
  year_length_days: 360,
  season_count: 2,
  day_length_hours: 40,
  moon_count: 2,
  tidal_strength: 60,
  seasons: [
    {
      id: 11,
      position: 0,
      name: 'Thaw',
      temperature_shift: 0,
      rain_shift: 10,
      growth: 70,
      travel: 50,
      campaign: 50,
      share_pct: 60,
      warmth: 'warming',
      water: 'deluge',
      edited: true,
    },
    {
      id: 12,
      position: 1,
      name: 'Frost',
      temperature_shift: -30,
      rain_shift: 0,
      growth: 10,
      travel: 30,
      campaign: 20,
      share_pct: 40,
      warmth: 'coldest',
      water: 'arid',
      edited: false,
    },
  ],
  seasons_max: 8,
  onsets: [
    {
      id: 31,
      year: 12,
      season_position: 1,
      onset: 'failed',
      locked: true,
      by_node_id: null,
    },
  ],
  calendars: [],
  notable_years: [
    {
      id: 5,
      epoch: 2,
      year: 80,
      kind: 'hunger',
      weather: null,
      name: 'the Bitter Year',
      magnitude: 70,
      region_id: 3,
      legend_id: null,
    },
  ],
  astronomy_records: [],
} as never

const CALENDAR = {
  world_id: 1,
  calendar_locked: ['moon_count'],
  day_length_hours: 40,
  long_days: true,
  long_day_hours: 30,
  sleep_customs: 1,
  calendars: [
    {
      knowledge_id: 7,
      name: 'Star Count',
      anchor_year: 0,
      keepers: 2,
      holy_days: [
        {
          index: 0,
          name: 'Fast of the Bitter Year',
          year: 80,
          season_position: 1,
          notable_year_id: 5,
          tradition_id: 21,
          tradition_name: 'The Fast of the Bitter Year',
        },
      ],
    },
  ],
  traditions: [
    {
      id: 21,
      name: 'The Fast of the Bitter Year',
      kind: 'fast',
      season_position: 1,
      calendar_id: 7,
      calendar_name: 'Star Count',
      in_season: true,
      held: [],
    },
    {
      id: 22,
      name: 'The Midday Rest of Vale',
      kind: 'rest_custom',
      season_position: 0,
      calendar_id: null,
      calendar_name: null,
      in_season: false,
      held: ['season_position'],
    },
  ],
}

const GROUND = {
  region_id: 3,
  ley_lines: [
    {
      id: 4,
      other_region_id: 6,
      other_region_name: 'Far Dunes',
      strength: 40,
      severed: false,
      severed_until_epoch: null,
      forged: false,
    },
  ],
  forced_weather: [
    {
      id: 9,
      kind: 'storm',
      label: 'Storm',
      from_epoch: 3,
      until_epoch: 4,
      season_position: null,
      son_id: null,
    },
  ],
} as never

const WORKS = {
  region_id: 3,
  roads: 1,
  bridges: 2,
  harbours: 0,
  irrigation: 1,
  irrigation_pct: 13,
  rainfall: 44,
  rain_lost_to_clearing: 6,
  cleared: 30,
  settlements: [
    {
      settlement_id: 8,
      name: 'Ford',
      bridges: 2,
      irrigation: 1,
      harbour: false,
      locked: ['bridges'],
    },
  ],
  ley_works: [
    {
      structure_id: 15,
      name: 'Spire',
      attuned: false,
      on_ley_line: true,
      at_nexus: false,
      function: 40,
      locked: [],
    },
  ],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 3 },
  })
}

describe('season calendar', () => {
  beforeEach(resetApi)

  it('shows the festival year and edits holy days, seasons and remembered years', async () => {
    serve()
    onApi('GET', '/api/worlds/1/calendar', CALENDAR)
    onApi('POST', '/api/actions/calendar:holy_day_remove', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/seasons:release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/seasons:calendar_release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/year:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SeasonCalendarPanel data={SEASONS} />)
    await expect
      .element(screen.getByText('The Midday Rest of Vale'))
      .toBeVisible()
    await expect
      .element(screen.getByText(/drifted off its season/))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Remembered years' }).click()
    await screen.getByRole('button', { name: 'Forget' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/year:delete'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Remove' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/calendar:holy_day_remove'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/calendar:holy_day_remove')[0].body
    ).toEqual({ knowledge_id: 7, index: 0 })
    await screen.getByRole('button', { name: 'Seasons and moons' }).click()
    await screen.getByRole('button', { name: 'Release the hold' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/seasons:release'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Moons and tides' }).click()
    await screen
      .getByRole('button', { name: 'Let the world decide again' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/seasons:calendar_release'))
      .toHaveLength(1)
  })

  it('sets works, ley ties, line strength and held weather of a region', async () => {
    serve()
    onApi('GET', '/api/regions/3/works', WORKS)
    onApi('POST', '/api/actions/settlement:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/ley:work', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/ley:dissolve', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <RegionWorksPanel regionId={3} ground={GROUND} />
    )
    await expect.element(screen.getByText('+13%')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Let the world decide again' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/settlement:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/settlement:edit')[0].body).toEqual({
      settlement_id: 8,
      values: {},
      release: ['bridges'],
    })
    await screen.getByRole('switch', { name: 'Channels the ley' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/ley:work'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/ley:work')[0].body).toEqual({
      structure_id: 15,
      values: { attuned: true },
      release: [],
    })
    await screen.getByRole('button', { name: 'Lines and weather' }).click()
    await screen.getByRole('button', { name: 'Unmake' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/ley:dissolve'))
      .toHaveLength(1)
  })

  it('moves, releases, clears and holds the onset of a season in a year', async () => {
    serve()
    onApi('GET', '/api/worlds/1/calendar', CALENDAR)
    onApi('POST', '/api/actions/seasons:onset', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/seasons:onset_release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/seasons:onset_clear', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SeasonCalendarPanel data={SEASONS} />)
    await screen.getByRole('button', { name: 'Season onsets' }).click()
    await expect.element(screen.getByText('Failed').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/seasons:onset_release'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/seasons:onset_release')[0].body
    ).toEqual({ onset_id: 31 })
    await screen.getByRole('button', { name: 'Clear' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/seasons:onset_clear'))
      .toHaveLength(1)
    const hold = screen.getByRole('button', { name: 'Hold this onset' })
    await expect.element(hold).toBeDisabled()
    await expect
      .element(hold)
      .toHaveAccessibleDescription('Write the year as a whole number.')
    await screen
      .getByRole('spinbutton', { name: 'Year', exact: true })
      .fill('40')
    await hold.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/seasons:onset'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/seasons:onset')[0].body).toEqual({
      world_id: 1,
      year: 40,
      season_position: 0,
      onset: 'failed',
    })
  })

  it('keeps the add-season control disabled with its reason once the year is full', async () => {
    serve()
    onApi('GET', '/api/worlds/1/calendar', CALENDAR)
    const { screen } = await renderApp(
      <SeasonCalendarPanel
        data={{ ...(SEASONS as object), seasons_max: 2 } as never}
      />
    )
    await screen.getByRole('button', { name: 'Seasons and moons' }).click()
    await expect
      .element(screen.getByText('The wheel of the year'))
      .toBeVisible()
    const add = screen.getByRole('button', { name: 'Add the season' })
    await expect.element(add).toBeDisabled()
    await expect
      .element(add)
      .toHaveAccessibleDescription('A world keeps at most 2 seasons.')
  })
})
