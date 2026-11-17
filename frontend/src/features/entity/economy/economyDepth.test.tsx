import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HoardControl } from './HoardControl'
import { NodeMaterials } from './NodeMaterials'
import { PriceHolds } from './PriceHolds'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WORLD = 4
const COMMUNITY = 960
const NODE = 77

function material(kind: string, label: string, family: string) {
  return {
    kind,
    world_material_id: null,
    label,
    family,
    origin: 'catalog',
    source: 'world',
    edited: false,
    hardness: 50,
    toughness: 50,
    weight: 50,
    edge: 50,
    conductivity: 50,
    sanctity: 50,
    corruption: 0,
    rarity: 50,
    base_value: 50,
    decay: 10,
    branch: null,
    level: 0,
    gate: null,
    description: null,
    deposit_id: null,
    held: false,
    base_kind: null,
    price_premium_pct: 100,
    worth_pct: 100,
    melting_point: 68,
    ignition_point: 100,
    boiling_point: 90,
    density: 72,
    impact_yield: 60,
    impact_fracture: 70,
    shear_yield: 58,
    shear_fracture: 68,
    elasticity: 30,
    thermal_conductivity: 60,
    solid_density: 75,
    max_edge: 65,
  }
}

const NODE_MATERIALS = {
  node_id: NODE,
  entity_type: 'army',
  world_id: WORLD,
  slots: [
    {
      slot: 'weapons',
      material: 'silver',
      world_material_id: null,
      label: 'Silver',
      family: 'precious',
      held: true,
      hardness: 30,
      toughness: 30,
      weight: 55,
      sanctity: 70,
      corruption: 0,
      rarity: 70,
      base_value: 75,
      decay: 5,
      effects: { damage: 12, holy_edge_pct: 180, battle_wear: 3 },
    },
  ],
  open_slots: ['armour'],
  foe_natures: ['undead'],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', `/api/worlds/${WORLD}/materials`, {
    materials: [
      material('gold', 'Gold', 'precious'),
      material('silver', 'Silver', 'precious'),
      material('iron', 'Iron', 'metal'),
    ],
  })
  onApi('GET', `/api/nodes/${NODE}/materials`, NODE_MATERIALS)
  onApi('GET', `/api/markets/${COMMUNITY}/holds`, {
    market_id: COMMUNITY,
    premiums: [
      {
        commodity: 'luxuries',
        premium_pct: 136,
        held_price: 150,
        held_supply: null,
      },
      {
        commodity: 'tools',
        premium_pct: 90,
        held_price: null,
        held_supply: null,
      },
    ],
  })
  for (const action of [
    'hoard:inject',
    'node_material:set',
    'node_material:release',
    'market:hold_price',
    'market:release_price',
  ])
    onApi('POST', `/api/actions/${action}`, ACCEPTED_ACTION)
}

describe('economy depth controls', () => {
  beforeEach(resetApi)

  it('pours a hoard of a luxury metal into the market', async () => {
    serve()
    const { screen } = await renderApp(
      <HoardControl communityId={COMMUNITY} worldId={WORLD} />
    )
    await expect
      .element(screen.getByText(/Floods the luxury price index/))
      .toBeVisible()
    await screen.getByRole('combobox', { name: 'Hoard of' }).click()
    await screen.getByRole('option', { name: 'Silver' }).click()
    await screen.getByRole('spinbutton', { name: 'Hoard units' }).fill('25')
    await screen.getByRole('button', { name: 'Pour the hoard' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/hoard:inject').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/hoard:inject')[0]?.body).toEqual({
      community_id: COMMUNITY,
      metal: 'silver',
      world_material_id: null,
      units: 25,
    })
  })

  it('shows what a node is made of, releases a held slot and sets an open one', async () => {
    serve()
    const { screen } = await renderApp(<NodeMaterials nodeId={NODE} />)
    await expect.element(screen.getByText('Weapons of silver')).toBeVisible()
    await expect
      .element(screen.getByText('Undead', { exact: true }))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'Holy edge vs the undead, the cursed and the void 180%'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Loses 3 condition in each battle'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/node_material:release').length)
      .toBe(1)
    expect(
      callsTo('POST', '/api/actions/node_material:release')[0]?.body
    ).toEqual({ node_id: NODE, slot: 'weapons' })
    await screen.getByRole('button', { name: 'Set the armour' }).click()
    await screen.getByRole('combobox', { name: 'Armour material' }).click()
    await screen.getByRole('option', { name: 'Iron' }).click()
    await screen.getByRole('button', { name: 'Make the armour of it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/node_material:set').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/node_material:set')[0]?.body).toEqual({
      node_id: NODE,
      slot: 'armour',
      material: 'iron',
      world_material_id: null,
      hold: true,
    })
  })

  it('lists material premiums with held prices, releases and holds one', async () => {
    serve()
    const { screen } = await renderApp(<PriceHolds marketId={COMMUNITY} />)
    await expect
      .element(screen.getByText('Luxuries: 136% of base price'))
      .toBeVisible()
    await expect.element(screen.getByText('Price held at 150')).toBeVisible()
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/market:release_price').length)
      .toBe(1)
    expect(
      callsTo('POST', '/api/actions/market:release_price')[0]?.body
    ).toEqual({ market_id: COMMUNITY, commodity: 'luxuries' })
    await screen.getByRole('button', { name: 'Hold a price' }).click()
    await screen.getByRole('spinbutton', { name: 'Held price' }).fill('120')
    await screen.getByRole('button', { name: 'Hold it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/market:hold_price').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/market:hold_price')[0]?.body).toEqual({
      market_id: COMMUNITY,
      commodity: 'grain',
      price: 120,
      supply: null,
    })
  })
})
