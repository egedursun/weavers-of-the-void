import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GatheringsSection } from './GatheringsSection'
import { HistoriesSection } from './HistoriesSection'
import { LegendsSection } from './LegendsSection'
import { SiteSection } from './SiteSection'
import { StorytellerSection } from './StorytellerSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const HOST = { id: 11, kind: 'entity' as const, name: 'Aben' }
const GUEST = { id: 12, kind: 'entity' as const, name: 'Corra' }
const HALL = { id: 40, kind: 'entity' as const, name: 'Long Hall' }

const GATHERING = {
  id: 7,
  kind: 'feast' as const,
  status: 'planned' as const,
  outcome: null,
  milestone: null,
  host: HOST,
  place: HALL,
  honoured: null,
  tradition: null,
  collection_id: null,
  epoch: 4,
  year: 212,
  season: 1,
  season_name: 'Thaw',
  seasons: [
    { position: 0, name: 'Frost' },
    { position: 1, name: 'Thaw' },
  ],
  cost: 30,
  prestige: 12,
  by_player: true,
  note: 'held by order of the gods',
  locked: [],
  guests: [
    {
      node: GUEST,
      role: 'guest' as const,
      reason: 'friend' as const,
      invited: true,
      attended: null,
      harmed: false,
      locked: false,
    },
  ],
}

const COLLECTION = {
  id: 90,
  kind: 'journey' as const,
  name: 'The Long Walk',
  world_id: 1,
  start_epoch: 2,
  end_epoch: null,
  parent_id: null,
  note: null,
  locked: [],
  members: 2,
  places: 1,
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('gatherings, histories, the storyteller and sites', () => {
  beforeEach(() => resetApi())

  it('lists a hosted feast and holds it at once', async () => {
    serveBase()
    onApi('GET', '/api/gatherings/of/11', {
      node_id: 11,
      hosted: [GATHERING],
      attended: [],
    })
    onApi('POST', '/api/actions/gathering:hold', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/gathering_guest:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GatheringsSection nodeId={11} />)
    await expect.element(screen.getByText('Feast').first()).toBeVisible()
    await expect.element(screen.getByText('Corra').first()).toBeVisible()
    await expect.element(screen.getByText(/year 212, Thaw/)).toBeVisible()
    await screen.getByRole('button', { name: 'Hold now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/gathering:hold'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/gathering:hold')[0].body).toEqual({
      gathering_id: 7,
    })
    await screen
      .getByRole('button', { name: 'Strike Corra from the list' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/gathering_guest:remove'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/gathering_guest:remove')[0].body
    ).toEqual({ gathering_id: 7, node_id: 12 })
  })

  it('opens a history of a figure and strikes one of its members', async () => {
    serveBase()
    onApi('GET', '/api/histories/of/11', {
      node_id: 11,
      entries: [{ collection: COLLECTION, role: 'leader' }],
    })
    onApi('GET', '/api/histories/90', {
      collection: COLLECTION,
      parent: null,
      children: [],
      roster: [
        { node: HOST, role: 'leader', since_epoch: 2 },
        { node: GUEST, role: 'witness', since_epoch: 3 },
      ],
      sites: [HALL],
      incidents: [{ id: 5, epoch: 3, text: 'They set out at dawn.' }],
    })
    onApi('POST', '/api/actions/collection_member:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HistoriesSection nodeId={11} />)
    await expect.element(screen.getByText('The Long Walk')).toBeVisible()
    await screen.getByRole('button', { name: 'Open' }).click()
    await expect
      .element(screen.getByText('They set out at dawn.'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Strike' }).nth(1).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/collection_member:remove'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/collection_member:remove')[0].body
    ).toEqual({ collection_id: 90, node_id: 12 })
  })

  it('pages the legends of the cosmos with their count', async () => {
    serveBase()
    onApi('GET', '/api/histories', { items: [COLLECTION], total: 1 })
    const { screen } = await renderApp(
      <LegendsSection worlds={[{ id: 1, name: 'Aerona' }]} />
    )
    await expect.element(screen.getByText('The Long Walk')).toBeVisible()
    await expect.element(screen.getByText('1 history')).toBeVisible()
    expect(callsTo('GET', '/api/histories')[0].search.get('limit')).toBe('10')
  })

  it('reads the tension of a world and changes its storyteller', async () => {
    serveBase()
    onApi('GET', '/api/storyteller/1', {
      world_id: 1,
      profile: 'cyclic',
      tension: 64,
      target: 40,
      band: 'heated',
      boost_pct: -12,
      cycle_offset: 3,
      spotlight: HOST,
      recent_kinds: { raid: 2 },
      updated_epoch: 6,
      locked: [],
      curve: [
        { epoch: 5, tension: 50, target: 40, boost_pct: 0, band: 'in_band' },
        { epoch: 6, tension: 64, target: 40, boost_pct: -12, band: 'heated' },
      ],
    })
    onApi('POST', '/api/actions/storyteller:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<StorytellerSection worldId={1} />)
    await expect.element(screen.getByText('Raids').first()).toBeVisible()
    await screen.getByRole('radio', { name: /Chaotic/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/storyteller:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/storyteller:set')[0].body).toEqual({
      world_id: 1,
      profile: 'chaotic',
      values: {},
      release: [],
    })
  })

  it('walks the rooms of a site and says why it cannot be dug', async () => {
    serveBase()
    onApi('GET', '/api/sites/40', {
      site_id: 40,
      roomed: true,
      diggable: false,
      rooms: [
        {
          id: 3,
          position: 0,
          kind: 'gate',
          challenge: 'trap',
          difficulty: 30,
          cleared_epoch: null,
          cleared_by: null,
          locked: [],
          contents: [],
        },
      ],
      holders: [],
      digs: [],
      features: [],
    })
    onApi('POST', '/api/actions/site_room:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <SiteSection siteId={40} entityType='structure' />
    )
    await expect.element(screen.getByText('1. Gate')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Break ground' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Remove' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/site_room:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/site_room:delete')[0].body).toEqual({
      room_id: 3,
    })
  })
})
