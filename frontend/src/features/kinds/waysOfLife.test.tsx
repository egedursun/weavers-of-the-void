import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WaysOfLifeSection } from './WaysOfLifeSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PEOPLE = { id: 12, kind: 'entity' as const, name: 'The Oru' }
const SON = { id: 2, kind: 'son' as const, name: 'Ithren' }
const GOODS = {
  concept: 'good' as const,
  label: 'Good',
  plural: 'Goods',
  hint: 'Things a people grows, gathers, makes or trades',
  categories: [{ key: 'grain', label: 'Grain' }],
  properties: [
    { column: 'bulk', label: 'Bulk', hint: 'Room it takes', low: 0, high: 100 },
  ],
}
const ASHGRAIN = {
  id: 3,
  concept: 'good' as const,
  name: 'Ashgrain',
  description: null,
  category: 'grain',
  category_label: 'Grain',
  world: null,
  origin: PEOPLE,
  derived_from_id: null,
  derived_from_name: null,
  built_in: false,
  retired: false,
  created_epoch: 2,
  locked: [],
  values: [{ column: 'bulk', value: 30 }],
  holders: [PEOPLE],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/kinds/concepts', [GOODS])
  onApi('GET', '/api/kinds/good', [ASHGRAIN])
}

describe('the ways of life section', () => {
  beforeEach(() => resetApi())

  it('shows what a people holds and made, edits a holding and lets one go', async () => {
    serveBase()
    onApi('GET', '/api/kinds/of/12', {
      node: PEOPLE,
      holdings: [
        {
          id: 40,
          concept: 'good',
          kind_id: 3,
          kind_name: 'Ashgrain',
          category_label: 'Grain',
          stance: 'makes',
          strength: 60,
          spread: 'trade',
          since_epoch: 3,
          locked: [],
        },
      ],
      made: [ASHGRAIN],
    })
    onApi('POST', '/api/actions/record_row:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/record_row:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WaysOfLifeSection nodeId={12} />)
    await expect.element(screen.getByText('Makes it: Ashgrain')).toBeVisible()
    await expect.element(screen.getByText(/came by trade/)).toBeVisible()
    await expect.element(screen.getByText(/held by 1 holder/)).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen
      .getByRole('spinbutton', { name: 'Strength of the hold' })
      .fill('90')
    await screen.getByRole('button', { name: 'Hold these values' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/record_row:edit'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/record_row:edit')[0].body
    ).toMatchObject({
      table: 'kind_holdings',
      key: { id: 40 },
      values: { strength: 90 },
    })
    await screen.getByRole('button', { name: 'Let it go' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/record_row:delete'))
      .toHaveLength(1)
  })

  it('lets a god bless a kind, with the control disabled until a kind is picked', async () => {
    serveBase()
    onApi('GET', '/api/kinds/of/2', { node: SON, holdings: [], made: [] })
    onApi('POST', '/api/actions/authored_kind:spread', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WaysOfLifeSection nodeId={2} />)
    await expect
      .element(screen.getByText('It holds no kinds yet'))
      .toBeVisible()
    const bless = screen.getByRole('button', { name: 'Set the blessing' })
    await expect.element(bless).toBeDisabled()
    await screen.getByRole('combobox', { name: 'Which one' }).click()
    await screen.getByRole('option', { name: 'Ashgrain (Grain)' }).click()
    await bless.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:spread'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:spread')[0].body
    ).toMatchObject({
      concept: 'good',
      kind_id: 3,
      holder_node_id: 2,
      stance: 'blesses',
    })
  })

  it('says so when its ways of life cannot be read', async () => {
    serveBase()
    onApi('GET', '/api/kinds/of/12', failure(500, 'The archive is closed.'))
    const { screen } = await renderApp(<WaysOfLifeSection nodeId={12} />)
    await expect
      .element(screen.getByText('Its ways of life could not be read'))
      .toBeVisible()
  })
})
