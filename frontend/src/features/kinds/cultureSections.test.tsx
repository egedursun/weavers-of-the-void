import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DressSection,
  EmblemsSection,
  MusicSection,
  SubstancesSection,
} from './CultureSections'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PEOPLE = { id: 41, kind: 'entity' as const, name: 'The Oru' }

function info(concept: string, label: string, plural: string) {
  return {
    concept,
    label,
    plural,
    hint: `${plural} a people holds`,
    categories: [{ key: 'first', label: `First ${label.toLowerCase()}` }],
    properties: [
      {
        column: 'prestige',
        label: 'Prestige',
        hint: 'Standing it lends',
        low: 0,
        high: 100,
        options: [],
      },
    ],
  }
}

const CONCEPTS = [
  info('garment', 'Garment', 'Garments'),
  info('colour_term', 'Colour term', 'Colour terms'),
  info('scent', 'Scent', 'Scents'),
  info('emblem_system', 'Emblem system', 'Emblem systems'),
  info('instrument', 'Instrument', 'Instruments'),
  info('music_tradition', 'Musical tradition', 'Musical traditions'),
  info('substance', 'Substance', 'Substances'),
]

const ROBE = {
  id: 5,
  concept: 'garment' as const,
  name: 'High robe',
  description: null,
  category: 'first',
  category_label: 'First garment',
  world: null,
  origin: PEOPLE,
  derived_from_id: null,
  derived_from_name: null,
  built_in: false,
  retired: false,
  created_epoch: 2,
  locked: [],
  values: [{ column: 'prestige', value: 40, option: null, option_label: null }],
  holders: [PEOPLE],
}

function serve(holdings: unknown[]) {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/kinds/concepts', CONCEPTS)
  onApi('GET', '/api/kinds/garment', [ROBE])
  for (const concept of [
    'colour_term',
    'scent',
    'emblem_system',
    'instrument',
    'music_tradition',
    'substance',
  ])
    onApi('GET', `/api/kinds/${concept}`, [])
  onApi('GET', '/api/kinds/of/41', { node: PEOPLE, holdings, made: [] })
}

const WORN = {
  id: 9,
  concept: 'garment',
  kind_id: 5,
  kind_name: 'High robe',
  category_label: 'First garment',
  stance: 'uses',
  strength: 70,
  spread: 'contact',
  since_epoch: 3,
  locked: [],
}

describe('the culture sections', () => {
  beforeEach(() => resetApi())

  it('shows the dress a people holds with how it holds it, and an empty scent block', async () => {
    serve([WORN])
    const { screen } = await renderApp(<DressSection nodeId={41} />)
    await expect.element(screen.getByText('High robe').first()).toBeVisible()
    await expect
      .element(screen.getByText(/strength 70 of 100 · .* · since epoch 3/))
      .toBeVisible()
    await expect
      .element(screen.getByText('It holds no scents yet'))
      .toBeVisible()
  })

  it('makes a new kind for the people and keeps the button disabled until it is named', async () => {
    serve([])
    onApi('POST', '/api/actions/authored_kind:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SubstancesSection nodeId={41} />)
    const make = screen.getByRole('button', { name: 'Make the substance' })
    await expect.element(make).toBeDisabled()
    await screen.getByLabelText('Name of the substance').fill('Bitterleaf')
    await make.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:create')[0].body
    ).toMatchObject({
      concept: 'substance',
      name: 'Bitterleaf',
      category: 'first',
      origin_node_id: 41,
    })
  })

  it('shows emblems and music with their own blocks and keeps them closed when read-only', async () => {
    serve([])
    const { screen } = await renderApp(
      <>
        <EmblemsSection nodeId={41} readOnlyReason='The world is read-only' />
        <MusicSection nodeId={41} />
      </>
    )
    await expect
      .element(screen.getByText('It holds no emblem systems yet'))
      .toBeVisible()
    await expect
      .element(screen.getByText('It holds no musical traditions yet'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Make the emblem system' }))
      .toBeDisabled()
  })

  it('says so when its ways of life cannot be read', async () => {
    serve([])
    onApi('GET', '/api/kinds/of/41', failure(500, 'down'))
    const { screen } = await renderApp(<MusicSection nodeId={41} />)
    await expect
      .element(screen.getByText('Its ways of life could not be read'))
      .toBeVisible()
  })
})
