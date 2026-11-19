import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BodySystemsSection } from './BodySystemsSection'

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
  table: 'body_systems',
  label: 'Body systems',
  columns: [
    column('holder_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('system', 'choice', { options: ['breath', 'nerves'] }),
    column('gravity_max', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { holder_entity_id: 7, system: 'breath', gravity_max: 75 },
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

describe('the body systems and sensitivities section', () => {
  beforeEach(() => resetApi())

  it('shows only its own records and strikes one by its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [rows, tags],
      creatable: [rows, tags],
      names: {},
    })
    onApi('POST', '/api/actions/body_system:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BodySystemsSection nodeId={7} />)
    await expect
      .element(
        screen.getByText('Body systems and sensitivities', { exact: true })
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open body systems' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open body systems' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/body_system:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/body_system:delete')[0].body).toEqual({
      table: 'body_systems',
      key: { id: 3 },
    })
  })
})
