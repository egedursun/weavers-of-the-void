import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { YearStrip, yearCounts } from '@/features/chronicle/YearStrip'
import { ForgeLey, HoldWeather, NotableYears } from './RegionPowers'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const GROUND = {
  region_id: 5,
  neighbours: [{ id: 6, name: 'Far Dunes' }],
  ley_lines: [
    {
      id: 1,
      other_region_id: 6,
      other_region_name: 'Far Dunes',
      strength: 60,
      severed: false,
      severed_until_epoch: null,
      forged: true,
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
  forecast: [
    {
      season_id: 1,
      season_name: 'Rains',
      kind: 'rain',
      label: 'Rain',
      effects: {},
    },
  ],
  notable_years: [
    {
      id: 2,
      epoch: 3,
      year: 140,
      kind: 'plenty',
      weather: null,
      name: 'the Year of Plenty in Vale',
      magnitude: 40,
      region_id: 5,
      legend_id: 11,
    },
  ],
} as never

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 3 },
  })
}

describe('region powers', () => {
  beforeEach(resetApi)

  it('forges, holds and remembers on a region', async () => {
    serve()
    onApi('POST', '/api/actions/ley:unforge', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/weather:release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/year:force_notable', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <>
        <ForgeLey regionId={5} ground={GROUND} />
        <HoldWeather regionId={5} ground={GROUND} />
        <NotableYears regionId={5} ground={GROUND} />
      </>
    )
    await expect.element(screen.getByText('Forged to Far Dunes')).toBeVisible()
    await screen.getByRole('button', { name: 'Leave it to the land' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/ley:unforge'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/weather:release'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/weather:release')[0].body).toEqual({
      forced_id: 9,
    })
    await expect
      .element(screen.getByText('Plenty; told as a legend'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Remember this year' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/year:force_notable'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/year:force_notable')[0].body
    ).toMatchObject({ region_id: 5, kind: 'plenty', magnitude: 50 })
  })

  it('counts the years of an epoch and picks one', async () => {
    const lines = [
      { id: 1, year: 140, text: 'a' },
      { id: 2, year: 140, text: 'b' },
      { id: 3, year: 151, text: 'c' },
    ] as never
    expect([...yearCounts(lines)]).toEqual([
      [140, 2],
      [151, 1],
    ])
    const picked: (number | null)[] = []
    const { screen } = await renderApp(
      <YearStrip
        lines={lines}
        selected={null}
        onSelect={(year) => picked.push(year)}
      />
    )
    await screen.getByRole('button', { name: 'Year 151, 1 record' }).click()
    expect(picked).toEqual([151])
  })
})
