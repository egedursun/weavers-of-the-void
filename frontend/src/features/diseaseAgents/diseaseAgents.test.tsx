import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DiseaseAgentsSection } from './DiseaseAgentsSection'

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

const rows = {
  table: 'disease_agents',
  label: 'Disease agents',
  columns: [
    column('disease_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('agent', 'choice', { options: ['virus', 'bacterium'] }),
    column('overuse', 'integer'),
  ],
  rows: [
    {
      key: { disease_entity_id: 7 },
      values: { disease_entity_id: 7, agent: 'bacterium', overuse: 10 },
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

describe('the agents of disease section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/disease_agent:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DiseaseAgentsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Agents of disease', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open disease agents' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open disease agents' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease_agent:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/disease_agent:delete')[0].body
    ).toEqual({
      table: 'disease_agents',
      key: { disease_entity_id: 7 },
    })
  })
})
