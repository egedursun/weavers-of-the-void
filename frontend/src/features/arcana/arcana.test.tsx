import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ArcanaSection } from './ArcanaSection'
import { MythicSection } from './MythicSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 7, kind: 'son' as const, name: 'Thalen' }
const MAGE = { id: 40, kind: 'entity' as const, name: 'Ilse' }
const RITE = { id: 50, kind: 'entity' as const, name: 'Kindling' }

const EMPTY_ARCANA = {
  grammar: null,
  lab_texts: [],
  vis: [],
  warping: null,
  longevity: null,
  charges: [],
  upkeep: null,
  kept: [],
}

const EMPTY_MYTHIC = {
  heroquests: [],
  mantling: null,
  walkers: [],
  servitor: null,
  servitors: [],
  geasa: [],
  laid: [],
  offices: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 40, name: 'Ilse', type: 'mortal', world_id: 1 },
    { kind: 'entity', id: 50, name: 'Kindling', type: 'rite', world_id: 1 },
  ])
}

describe('arcana', () => {
  beforeEach(() => resetApi())

  it('shows a mage’s vis, warping and longevity and takes vis away', async () => {
    serveBase()
    onApi('GET', '/api/arcana/of/40', {
      ...EMPTY_ARCANA,
      node: MAGE,
      vis: [{ form: 'fire', amount: 4, locked: [] }],
      warping: { value: 35, stage: 1, updated_epoch: 5, locked: [] },
      longevity: {
        form: 'body',
        dose: 1,
        dependence: 20,
        years_gained: 12,
        lapsed_epochs: 0,
        since_epoch: 3,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/vis:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ArcanaSection nodeId={40} />)
    await expect.element(screen.getByText('Fire 4')).toBeVisible()
    await expect
      .element(screen.getByText('Longevity magic').first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Take away the fire vis' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/vis:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/vis:delete')[0].body).toEqual({
      holder_id: 40,
      form: 'fire',
    })
  })

  it('shows the grammar of a rite and returns it to its school', async () => {
    serveBase()
    onApi('GET', '/api/arcana/of/50', {
      ...EMPTY_ARCANA,
      node: RITE,
      grammar: {
        technique: 'destroy',
        form: 'fire',
        range: 'sight',
        duration: 'instant',
        target: 'one',
        difficulty: 42,
        paradigm: null,
        myth: null,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/rite_grammar:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ArcanaSection nodeId={50} />)
    await expect.element(screen.getByText('Destroy fire')).toBeVisible()
    await expect.element(screen.getByText('Difficulty 42')).toBeVisible()
    await screen.getByRole('button', { name: 'Back to its school' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/rite_grammar:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/rite_grammar:delete')[0].body).toEqual(
      { rite_id: 50 }
    )
  })

  it('says why the magic could not be read', async () => {
    serveBase()
    onApi('GET', '/api/arcana/of/40', failure(500, 'The heavens are silent.'))
    const { screen } = await renderApp(<ArcanaSection nodeId={40} />)
    await expect
      .element(screen.getByText('The magic could not be read'))
      .toBeVisible()
  })
})

describe('myth', () => {
  beforeEach(() => resetApi())

  it('shows a mortal’s path and geas and breaks the geas', async () => {
    serveBase()
    onApi('GET', '/api/mythic/of/40', {
      ...EMPTY_MYTHIC,
      node: MAGE,
      heroquests: [
        {
          id: 5,
          quester: MAGE,
          legend: null,
          god: SON,
          realm: 'dead',
          place: null,
          steps: 4,
          step: 1,
          fidelity: 80,
          deviated: false,
          state: 'questing',
          boon: null,
          interference: 15,
          next_trial: 'passion',
          members: [{ id: 41, kind: 'entity' as const, name: 'Cade' }],
          start_epoch: 5,
          end_epoch: null,
          locked: [],
        },
      ],
      mantling: {
        mortal: MAGE,
        god: SON,
        deeds: 8,
        worship: 2,
        progress: 90,
        state: 'walking',
        blocked: false,
        notified: true,
        since_epoch: 4,
        locked: [],
      },
      geasa: [
        {
          id: 3,
          bearer: MAGE,
          layer_node: SON,
          layer: 'god',
          mode: 'taboo',
          act: 'theft',
          state: 'kept',
          favour: 12,
          laid_epoch: 2,
          last_kept_epoch: 5,
          broken_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/geas:break', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/heroquest:party', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MythicSection nodeId={40} />)
    await expect.element(screen.getByText('Taboo: Theft')).toBeVisible()
    await expect
      .element(screen.getByText('Next: a trial of passion'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText("Walking a god's path · since epoch 4 · you were told")
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Send Cade home' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/heroquest:party'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/heroquest:party')[0].body).toEqual({
      quest_id: 5,
      members: [],
    })
    await screen.getByRole('button', { name: 'Break it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/geas:break'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/geas:break')[0].body).toEqual({
      geas_id: 3,
    })
  })

  it('shows a god’s cosmic offices and empties one', async () => {
    serveBase()
    onApi('GET', '/api/mythic/of/7', { ...EMPTY_MYTHIC, node: SON })
    onApi('GET', '/api/mythic/offices', [
      {
        office: 'dead',
        holder: SON,
        chosen_by: 'creator',
        since_epoch: 2,
        neglect: 0,
        duty: 40,
        office_kind_id: null,
        office_duty: 'the_dead',
        office_name: null,
        locked: [],
      },
    ])
    onApi('POST', '/api/actions/cosmic_office:vacate', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MythicSection nodeId={7} />)
    await expect.element(screen.getByText('Office of the dead')).toBeVisible()
    await screen.getByRole('button', { name: 'Empty it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cosmic_office:vacate'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/cosmic_office:vacate')[0].body
    ).toEqual({ office: 'dead' })
  })

  it('says why the myths could not be read', async () => {
    serveBase()
    onApi('GET', '/api/mythic/of/7', failure(500, 'The heavens are silent.'))
    const { screen } = await renderApp(<MythicSection nodeId={7} />)
    await expect
      .element(screen.getByText('The myths could not be read'))
      .toBeVisible()
  })
})
