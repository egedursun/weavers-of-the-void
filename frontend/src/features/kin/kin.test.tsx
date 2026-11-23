import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { KinSection } from './KinSection'

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
  table: 'kin_groups',
  label: 'Kin groups',
  columns: [
    column('people_entity_id', 'integer', {
      primary: true,
      owner: true,
      editable: false,
    }),
    column('form', 'choice', {
      options: ['lineage', 'clan', 'moiety'],
    }),
    column('exogamy', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { people_entity_id: 7, form: 'clan', exogamy: 80 },
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

const duties = {
  table: 'kin_role_duties',
  label: 'Kin role duties',
  columns: [
    column('people_entity_id', 'integer', {
      primary: true,
      owner: true,
      required: true,
      editable: false,
    }),
    column('role', 'choice', {
      options: ['sworn_kin', 'foster_kin', 'godparent'],
      primary: true,
      required: true,
      editable: false,
    }),
    column('duty', 'choice', {
      options: ['support', 'avenge', 'mourn'],
      primary: true,
      required: true,
      editable: false,
    }),
    column('strength', 'integer'),
  ],
  rows: [],
}

describe('kin section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of kin and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/kin_group:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<KinSection nodeId={7} />)
    await expect.element(screen.getByText('Kin', { exact: true })).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open kin groups' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open kin groups' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/kin_group:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/kin_group:delete')[0].body).toEqual({
      table: 'kin_groups',
      key: { id: 3 },
    })
  })
  it('binds a duty on foster kin through its own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care],
      creatable: [duties],
      names: {},
    })
    onApi('POST', '/api/actions/kin_role_duty:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<KinSection nodeId={7} />)
    await screen.getByRole('combobox', { name: 'Kind of record' }).click()
    await screen.getByRole('option', { name: /Kin role duties/ }).click()
    await screen.getByRole('button', { name: 'Make it', exact: true }).click()
    const dialog = screen.getByRole('dialog')
    await expect
      .element(dialog.getByRole('button', { name: 'Make it', exact: true }))
      .toHaveAccessibleDescription('Fill in role.')
    await dialog.getByRole('combobox', { name: 'Role' }).click()
    await screen.getByRole('option', { name: 'Foster kin' }).click()
    await dialog.getByRole('combobox', { name: 'Duty' }).click()
    await screen.getByRole('option', { name: 'Mourn' }).click()
    await dialog.getByRole('button', { name: 'Make it', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/kin_role_duty:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/kin_role_duty:create')[0].body
    ).toEqual({
      table: 'kin_role_duties',
      values: { people_entity_id: 7, role: 'foster_kin', duty: 'mourn' },
    })
  })
})
