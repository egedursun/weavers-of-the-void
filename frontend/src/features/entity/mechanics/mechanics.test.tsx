import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CausalityGraph, layoutCausality, linkedOnly } from './CausalityGraph'
import { ModifierCard, ModifierForge } from './ModifierForge'
import { ProfileValues, parseColumn } from './ProfileValues'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MODIFIER = {
  id: 5,
  key: 'prosperity',
  op: 'multiply' as const,
  magnitude: 0.9,
  source_kind: 'curse' as const,
  source_subsystem: 'gods' as const,
  source_node_id: 3,
  source_name: 'Haevaron',
  reason_key: 'modifier.curse',
  reason: 'a curse laid by Haevaron',
  stacking_group: 'curse',
  start_epoch: 4,
  end_epoch: null,
  decay_pct: null,
  held: false,
}

const NODE = {
  id: 1,
  kind: 'grudges.enmity',
  epoch: 2,
  year: 40,
  magnitude: 30,
  text: 'The grudge began.',
  own: false,
  role: null,
  cause_incident_id: null,
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

describe('mechanics controls', () => {
  beforeEach(resetApi)

  it('forges a modifier of an engine source', async () => {
    serve()
    onApi('POST', '/api/actions/modifier:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <ModifierForge nodeId={9} statKeys={['prosperity']} blocked={undefined} />
    )
    await screen.getByRole('spinbutton', { name: 'Amount' }).fill('4')
    await screen.getByRole('button', { name: 'Forge it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/modifier:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/modifier:create')[0].body).toEqual({
      node_id: 9,
      key: 'prosperity',
      op: 'add',
      magnitude: 4,
      source_kind: 'player',
      source_node_id: null,
      stacking_group: null,
      epochs: null,
      decay_pct: null,
    })
  })

  it('holds a derived modifier so the engine keeps it', async () => {
    serve()
    onApi('POST', '/api/actions/modifier:hold', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <ul>
        <ModifierCard modifier={MODIFIER} blocked={undefined} />
      </ul>
    )
    await expect
      .element(screen.getByText('a curse laid by Haevaron'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Hold' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/modifier:hold'))
      .toHaveLength(1)
  })

  it('draws only linked incidents, one column per step of cause', async () => {
    const graph = {
      node_id: 9,
      nodes: [
        NODE,
        {
          ...NODE,
          id: 2,
          epoch: 5,
          own: true,
          role: 'actor' as const,
          cause_incident_id: 1,
        },
        { ...NODE, id: 3, epoch: 6, own: true, role: 'subject' as const },
      ],
      edges: [{ cause: 1, effect: 2, span: 3 }],
    }
    const layout = layoutCausality(linkedOnly(graph))
    expect(layout.placed.map((item) => item.node.id)).toEqual([1, 2])
    expect(layout.placed[1].x).toBeGreaterThan(layout.placed[0].x)
    serve()
    onApi('GET', '/api/nodes/9/causality', graph)
    const { screen } = await renderApp(<CausalityGraph nodeId={9} />)
    await expect
      .element(screen.getByRole('img', { name: 'Causality graph' }))
      .toBeVisible()
  })

  it('sets and holds a profile value', async () => {
    serve()
    onApi('GET', '/api/nodes/9/profiles', [
      {
        table: 'place_environment',
        lockable: true,
        columns: [
          {
            name: 'chokepoint',
            kind: 'flag',
            value: false,
            options: [],
            nullable: false,
            held: false,
            pinned: false,
          },
        ],
      },
    ])
    onApi('POST', '/api/actions/profile:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <ProfileValues nodeId={9} blocked={undefined} />
    )
    await screen.getByRole('button', { name: 'Adjust values' }).click()
    await screen.getByRole('switch', { name: 'Chokepoint' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/profile:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/profile:set')[0].body).toEqual({
      node_id: 9,
      table: 'place_environment',
      column: 'chokepoint',
      value: true,
      hold: true,
    })
    expect(
      parseColumn(
        {
          name: 'height',
          kind: 'integer',
          value: 1,
          options: [],
          nullable: true,
          held: false,
          pinned: false,
        },
        ''
      )
    ).toBeNull()
  })
})
