import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoriesSection } from '../sections/MemoriesSection'
import { MindSection } from '../sections/MindSection'
import { SkillsSection } from '../sections/SkillsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const AXES = [
  ['honour', 'Pragmatism', 'Honour', 40],
  ['tradition', 'Innovation', 'Tradition', -20],
  ['hierarchy', 'Equality', 'Hierarchy', 10],
  ['martial', 'Peace', 'Martial glory', 70],
  ['piety', 'Worldliness', 'Piety', -55],
  ['purity', 'Tolerance of the unclean', 'Purity', 5],
  ['kinship', 'Individualism', 'Clan loyalty', 30],
  ['mercy', 'Cruelty', 'Mercy', -10],
  ['knowledge', 'Scorn of learning', 'Learning', 15],
  ['wealth', 'Austerity', 'Commerce and display', 0],
  ['nature', 'Mastery over nature', 'Harmony with nature', 0],
  ['superstition', 'Rationalism', 'Omen-reading', 25],
  ['xenophilia', 'Xenophobia', 'Openness to strangers', -5],
  ['death', 'Fear of death', 'Veneration of the dead', 0],
] as const

const SELF = { id: 7, kind: 'entity', name: 'Kel' }
const FOE = { id: 9, kind: 'entity', name: 'Morr' }

const MIND = {
  node_id: 7,
  name: 'Kel',
  holder: 'personal',
  locked: ['values'],
  lockable: ['values', 'traits', 'skills', 'memories', 'needs', 'role'],
  borrowed_from: null,
  reference: { id: 3, kind: 'entity', name: 'Hill Folk' },
  values: AXES.map(([axis, low, high, value]) => ({
    axis,
    low_label: low,
    high_label: high,
    value,
    reference: value - 10,
  })),
  traits: [
    {
      trait: 'brave',
      label: 'Brave',
      source: 'experience',
      epoch: 4,
      source_node: null,
      opposite: 'craven',
      heritable: true,
      effects: [{ effect: 'courage', value: 30 }],
      capacities: [{ capacity: 'melee', value: 10 }],
    },
  ],
  skills: [
    {
      skill: 'spear',
      label: 'Spear',
      family: 'combat',
      capacity: 'melee',
      level: 62,
      effective: 31,
      peak: 70,
      xp: 12,
      next_level_xp: 57,
      last_used_epoch: 2,
      rusting: true,
      source: 'practice',
    },
  ],
  needs: [
    { need: 'safety', label: 'Safety', value: 20 },
    { need: 'purpose', label: 'Purpose', value: 80 },
  ],
  pressures: [],
  memories: [
    {
      id: 41,
      subject: FOE,
      kind: 'killed_kin',
      label: 'Killed our kin',
      magnitude: -60,
      strength: -48,
      decay_pct: 2,
      epoch: 3,
      note: 'Arn',
      inherited_from: null,
    },
  ],
  opinions: [
    {
      holder: SELF,
      subject: FOE,
      value: -48,
      alignment: -6,
      components: [
        { component: 'trust', value: -7 },
        { component: 'fear', value: 5 },
        { component: 'respect', value: 0 },
        { component: 'affection', value: 0 },
        { component: 'grievance', value: 36 },
      ],
      terms: [{ key: 'enemy', value: -50 }],
      memories: [
        {
          id: 41,
          kind: 'killed_kin',
          label: 'Killed our kin',
          epoch: 3,
          strength: -48,
          weight_pct: 140,
          contribution: -67,
          note: 'Arn',
        },
      ],
    },
  ],
  career: { role: 'warrior', ended_epoch: 5, fixed: false },
  max_traits: 5,
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/minds/7', MIND)
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 7, name: 'Kel', type: 'mortal', status: 'canon' },
    { kind: 'entity', id: 9, name: 'Morr', type: 'mortal', status: 'canon' },
  ])
}

describe('mind sections', () => {
  beforeEach(resetApi)

  it('shows values on a radar, the temperament and the needs, and takes a trait away', async () => {
    serve()
    onApi('POST', '/api/actions/mind:trait_remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MindSection nodeId={7} />)
    await expect.element(screen.getByRole('img', { name: 'Kel' })).toBeVisible()
    await expect
      .element(screen.getByText('Martial glory (against peace)'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Worldliness (against piety)'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Brave', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('A wound ended their old calling in epoch 5'))
      .toBeVisible()
    await expect.element(screen.getByText('Holding values')).toBeVisible()
    await screen.getByRole('button', { name: 'Take away Brave' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mind:trait_remove'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mind:trait_remove')[0].body).toEqual({
      node_id: 7,
      trait: 'brave',
    })
  })

  it('releases a held part of the mind', async () => {
    serve()
    onApi('POST', '/api/actions/mind:unlock', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MindSection nodeId={7} />)
    await screen.getByRole('button', { name: 'Release values' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mind:unlock'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mind:unlock')[0].body).toEqual({
      node_id: 7,
      field: 'values',
    })
  })

  it('lists skills by family with rust and wounds, and forgets one', async () => {
    serve()
    onApi('POST', '/api/actions/mind:skill_remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SkillsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Spear', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Only 31 with this body'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Rusting, last used in epoch 2'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Forget Spear' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mind:skill_remove'))
      .toHaveLength(1)
  })

  it('explains an opinion and erases a memory', async () => {
    serve()
    onApi('POST', '/api/actions/mind:memory_remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MemoriesSection nodeId={7} />)
    await expect.element(screen.getByText('Distrust')).toBeVisible()
    await expect.element(screen.getByText('Open enmity -50')).toBeVisible()
    await expect.element(screen.getByText('Now -48 (was -60)')).toBeVisible()
    await screen.getByRole('button', { name: 'Edit' }).click()
    await screen.getByRole('button', { name: 'Erase' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mind:memory_remove'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mind:memory_remove')[0].body).toEqual({
      memory_id: 41,
    })
  })
})
