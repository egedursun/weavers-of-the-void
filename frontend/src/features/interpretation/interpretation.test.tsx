import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InterpretationSection } from './InterpretationSection'

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

const readings = {
  table: 'interpretations',
  label: 'Interpretations',
  columns: [
    column('first_party_id', 'integer', { owner: true, editable: false }),
    column('fault', 'choice', { options: ['none', 'slanted'] }),
    column('fidelity', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { first_party_id: 7, fault: 'slanted', fidelity: 60 },
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

describe('interpretation section', () => {
  beforeEach(() => resetApi())

  it('shows only the words carried between tongues and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [readings, tags],
      creatable: [readings, tags],
      names: {},
    })
    onApi('POST', '/api/actions/interpretation:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<InterpretationSection nodeId={7} />)
    await expect
      .element(screen.getByText('Words between tongues', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open interpretations' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/interpretation:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/interpretation:delete')[0].body
    ).toEqual({
      table: 'interpretations',
      key: { id: 5 },
    })
  })
})
