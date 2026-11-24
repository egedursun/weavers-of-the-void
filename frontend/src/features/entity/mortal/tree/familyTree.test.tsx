import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type FamilyTree, type TreePerson } from '../api'
import { FamilyTreePanel } from './FamilyTreePanel'
import { familyLayout } from './familyLayout'
import { kinCircle } from './kinship'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function person(
  id: number,
  name: string,
  relation: string,
  generation: number,
  extra: Partial<TreePerson> = {}
): TreePerson {
  return {
    id,
    name,
    title: null,
    relation,
    living: true,
    sex: 'bearer',
    role: null,
    generation,
    birth_epoch: 3 + generation,
    end_epoch: null,
    cover: null,
    house_id: 30,
    blood: true,
    ...extra,
  }
}

const TREE: FamilyTree = {
  root: 5,
  up: 3,
  down: 3,
  deeper_up: true,
  deeper_down: false,
  people: [
    person(4, 'Ama', 'Parent', -1, {
      living: false,
      end_epoch: 4,
      role: 'ruler',
    }),
    person(8, 'Vel', 'Godparent', -1, { blood: false, house_id: null }),
    person(5, 'Iska', 'This mortal', 0),
    person(6, 'Oru', 'Spouse', 0, { blood: false }),
    person(7, 'Tal', 'Child', 1),
  ],
  houses: [
    { house: { id: 30, kind: 'entity', name: 'House Ama' }, ink: 'gold' },
  ],
  unions: [
    {
      marriage_id: 9,
      first_id: 5,
      second_id: 6,
      form: 'pair',
      purpose: 'love',
      start_epoch: 4,
      end_epoch: null,
      cause_end: null,
      forced: false,
    },
  ],
  ties: [
    {
      bond_id: 11,
      kind: 'parent_of',
      source_id: 4,
      target_id: 5,
      past: false,
      epoch: 3,
    },
    {
      bond_id: 12,
      kind: 'parent_of',
      source_id: 5,
      target_id: 7,
      past: false,
      epoch: 5,
    },
    {
      bond_id: 13,
      kind: 'parent_of',
      source_id: 6,
      target_id: 7,
      past: false,
      epoch: 5,
    },
    {
      bond_id: 14,
      kind: 'godparent_of',
      source_id: 8,
      target_id: 5,
      past: false,
      epoch: 4,
    },
  ],
  layout: {
    width: 900,
    height: 700,
    card_width: 232,
    card_height: 84,
    cards: [
      { person_id: 4, x: 72, y: 98 },
      { person_id: 8, x: 400, y: 98 },
      { person_id: 5, x: 72, y: 338 },
      { person_id: 6, x: 364, y: 338 },
      { person_id: 7, x: 218, y: 578 },
    ],
    partners: [
      {
        key: 'marriage-9',
        first_id: 5,
        second_id: 6,
        kind: 'spouse_of',
        ended: false,
        widowed: false,
        marriage_id: 9,
        bond_id: null,
        path: 'M 304 380 H 364',
        knot_x: 334,
        knot_y: 380,
      },
    ],
    families: [
      {
        key: '4',
        parent_ids: [4],
        child_ids: [5],
        path: 'M 188 182 V 298 M 188 298 H 188 M 188 298 V 338',
      },
      {
        key: '5-6',
        parent_ids: [5, 6],
        child_ids: [7],
        path: 'M 334 380 V 538 M 334 538 H 334 M 334 538 V 578',
      },
    ],
    care: [{ bond_id: 14, path: 'M 516 182 C 516 260, 130 260, 130 338' }],
    rows: [
      { generation: -1, y: 98 },
      { generation: 0, y: 338 },
      { generation: 1, y: 578 },
    ],
  },
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/mortals/5/family', TREE)
}

describe('the family tree of a mortal', () => {
  beforeEach(() => resetApi())

  it('reads the drawn layout the world serves into cards and lines', () => {
    const layout = familyLayout(TREE)
    expect(layout.cards.size).toBe(5)
    expect(layout.partners[0]).toMatchObject({
      kind: 'spouse_of',
      knot: { x: 334, y: 380 },
    })
    expect(layout.partners[0].union?.purpose).toBe('love')
    expect(layout.care[0]).toMatchObject({ kind: 'godparent_of' })
    expect(layout.families.map((line) => line.children)).toEqual([[5], [7]])
  })

  it('lights a mortal, their blood, their spouses and their bonds of care', () => {
    expect([...kinCircle(TREE, 5)].sort()).toEqual([4, 5, 6, 7, 8])
    expect([...kinCircle(TREE, 6)].sort()).toEqual([5, 6, 7])
  })

  it('draws every kin by name and relation, and counts them', async () => {
    serve()
    const { screen } = await renderApp(
      <FamilyTreePanel mortalId={5} blocked={null} />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Tal, Child' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Ama, Parent' }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Kin in the tree')).toBeVisible()
    await expect.element(screen.getByText('More beyond')).toBeVisible()
    await expect.element(screen.getByText('House Ama').first()).toBeVisible()
  })

  it('chooses a mortal, shows their bonds and undoes one by the hand of the god', async () => {
    serve()
    onApi('POST', '/api/actions/kin:unbond', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <FamilyTreePanel mortalId={5} blocked={null} />
    )
    await screen.getByRole('button', { name: 'Tal, Child' }).click()
    await expect.element(screen.getByText('Chosen in the tree')).toBeVisible()
    await screen.getByRole('button', { name: 'Undo this bond' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/kin:unbond'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/kin:unbond')[0].body).toEqual({
      bond_id: 12,
    })
  })

  it('asks the world to leave out a bond of care the god hides', async () => {
    serve()
    const { screen } = await renderApp(
      <FamilyTreePanel mortalId={5} blocked={null} />
    )
    await screen.getByRole('button', { name: 'Godparent' }).first().click()
    await expect
      .poll(() =>
        callsTo('GET', '/api/mortals/5/family').some((call) =>
          call.search.getAll('hide').includes('godparent_of')
        )
      )
      .toBe(true)
  })
})
