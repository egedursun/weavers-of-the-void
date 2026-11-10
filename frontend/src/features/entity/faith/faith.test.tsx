import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VIEW } from '@/features/cosmography/cosmographyFixtures'
import { AfterlifeSection, SoulSection } from './Afterlife'
import { DoctrineSection } from './Doctrine'
import { PossessedSection } from './Possessed'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const CULT = { id: 5, kind: 'entity', name: 'Church of Ilun' }
const GOD = { id: 2, kind: 'son', name: 'Ilun' }
const TOWN = { id: 30, kind: 'entity', name: 'Ilunford' }
const PRIEST = { id: 31, kind: 'entity', name: 'Abbot Ren' }
const SAINT = { id: 32, kind: 'entity', name: 'Saint Eda' }
const BONES = { id: 33, kind: 'entity', name: 'Bones of Saint Eda' }
const TONGUE = { id: 34, kind: 'entity', name: 'Old Chant' }
const SECT = { id: 35, kind: 'entity', name: 'The Grey Sect' }
const SHADE = { id: 40, kind: 'entity', name: 'Shade of Ardo' }
const HOST = { id: 41, kind: 'entity', name: 'Vessel' }
const REGION = { id: 50, kind: 'entity', name: 'Vale of Mist' }

const DOCTRINE = {
  cult: CULT,
  god: GOD,
  judgement: 'deeds',
  orthodoxy: 60,
  tithe_rate: 10,
  treasury: 120,
  clergy_count: 14,
  clergy_quality: 55,
  zeal: 62,
  zeal_parts: { preaching: 4, 'doom omens': 6 },
  fanaticism: null,
  fanaticism_epoch: null,
  doctrinal_distance: 12,
  excommunicated: [],
  members: [TOWN],
  locked: ['orthodoxy'],
  tenets: [
    {
      tenet: 'pilgrimage_duty',
      name: 'The Long Walk',
      effect: 'The faithful must journey to a holy place.',
      target: '30',
      target_name: 'Ilunford',
      since_epoch: 2,
      revealed_by_son_id: 2,
    },
  ],
  holdings: [{ kind: 'land', holding: TOWN, since_epoch: 1 }],
  clergy: [
    { kind: 'high_priest', holder: PRIEST, since_epoch: 3, locked: true },
  ],
  heresies: [
    {
      heresy: SECT,
      parent: CULT,
      distance: 40,
      declared_epoch: 3,
      suppressed: true,
      tolerated: false,
      locked: [],
    },
  ],
  mother: null,
  relics: [
    {
      item: BONES,
      saint: SAINT,
      shrine: TOWN,
      sanctity: 70,
      pilgrims: 300,
      canonised_epoch: 3,
      cult: CULT,
      locked: ['sanctity'],
    },
  ],
  rebirth_path: 'house',
  liturgical_language: TONGUE,
  liturgy_reach: 50,
  parent_cult: null,
  devotion: 44,
  state_realm: null,
  clergy_sway: 0,
  god_king: null,
  tithe_base: [TOWN],
  realm_population: 9,
}

const SOUL = {
  spirit: SHADE,
  origin: null,
  patron_son_id: 2,
  patron_name: 'Ilun',
  state: 'in_realm',
  alignment: 'vengeful',
  binding: 'person',
  bound: HOST,
  rite: 'nameless',
  sealed: true,
  seal_strength: 60,
  memory_strength: 70,
  veneration: 10,
  unrest: 80,
  imprint: { mercy: -60 },
  traits: ['wrathful'],
  deeds: { renown: 20, honour: 30, faith: 40, violence: 50, infamy: 60 },
  stratum: null,
  judgements: [],
  possessing: HOST,
  possession: {
    host: HOST,
    spirit: SHADE,
    since_epoch: 4,
    stress: 35,
    host_values: { mercy: 20 },
    locked: [],
  },
  reborn_as: null,
  gate: null,
  locked: ['rite'],
}

const STRATUM = {
  id: 7,
  kind: 'paradise',
  name: 'Hall of Heroes',
  criteria: { priority: 5, renown_at_least: 70, tenets_any: ['holy_war'] },
  population: 3,
  souls: [SHADE],
  realm: REGION,
  closed: false,
  son_id: 2,
  son_name: 'Ilun',
  cult: null,
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 5 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
  onApi('GET', '/api/tenets/kinds', [])
}

describe('faith sections', () => {
  beforeEach(resetApi)

  it('shows devotion, liturgy and rebirth, and holds a clergy appointment loose', async () => {
    serve()
    onApi('GET', '/api/entities/5/doctrine', DOCTRINE)
    onApi('POST', '/api/actions/cult:office', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DoctrineSection cultId={5} />)
    await expect
      .element(screen.getByText('Souls reborn into its house'))
      .toBeVisible()
    await expect.element(screen.getByText('Liturgy in Old Chant')).toBeVisible()
    await expect.element(screen.getByText('The Long Walk')).toBeVisible()
    await expect.element(screen.getByText('Devotion').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Appoint' }).click()
    await screen
      .getByRole('button', { name: 'Let the faith choose again' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cult:office'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/cult:office')[0].body).toMatchObject({
      cult_id: 5,
      kind: 'high_priest',
      locked: false,
    })
  })

  it('tends a relic and forgives a heresy', async () => {
    serve()
    onApi('GET', '/api/entities/5/doctrine', DOCTRINE)
    onApi('POST', '/api/actions/relic:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/cult:undeclare_heresy', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DoctrineSection cultId={5} />)
    await screen.getByRole('button', { name: 'Tend the relic' }).click()
    await screen.getByRole('button', { name: 'Let pilgrims decide' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/relic:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/relic:edit')[0].body).toEqual({
      item_id: 33,
      values: {},
      release: ['sanctity'],
    })
    await screen.getByRole('button', { name: 'Shape the heresy' }).click()
    await screen.getByRole('button', { name: 'Forgive and unname it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cult:undeclare_heresy'))
      .toHaveLength(1)
  })

  it('shows the seal and possession of a soul and drives the spirit out', async () => {
    serve()
    onApi('GET', '/api/entities/40/soul', SOUL)
    onApi('GET', '/api/entities/40/afterlife', {
      realm: null,
      strata: [],
      realms: [],
      gods: [],
    })
    onApi('POST', '/api/actions/soul:exorcise', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SoulSection spiritId={40} />)
    await expect
      .element(screen.getByText('Sealed against rebirth').first())
      .toBeVisible()
    await expect
      .element(screen.getByText('Buried nameless').first())
      .toBeVisible()
    await expect.element(screen.getByText('Mercy 20')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust the possession' }).click()
    await screen.getByRole('button', { name: 'Drive it out' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/soul:exorcise'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/soul:exorcise')[0].body).toEqual({
      host_id: 41,
    })
  })

  it('shows the spirit that possesses a mortal and drives it out from the host', async () => {
    serve()
    onApi('GET', '/api/entities/41/possession', SOUL.possession)
    onApi('POST', '/api/actions/soul:exorcise', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PossessedSection hostId={41} />)
    await expect.element(screen.getByText('Possessed by')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust the possession' }).click()
    await screen.getByRole('button', { name: 'Drive it out' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/soul:exorcise'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/soul:exorcise')[0].body).toEqual({
      host_id: 41,
    })
  })

  it('reads a stratum as typed rules and closes its gates', async () => {
    serve()
    onApi('GET', '/api/entities/50/afterlife', {
      realm: REGION,
      strata: [STRATUM],
      realms: [REGION],
      gods: [{ son_id: 2, name: 'Ilun', souls: 3 }],
    })
    onApi('POST', '/api/actions/afterlife:stratum', ACCEPTED_ACTION)
    const { screen } = await renderApp(<AfterlifeSection regionId={50} />)
    await expect.element(screen.getByText('Renown at least 70')).toBeVisible()
    await expect.element(screen.getByText('Only for Ilun')).toBeVisible()
    await expect.element(screen.getByText('Faith holds Holy war')).toBeVisible()
    await screen.getByRole('button', { name: 'Shape the stratum' }).click()
    await screen.getByRole('button', { name: 'Close its gates' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/afterlife:stratum'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/afterlife:stratum')[0].body
    ).toMatchObject({
      realm_id: 50,
      stratum_id: 7,
      closed: true,
    })
  })

  it('sets the dimension a stratum lies in', async () => {
    serve()
    onApi('GET', '/api/cosmography', VIEW)
    onApi('GET', '/api/entities/50/afterlife', {
      realm: REGION,
      strata: [STRATUM],
      realms: [REGION],
      gods: [],
    })
    onApi('POST', '/api/actions/afterlife:stratum', ACCEPTED_ACTION)
    const { screen } = await renderApp(<AfterlifeSection regionId={50} />)
    await screen.getByRole('button', { name: 'Shape the stratum' }).click()
    await screen
      .getByRole('combobox', { name: 'Lies in the dimension' })
      .click()
    await screen.getByRole('option', { name: 'Aerona Prime' }).click()
    await screen.getByRole('button', { name: 'Set the rules' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/afterlife:stratum'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/afterlife:stratum')[0].body
    ).toMatchObject({
      stratum_id: 7,
      dimension_id: 101,
      clear_dimension: false,
    })
  })
})
