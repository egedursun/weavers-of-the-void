import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SacredSection } from './SacredSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 30, kind: 'entity' as const, name: 'Wellbrook' }
const SPIRIT = { id: 31, kind: 'entity' as const, name: 'Spirit of Wellbrook' }
const MORTAL = { id: 32, kind: 'entity' as const, name: 'Orla' }
const SON = { id: 4, kind: 'son' as const, name: 'Thalor' }

const EMPTY = {
  spirits: [],
  offices: [],
  petitions: [],
  mystic: null,
  mystics: [],
  movements: [],
  crises: [],
  teachings: [],
  sacraments: [],
  afterlives: [],
  climate: null,
  systems: [],
  readings: [],
  foresights: [],
  models: [],
  feedings: [],
  harvests: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    {
      kind: 'entity',
      id: 30,
      name: 'Wellbrook',
      type: 'settlement',
      world_id: 1,
    },
    {
      kind: 'entity',
      id: 31,
      name: 'Spirit of Wellbrook',
      type: 'spirit',
      world_id: 1,
    },
    { kind: 'entity', id: 32, name: 'Orla', type: 'mortal', world_id: 1 },
    { kind: 'son', id: 4, name: 'Thalor' },
  ])
}

describe('spirits, mysteries, rites and omens', () => {
  beforeEach(() => resetApi())

  it('shows a town’s spirit, its office and a petition, and grants it', async () => {
    serveBase()
    onApi('GET', '/api/sacred/of/30', {
      ...EMPTY,
      node: TOWN,
      spirits: [
        {
          spirit: SPIRIT,
          place: TOWN,
          community: TOWN,
          kind: 'city',
          temperament: 40,
          contentment: 70,
          offerings: 3,
          owed: 1,
          favour: 25,
          offended: 'pollution',
          last_offering_epoch: 5,
          bound_epoch: 2,
          locked: [],
        },
      ],
      offices: [
        {
          spirit: SPIRIT,
          rank: 'city',
          superior: null,
          overseer: SON,
          jurisdiction: TOWN,
          merit: 12,
          corruption: 20,
          resolved: 4,
          neglected: 0,
          dismissed: false,
          appointed_epoch: 2,
          locked: [],
        },
      ],
      petitions: [
        {
          id: 9,
          petitioner: MORTAL,
          office: SPIRIT,
          kind: 'healing',
          defendant: null,
          target: null,
          bribe: 0,
          status: 'filed',
          filed_epoch: 5,
          due_epoch: 6,
          resolved_epoch: null,
          appealed_to: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/petition:judge', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SacredSection nodeId={30} />)
    await expect
      .element(
        screen.getByText(
          'Wellbrook: contentment 70, favour 25, offended by pollution'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Orla asks for healing'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Grant it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/petition:judge'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/petition:judge')[0].body).toEqual({
      petition_id: 9,
      granted: true,
    })
  })

  it('reads a mystic’s visions and answers in another as a god', async () => {
    serveBase()
    onApi('GET', '/api/sacred/of/32', {
      ...EMPTY,
      node: MORTAL,
      mystic: {
        mortal: MORTAL,
        state: 'visionary',
        visions: 3,
        genuine_visions: 1,
        followers: 40,
        answered_by: SON,
        cult: null,
        founded: null,
        reverence: 30,
        persecution: 10,
        since_epoch: 3,
        last_vision_epoch: 5,
        history: [
          {
            id: 2,
            epoch: 5,
            kind: 'union',
            sender: SON,
            genuine: true,
            awe: 40,
            locked: [],
          },
        ],
        locked: [],
      },
      sacraments: [
        {
          id: 7,
          mortal: MORTAL,
          kind: 'initiation',
          cult: null,
          priest: null,
          epoch: 4,
          missed: true,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/vision:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SacredSection nodeId={32} />)
    await expect
      .element(screen.getByText('Orla: 3 visions, 1 real, 40 followers'))
      .toBeVisible()
    await expect.element(screen.getByText('Union in epoch 5')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Another vision of its own' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/vision:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/vision:create')[0].body).toEqual({
      mystic_id: 32,
      sender_id: null,
      kind: null,
    })
    await screen
      .getByRole('tab', { name: /Rites, afterlife and faith/ })
      .click()
    await expect.element(screen.getByText('Initiation of Orla')).toBeVisible()
  })

  it('names a sea spirit, its offence and the wrongdoer a petition for vengeance names', async () => {
    serveBase()
    onApi('GET', '/api/sacred/of/30', {
      ...EMPTY,
      node: TOWN,
      spirits: [
        {
          spirit: SPIRIT,
          place: TOWN,
          community: TOWN,
          kind: 'sea',
          temperament: 40,
          contentment: 30,
          offerings: 0,
          owed: 4,
          favour: 0,
          offended: 'overharvest',
          last_offering_epoch: null,
          bound_epoch: 2,
          locked: [],
        },
      ],
      petitions: [
        {
          id: 11,
          petitioner: MORTAL,
          office: SPIRIT,
          kind: 'vengeance',
          defendant: null,
          target: TOWN,
          bribe: 0,
          status: 'filed',
          filed_epoch: 5,
          due_epoch: 6,
          resolved_epoch: null,
          appealed_to: null,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<SacredSection nodeId={30} />)
    await expect
      .element(
        screen.getByText(
          'Wellbrook: contentment 30, favour 0, offended by more taken than its due'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Orla asks for vengeance on a wrongdoer'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Vengeance sought on').first())
      .toBeVisible()
  })

  it('shows what a god feeds on and sets a new feeling', async () => {
    serveBase()
    onApi('GET', '/api/sacred/of/4', {
      ...EMPTY,
      node: SON,
      feedings: [
        { emotion: 'grief', weight: 60, harvested: 7, epoch: 5, locked: [] },
      ],
      harvests: [{ id: 1, epoch: 5, emotion: 'grief', count: 80, essence: 7 }],
    })
    onApi('POST', '/api/actions/god_feeding:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SacredSection nodeId={4} />)
    await expect.element(screen.getByText('Feeds on grief')).toBeVisible()
    await expect
      .element(screen.getByText('Grief: 7 essence over 1 epoch'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Feed on it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/god_feeding:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/god_feeding:set')[0].body).toEqual({
      god_id: 4,
      emotion: 'awe',
      weight: 50,
    })
  })
})
