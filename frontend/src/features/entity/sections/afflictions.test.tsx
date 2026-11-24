import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AfflictionsSection } from './AfflictionsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const BASE = {
  stage_label: null,
  stage_count: 3,
  since_epoch: 48,
  stage_since_epoch: 49,
  next_stage_epoch: 52,
  source_node_id: null,
  source_name: null,
  source_link: null,
  visibility: 'noticeable',
  cured_epoch: null,
  applied: {},
  fortune_sign: null,
  fortune_strength: null,
  transform_plan: null,
  transform_species_id: null,
  transform_substance: null,
  transform_trigger: null,
  transform_mind_kept: null,
  changed_from: null,
  charm_target_id: null,
  charm_target_name: null,
  charm_kind: null,
  charm_strength: null,
  ageing_rate_pct: null,
  forget_scope: null,
  sleep_until: null,
}

const VIEW = {
  node_id: 501,
  name: 'Oswin',
  bearable: true,
  epoch: 50,
  afflictions: [
    {
      ...BASE,
      id: 1,
      package: 'divine_blessing',
      label: 'A blessing',
      stage: 1,
      transmission: 'rite',
      held: false,
      fortune_sign: 1,
      fortune_strength: 60,
      charm_target_id: 77,
      charm_target_name: 'Hild',
      charm_kind: 'devotion',
      charm_strength: 45,
    },
    {
      ...BASE,
      id: 2,
      package: 'lycanthropy',
      label: 'A change of shape',
      stage: 2,
      transmission: 'bite',
      held: true,
      transform_plan: 'quadruped',
      transform_trigger: 'season',
      transform_mind_kept: false,
      changed_from: 'humanoid',
    },
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
    { id: 501, kind: 'entity', type: 'mortal', name: 'Oswin', world_id: 1 },
    { id: 77, kind: 'entity', type: 'mortal', name: 'Hild', world_id: 1 },
  ])
  onApi('GET', '/api/effect-packages', [])
  onApi('GET', '/api/variants', [])
}

describe('afflictions section', () => {
  beforeEach(resetApi)

  it('shows fortune, charm and change of shape on what a bearer carries', async () => {
    serve()
    onApi('GET', '/api/bodies/501/afflictions', VIEW)
    const { screen } = await renderApp(<AfflictionsSection nodeId={501} />)
    await expect
      .element(screen.getByText('Good fortune at strength 60'))
      .toBeVisible()
    await expect.element(screen.getByText('Charm of devotion')).toBeVisible()
    await expect.element(screen.getByText('Hild')).toBeVisible()
    await expect.element(screen.getByText('Charm strength 45')).toBeVisible()
    await expect.element(screen.getByText('Becomes four-legged')).toBeVisible()
    await expect.element(screen.getByText('Each season')).toBeVisible()
    await expect.element(screen.getByText('Loses its own mind')).toBeVisible()
    await expect.element(screen.getByText(/Changed now, from/)).toBeVisible()
  })

  it('deepens, holds and lets a held affliction run again', async () => {
    serve()
    onApi('GET', '/api/bodies/501/afflictions', VIEW)
    onApi('POST', '/api/actions/affliction:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/affliction:hold', ACCEPTED_ACTION)
    const { screen } = await renderApp(<AfflictionsSection nodeId={501} />)
    await screen.getByRole('button', { name: 'Deepen a stage' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/affliction:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/affliction:edit')[0].body).toEqual({
      affliction_id: 1,
      stage: 2,
      clear_source: false,
    })
    await screen.getByRole('button', { name: 'Hold it here' }).click()
    await screen.getByRole('button', { name: 'Let it run' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/affliction:hold'))
      .toHaveLength(2)
    expect(
      callsTo('POST', '/api/actions/affliction:hold').map((call) => call.body)
    ).toEqual([
      { affliction_id: 1, hold: true },
      { affliction_id: 2, hold: false },
    ])
  })

  it('says why a stage cannot ease further', async () => {
    serve()
    onApi('GET', '/api/bodies/501/afflictions', {
      ...VIEW,
      afflictions: [{ ...VIEW.afflictions[0], stage: 0 }],
    })
    const { screen } = await renderApp(<AfflictionsSection nodeId={501} />)
    const ease = screen.getByRole('button', { name: 'Ease a stage' })
    await expect.element(ease).toBeDisabled()
    await expect
      .element(ease)
      .toHaveAccessibleDescription('It cannot ease further.')
  })
})
