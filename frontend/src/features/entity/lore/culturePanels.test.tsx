import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TongueAtlas } from '@/features/languages/TongueAtlas'
import { LanguagePanel } from './panels/LanguagePanel'
import { LegendPanel } from './panels/LegendPanel'
import { TraditionPanel } from './panels/TraditionPanel'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 30, kind: 'entity' as const, name: 'Ashford' }
const COURT = { id: 31, kind: 'entity' as const, name: 'Kingdom of Ash' }
const TONGUE = { id: 7, kind: 'entity' as const, name: 'Ossic' }
const OTHER = { id: 8, kind: 'entity' as const, name: 'Varn' }
const BARD = { id: 40, kind: 'entity' as const, name: 'Ilse' }
const WORK = { id: 41, kind: 'entity' as const, name: 'The Garden Fresco' }

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

describe('culture panels', () => {
  beforeEach(resetApi)

  it('shows registers and releases a held understanding', async () => {
    serve()
    onApi(
      'POST',
      '/api/actions/language:release_understanding',
      ACCEPTED_ACTION
    )
    const { screen } = await renderApp(
      <LanguagePanel
        id={7}
        blocked={null}
        card={{
          prestige: 60,
          prestige_parts: { 'its literature': 12 },
          standardisation: 40,
          liturgical: false,
          lingua_franca: true,
          speakers: [
            {
              community: TOWN,
              kind: 'native',
              share: 80,
              since_epoch: 1,
              held: true,
            },
          ],
          kin: [{ language: OTHER, value: 45, held: true }],
          registers: [
            {
              holder: COURT,
              kind: 'court',
              language: TONGUE,
              since_epoch: 3,
              held: true,
            },
          ],
          locked: [],
        }}
      />
    )
    await expect.element(screen.getByText('Court').first()).toBeVisible()
    await expect
      .element(screen.getByText('Kingdom of Ash').first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Shape this tongue' }).click()
    await screen
      .getByRole('button', { name: 'Let the world measure Varn again' })
      .click()
    await expect
      .poll(() =>
        callsTo('POST', '/api/actions/language:release_understanding')
      )
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/language:release_understanding')[0].body
    ).toEqual({ first_id: 7, second_id: 8 })
  })

  it('shows a legend with its bards, its true source and its fixing work', async () => {
    serve()
    const { screen } = await renderApp(
      <LegendPanel
        id={9}
        blocked={null}
        card={{
          archetype: 'lost_paradise',
          credence: 55,
          distortion: 20,
          subject: null,
          moral: { nature: 5 },
          tellers: [TOWN],
          bards: [BARD],
          fixed_in: WORK,
          source: { id: 3, kind: 'war.battle', epoch: 2, note: null },
          custom_archetype_id: null,
          locked: [],
        }}
      />
    )
    await expect
      .element(screen.getByText('Born of a true incident in epoch 2'))
      .toBeVisible()
    await expect.element(screen.getByText('Ilse')).toBeVisible()
    await expect
      .element(screen.getByText('The Garden Fresco').first())
      .toBeVisible()
  })

  it('shows what a tradition brings and sets a new effect', async () => {
    serve()
    onApi('POST', '/api/actions/tradition:effect', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <TraditionPanel
        id={11}
        blocked={null}
        card={{
          kind: 'taboo',
          calendar_slot: 'midwinter',
          cost: {},
          effects: [
            { effect: 'cohesion', target: '', magnitude: 4 },
            { effect: 'value', target: 'mercy', magnitude: 2 },
          ],
          taboo_target: null,
          taboo_act: 'winter_fighting',
          custom_kind_id: null,
          origin: null,
          origin_incident: null,
          keepers: [
            {
              community: TOWN,
              participation: 70,
              skipped: 0,
              last_celebrated_epoch: 11,
              held: false,
            },
          ],
          locked: [],
        }}
      />
    )
    await expect
      .element(screen.getByText('Forbids war in winter'))
      .toBeVisible()
    await expect.element(screen.getByText('Cohesion +4')).toBeVisible()
    await expect.element(screen.getByText('Mercy pressed +2')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Shape this tradition' })
      .click({ force: true })
    await screen
      .getByRole('button', { name: 'Add' })
      .last()
      .click({ force: true })
    await expect
      .poll(() => callsTo('POST', '/api/actions/tradition:effect'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/tradition:effect')[0].body).toEqual({
      tradition_id: 11,
      effect: 'cohesion',
      target: '',
      magnitude: 2,
    })
  })

  it('shows the registers of a world in the tongue atlas', async () => {
    serve()
    onApi('GET', '/api/worlds/1/tongues', {
      ranking: [
        {
          language: TONGUE,
          prestige: 60,
          lingua_franca: true,
          liturgical: false,
          speakers: 2,
        },
      ],
      matrix: [[100]],
      registers: [
        {
          holder: COURT,
          kind: 'court',
          language: TONGUE,
          since_epoch: 3,
          held: false,
        },
      ],
    })
    const { screen } = await renderApp(<TongueAtlas worldId={1} />)
    await expect
      .element(screen.getByText('Court, liturgy, market and hearth'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Kingdom of Ash').first())
      .toBeVisible()
  })
})
