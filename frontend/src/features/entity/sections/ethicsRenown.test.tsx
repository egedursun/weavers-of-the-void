import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EthicsSection } from './EthicsSection'
import { RenownSection } from './RenownSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const FOLK = { id: 41, name: 'Grimfolk', kind: 'entity', type: 'people' }
const TOWN = { id: 40, name: 'Grimsby', kind: 'entity', type: 'settlement' }
const ORLA = { id: 32, name: 'Orla', kind: 'entity', type: 'mortal' }

const STANCES = [
  { key: 'required', label: 'Required' },
  { key: 'admirable', label: 'Admirable' },
  { key: 'acceptable', label: 'Acceptable' },
  { key: 'frowned_upon', label: 'Frowned upon' },
  { key: 'shameful', label: 'Shameful' },
  { key: 'unthinkable', label: 'Unthinkable' },
]

const MIND = {
  node_id: 41,
  name: 'Grimfolk',
  has_preferences: false,
  has_ethics: true,
  ethics_holder: FOLK,
  ethics_own: true,
  preferences: [],
  totem: null,
  ethics: [
    {
      act: 'fixing_contests',
      label: 'Fixing contests',
      stance: 'shameful',
      reading: -40,
      since_epoch: 4,
      held: false,
    },
    {
      act: 'mercy_to_enemy',
      label: 'Mercy to an enemy',
      stance: 'admirable',
      reading: 30,
      since_epoch: 5,
      held: true,
    },
  ],
  honour_model: 'face',
  honour_label: 'Face',
  honour_held: false,
  preference_kinds: [],
  stances: STANCES,
  honour_models: [
    { key: 'dignity', label: 'Dignity' },
    { key: 'face', label: 'Face' },
  ],
}

function serve(readOnly = false) {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: readOnly,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { ...FOLK, world_id: 4 },
    { ...TOWN, world_id: 4 },
    { ...ORLA, world_id: 4 },
  ])
}

const RENOWN = {
  node_id: 32,
  name: 'Orla',
  glory: 40,
  infamy: 5,
  reputations: [
    {
      id: 9,
      subject: ORLA,
      community: TOWN,
      axis: 'mercy',
      label: 'Mercy',
      skill: null,
      value: 60,
      heard_epoch: 5,
      held: false,
    },
    {
      id: 10,
      subject: ORLA,
      community: TOWN,
      axis: 'skill_renown',
      label: 'Renown for a skill',
      skill: 'blade',
      value: 45,
      heard_epoch: 6,
      held: true,
    },
  ],
  views: [],
  standing: null,
  ruler: false,
  deeds: [],
  trades: [],
  axes: [
    { key: 'heroism', label: 'Heroism' },
    { key: 'mercy', label: 'Mercy' },
    { key: 'justice', label: 'Justice' },
  ],
  claim_kinds: [],
  claim_statuses: [],
  lore_kinds: [],
}

describe('ethics', () => {
  beforeEach(resetApi)

  it('names each act and the honour model by their labels and sets a stance', async () => {
    serve()
    onApi('GET', '/api/minds/41/culture', MIND)
    onApi('POST', '/api/actions/ethics:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EthicsSection nodeId={41} />)
    await expect.element(screen.getByText('Fixing contests')).toBeVisible()
    await expect.element(screen.getByText('Mercy to an enemy')).toBeVisible()
    await expect.element(screen.getByText('Since epoch 5 · held')).toBeVisible()
    await expect.element(screen.getByText('Face').first()).toBeVisible()
    await expect.element(screen.getByText('Shameful: 1')).toBeVisible()
    expect(screen.container.textContent).not.toContain('fixing_contests')
    await screen.getByRole('combobox', { name: 'Stance' }).first().click()
    await screen.getByRole('option', { name: 'Unthinkable' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/ethics:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/ethics:set')[0].body).toEqual({
      holder_id: 41,
      act: 'fixing_contests',
      stance: 'unthinkable',
      hold: true,
    })
  })

  it('points a mortal to the ethics of its people and keeps the stances locked there', async () => {
    serve()
    onApi('GET', '/api/minds/32/culture', {
      ...MIND,
      node_id: 32,
      name: 'Orla',
      ethics_own: false,
    })
    const { screen } = await renderApp(<EthicsSection nodeId={32} />)
    await expect
      .element(screen.getByText('Living by the ethics of'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('combobox', { name: 'Stance' }).first())
      .toBeDisabled()
  })

  it('says a people without ethics yet will have them read', async () => {
    serve()
    onApi('GET', '/api/minds/41/culture', {
      ...MIND,
      ethics: [],
      honour_model: null,
      honour_label: null,
    })
    const { screen } = await renderApp(<EthicsSection nodeId={41} />)
    await expect.element(screen.getByText('No ethics yet')).toBeVisible()
    await expect.element(screen.getByText('None')).toBeVisible()
  })
})

describe('renown', () => {
  beforeEach(resetApi)

  it('names mercy and a skill by their labels and spreads a name for justice', async () => {
    serve()
    onApi('GET', '/api/renown/32', RENOWN)
    onApi('POST', '/api/actions/renown:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RenownSection nodeId={32} />)
    await expect
      .element(screen.getByText('Mercy · heard in epoch 5'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Renown for a skill (blade) · heard in epoch 6')
      )
      .toBeVisible()
    expect(screen.container.textContent).not.toContain('skill_renown')
    const spread = screen.getByRole('button', { name: 'Spread', exact: true })
    await expect
      .element(spread.first())
      .toHaveAccessibleDescription('Pick who or where first.')
    await screen.getByRole('combobox', { name: 'Where' }).click()
    await screen.getByRole('option', { name: /Grimsby/ }).click()
    await screen.getByRole('combobox', { name: 'Known for' }).first().click()
    await screen.getByRole('option', { name: 'Justice' }).click()
    await spread.first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/renown:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/renown:set')[0].body).toEqual({
      subject_id: 32,
      community_id: 40,
      axis: 'justice',
      value: 50,
      hold: true,
    })
  })

  it('says no community knows them yet and keeps Spread with the read-only reason', async () => {
    serve(true)
    onApi('GET', '/api/renown/32', { ...RENOWN, reputations: [] })
    const { screen } = await renderApp(<RenownSection nodeId={32} />)
    await expect
      .element(screen.getByText('No community knows them for anything yet.'))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('button', { name: 'Spread', exact: true }).first()
      )
      .toHaveAccessibleDescription('A guest world is open read-only.')
  })
})
