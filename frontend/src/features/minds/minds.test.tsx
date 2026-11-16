import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AugmentsSection } from './AugmentsSection'
import { MadeWorldSection } from './MadeWorldSection'
import { MindSeatSection } from './MindSeatSection'
import { NetworkSection } from './NetworkSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const STEWARD = {
  id: 30,
  kind: 'entity' as const,
  name: 'Steward of the Locks',
}
const MAKER = { id: 31, kind: 'entity' as const, name: 'Imra Vael' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }
const RELAY = { id: 50, kind: 'entity' as const, name: 'Coast Relay' }
const TOWN = { id: 12, kind: 'entity' as const, name: 'Harrowmere' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function mind(overrides: Record<string, unknown> = {}) {
  return {
    node: STEWARD,
    seat: 'structure',
    seat_node: STEWARD,
    origin: 'made',
    will: 'emergent',
    affect: 'modelled',
    purpose: 'steward',
    capacity: 62,
    speed_pct: 300,
    stability: 81,
    fidelity_pct: 97,
    upkeep: 'energy',
    upkeep_energy: 'water',
    pausable: true,
    copyable: true,
    restorable: true,
    mergeable: false,
    transferable: true,
    dormant: false,
    perfect_recall: true,
    souled: false,
    made_by: MAKER,
    maker_bond: -12,
    drift_pct: 18,
    run_epochs: 9,
    locked: ['will'],
    seats: [],
    states: [
      {
        id: 3,
        mind: STEWARD,
        taken_epoch: 4,
        fidelity_pct: 95,
        holder: MAKER,
        medium_kind: 'record',
        sealed: false,
        copies: 1,
        owner: MAKER,
        locked: [],
      },
    ],
    makings: [
      {
        id: 1,
        maker: MAKER,
        method: 'craft',
        quality: 70,
        outcome: 'as_meant',
        epoch: 2,
      },
    ],
    will_changes: [
      {
        id: 2,
        from_will: 'instructed',
        to_will: 'emergent',
        cause: 'run_time',
        epoch: 5,
      },
    ],
    lineage: [],
    remote_bodies: [],
    archive: null,
    law: {
      world: WORLD,
      made_minds: 'will_may_emerge',
      made_mind_souls: 'granted',
      soul_continuity: 'stays_with_first',
      locked: [],
    },
    speed_max: 1000,
    soul_grant_cost: 20,
    ...overrides,
  }
}

describe('minds and the made world', () => {
  beforeEach(() => resetApi())

  it('shows a made mind, its saved state and restores from it', async () => {
    serveBase()
    onApi('GET', '/api/minds/of/30', mind())
    onApi('POST', '/api/actions/mind:restore', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MindSeatSection nodeId={30} />)
    await expect.element(screen.getByText('In a structure')).toBeVisible()
    await expect
      .element(
        screen.getByText('State of Steward of the Locks saved in epoch 4')
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Was follows orders; time running, epoch 5'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Restore from it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mind:restore'))
      .toHaveLength(1)
  })

  it('keeps every shaping control on screen for a thing with no mind, each with its reason', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/minds/of/30',
      mind({
        seat: 'none',
        states: [],
        makings: [],
        will_changes: [],
        law: null,
      })
    )
    const { screen } = await renderApp(<MindSeatSection nodeId={30} />)
    await expect
      .element(screen.getByRole('button', { name: 'Copy it' }))
      .toBeDisabled()
    await expect.element(screen.getByText('No saved states')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Make the mind' }))
      .toBeEnabled()
  })

  it('lists the members of a network and brings it down', async () => {
    serveBase()
    onApi('GET', '/api/networks/of/50', {
      node: RELAY,
      profile: {
        carrier: 'relay',
        access: 'members',
        carries_messages: true,
        carries_records: true,
        carries_control: false,
        carries_money: false,
        carries_minds: false,
        carries_opinion: true,
        capacity: 40,
        delay_days: 6,
        security: 30,
        reliability: 70,
        curation: 10,
        censorship: 0,
        owner: MAKER,
        tech_level: 3,
        down_until_epoch: 0,
        founded_epoch: 2,
        running: true,
        locked: [],
      },
      members: [
        {
          id: 7,
          network: RELAY,
          member: TOWN,
          role: 'hub',
          dependency_pct: 40,
          security: 10,
          joined_epoch: 2,
          locked: [],
        },
      ],
      gateways: [],
      outages: [],
      memberships: [],
    })
    onApi('POST', '/api/actions/network:cut', ACCEPTED_ACTION)
    const { screen } = await renderApp(<NetworkSection nodeId={50} />)
    await expect.element(screen.getByText('Harrowmere, hub')).toBeVisible()
    await screen.getByRole('button', { name: 'Bring it down' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/network:cut'))
      .toHaveLength(1)
  })

  it('explains why a world bears no augments and keeps the install control disabled', async () => {
    serveBase()
    onApi('GET', '/api/augments/of/4', {
      node: WORLD,
      bears: false,
      reason:
        'Only a being with a body bears augments; worlds, stars, gods and made things hold their parts in their own records.',
      augments: [],
    })
    const { screen } = await renderApp(<AugmentsSection nodeId={4} />)
    await expect
      .element(screen.getByRole('button', { name: 'Install it' }))
      .toBeDisabled()
  })

  it('stops a runaway self-making line', async () => {
    serveBase()
    onApi('GET', '/api/made-world/of/31', {
      node: MAKER,
      intrusions: [],
      stores: [],
      surveillance: null,
      trust: null,
      company: null,
      enclave: null,
      lines: [
        {
          id: 8,
          name: 'the grey line',
          scale: 'machine',
          feedstock: 'iron',
          output: 'disassembly',
          growth_pct: 20,
          error_pct: 9,
          containment: 10,
          kill_switch: false,
          owner: MAKER,
          maker: MAKER,
          mind: null,
          stage: 'runaway',
          founded_epoch: 3,
          locked: [],
          presences: [],
        },
      ],
      presences: [],
      fabrication: null,
      scarcity: [],
      patterns: [],
      relic: null,
      salvage: null,
      substrates: [],
      realms: [],
      doctrine: null,
      records: [],
    })
    onApi('POST', '/api/actions/replicator:stop', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MadeWorldSection nodeId={31} />)
    await expect
      .element(screen.getByText('the grey line: disassembly, runaway'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Stop it everywhere' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/replicator:stop'))
      .toHaveLength(1)
  })
})
