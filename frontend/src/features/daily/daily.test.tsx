import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DailyLifeSection } from './DailyLifeSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const column = (name: string, kind: string, extra = {}) => ({
  name,
  kind,
  options: [],
  nullable: false,
  primary: false,
  owner: false,
  required: false,
  editable: true,
  ...extra,
})

const care = {
  table: 'care_customs',
  label: 'Care customs',
  columns: [
    column('people_entity_id', 'integer', {
      primary: true,
      owner: true,
      editable: false,
    }),
    column('wash_frequency', 'choice', {
      options: ['none', 'by_rite', 'seasonal', 'weekly', 'daily'],
    }),
    column('cleanliness', 'integer'),
  ],
  rows: [
    {
      key: { people_entity_id: 7 },
      values: { people_entity_id: 7, wash_frequency: 'daily', cleanliness: 70 },
      held: [],
    },
  ],
}

const tags = {
  table: 'entity_tags',
  label: 'Entity tags',
  columns: [column('tag', 'text')],
  rows: [{ key: { entity_id: 7, tag: 'x' }, values: { tag: 'x' }, held: [] }],
}

const housework = {
  table: 'housework',
  label: 'Housework',
  columns: [
    column('id', 'integer', { primary: true, editable: false }),
    column('duty', 'choice', {
      options: ['food', 'water', 'sickcare', 'household_rites'],
    }),
    column('doer_node_id', 'integer', { owner: true }),
    column('load', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { id: 3, duty: 'household_rites', doer_node_id: 7, load: 25 },
      held: ['load'],
    },
  ],
}

const pursuits = {
  table: 'leisure_pursuits',
  label: 'Leisure pursuits',
  columns: [
    column('id', 'integer', { primary: true, editable: false }),
    column('holder_node_id', 'integer', { owner: true, required: true }),
    column('kind', 'choice', {
      options: ['conversation', 'games', 'sport', 'collecting'],
      required: true,
    }),
    column('share', 'integer'),
  ],
  rows: [],
}

describe('daily life section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of daily life and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/care_custom:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DailyLifeSection nodeId={7} />)
    await expect.element(screen.getByText('Daily life')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open care customs' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open care customs' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/care_custom:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/care_custom:delete')[0].body).toEqual({
      table: 'care_customs',
      key: { people_entity_id: 7 },
    })
  })
  it('names a house duty by its words and gives a pursuit through its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [housework],
      creatable: [pursuits],
      names: {},
    })
    onApi('POST', '/api/actions/leisure_pursuit:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DailyLifeSection nodeId={7} />)
    const make = screen.getByRole('button', { name: 'Make it', exact: true })
    await expect
      .element(make)
      .toHaveAccessibleDescription('Choose a kind of record first.')
    await screen.getByRole('combobox', { name: 'Kind of record' }).click()
    await screen.getByRole('option', { name: /Leisure pursuits/ }).click()
    await make.click()
    const dialog = screen.getByRole('dialog')
    await expect
      .element(dialog.getByRole('button', { name: 'Make it', exact: true }))
      .toHaveAccessibleDescription('Fill in kind.')
    await dialog.getByRole('combobox', { name: 'Kind' }).click()
    await screen.getByRole('option', { name: 'Collecting' }).click()
    await dialog.getByRole('button', { name: 'Make it', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/leisure_pursuit:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/leisure_pursuit:create')[0].body
    ).toEqual({
      table: 'leisure_pursuits',
      values: { holder_node_id: 7, kind: 'collecting' },
    })
    await screen.getByRole('button', { name: 'Open housework' }).click()
    await expect.element(screen.getByText('Household rites')).toBeVisible()
    expect(screen.container.textContent).not.toContain('household_rites')
  })

  it('says what keeps daily life when nothing is kept yet', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [],
      creatable: [pursuits],
      names: {},
    })
    const { screen } = await renderApp(<DailyLifeSection nodeId={7} />)
    await expect
      .element(
        screen.getByText(/Nothing of daily life is kept for this thing yet/)
      )
      .toBeVisible()
  })
})
