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
  OrganisationKindsSection,
  RankKindsSection,
  WorkSection,
} from './SocietySections'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const ORDER = { id: 52, kind: 'entity' as const, name: 'The Quiet Hand' }

function info(concept: string, label: string, plural: string) {
  return {
    concept,
    label,
    plural,
    hint: `${plural} a body holds`,
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
  info('profession', 'Profession', 'Professions'),
  info('rank', 'Rank', 'Ranks'),
  info('organisation', 'Form of organisation', 'Forms of organisation'),
]

const CIRCLE = {
  id: 7,
  concept: 'organisation' as const,
  name: 'Sworn circle',
  description: null,
  category: 'first',
  category_label: 'First form of organisation',
  world: null,
  origin: ORDER,
  derived_from_id: null,
  derived_from_name: null,
  built_in: false,
  retired: false,
  created_epoch: 4,
  locked: [],
  values: [{ column: 'prestige', value: 55, option: null, option_label: null }],
  holders: [ORDER],
}

const HELD = {
  id: 11,
  concept: 'organisation',
  kind_id: 7,
  kind_name: 'Sworn circle',
  category_label: 'First form of organisation',
  stance: 'makes',
  strength: 80,
  spread: 'invented',
  since_epoch: 4,
  locked: [],
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
  onApi('GET', '/api/kinds/organisation', [CIRCLE])
  onApi('GET', '/api/kinds/profession', [])
  onApi('GET', '/api/kinds/rank', [])
  onApi('GET', '/api/kinds/of/52', { node: ORDER, holdings, made: [] })
}

describe('the society kind sections', () => {
  beforeEach(() => resetApi())

  it('shows the form a faction takes with how strongly it holds it', async () => {
    serve([HELD])
    const { screen } = await renderApp(<OrganisationKindsSection nodeId={52} />)
    await expect.element(screen.getByText('Sworn circle').first()).toBeVisible()
    await expect
      .element(screen.getByText(/strength 80 of 100 · .* · since epoch 4/))
      .toBeVisible()
  })

  it('makes a rank for the body and keeps the button disabled until it is named', async () => {
    serve([])
    onApi('POST', '/api/actions/authored_kind:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RankKindsSection nodeId={52} />)
    const make = screen.getByRole('button', { name: 'Make the rank' })
    await expect.element(make).toBeDisabled()
    await screen.getByLabelText('Name of the rank').fill('Keeper of keys')
    await make.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:create')[0].body
    ).toMatchObject({
      concept: 'rank',
      name: 'Keeper of keys',
      category: 'first',
      origin_node_id: 52,
    })
  })

  it('shows an empty professions block and keeps it closed when read-only', async () => {
    serve([])
    const { screen } = await renderApp(
      <WorkSection nodeId={52} readOnlyReason='The world is read-only' />
    )
    await expect
      .element(screen.getByText('It holds no professions yet'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Make the profession' }))
      .toBeDisabled()
  })

  it('says so when its ways of life cannot be read', async () => {
    serve([])
    onApi('GET', '/api/kinds/of/52', failure(500, 'down'))
    const { screen } = await renderApp(<WorkSection nodeId={52} />)
    await expect
      .element(screen.getByText('Its ways of life could not be read'))
      .toBeVisible()
  })
})
