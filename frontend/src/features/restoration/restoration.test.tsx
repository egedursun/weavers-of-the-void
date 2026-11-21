import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RestorationsSection } from './RestorationsSection'

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

const movements = {
  table: 'restorations',
  label: 'Restorations',
  columns: [
    column('fallen_polity_id', 'integer', { owner: true, editable: false }),
    column('stage', 'choice', {
      options: ['memory', 'movement', 'rising', 'restored', 'failed'],
    }),
    column('memory', 'integer'),
  ],
  rows: [
    {
      key: { id: 5 },
      values: { fallen_polity_id: 7, stage: 'movement', memory: 60 },
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

describe('restorations section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of restorations, carries one on and strikes it by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [movements, tags],
      creatable: [movements, tags],
      names: {},
    })
    onApi('POST', '/api/actions/restoration:delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/restoration:advance', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RestorationsSection nodeId={7} />)
    await expect
      .element(screen.getByText('Restorations', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open restorations' }).click()
    await screen
      .getByRole('button', { name: 'Carry it to its next stage' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/restoration:advance'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/restoration:advance')[0].body).toEqual(
      {
        record_id: 5,
      }
    )
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/restoration:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/restoration:delete')[0].body).toEqual({
      table: 'restorations',
      key: { id: 5 },
    })
  })
})
