import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PublicWorksSection } from './PublicWorksSection'

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
  table: 'public_works',
  label: 'Public works',
  columns: [
    column('polity_entity_id', 'integer', {
      owner: true,
      editable: false,
    }),
    column('kind', 'choice', {
      options: ['road', 'bridge', 'canal'],
    }),
    column('quality', 'integer'),
  ],
  rows: [
    {
      key: { id: 3 },
      values: { polity_entity_id: 7, kind: 'road', quality: 60 },
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

describe('public works section', () => {
  beforeEach(() => resetApi())

  it('shows only the records of works and strikes them by their own lever', async () => {
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [care, tags],
      creatable: [care, tags],
      names: {},
    })
    onApi('POST', '/api/actions/public_works:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PublicWorksSection nodeId={7} />)
    await expect
      .element(screen.getByText('Public works', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open public works' }))
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open entity tags' }).query()
    ).toBeNull()
    await screen.getByRole('button', { name: 'Open public works' }).click()
    await screen.getByRole('button', { name: 'Unmake this row' }).click()
    await screen.getByRole('button', { name: 'Unmake it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/public_works:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/public_works:delete')[0].body).toEqual(
      {
        table: 'public_works',
        key: { id: 3 },
      }
    )
  })

  it('carries works under way a stage further and says why finished ones cannot be', async () => {
    const building = {
      ...care,
      columns: [
        ...care.columns,
        column('status', 'choice', { options: ['building', 'finished'] }),
      ],
      rows: [
        {
          key: { id: 3 },
          values: {
            polity_entity_id: 7,
            kind: 'road',
            quality: 60,
            status: 'building',
          },
          held: [],
        },
        {
          key: { id: 4 },
          values: {
            polity_entity_id: 7,
            kind: 'canal',
            quality: 70,
            status: 'finished',
          },
          held: [],
        },
      ],
    }
    onApi('GET', '/api/records/7/rows', {
      node_id: 7,
      tables: [building],
      creatable: [building],
      names: {},
    })
    onApi('POST', '/api/actions/public_works:advance', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PublicWorksSection nodeId={7} />)
    await screen.getByRole('button', { name: 'Open public works' }).click()
    const steps = screen.getByRole('button', {
      name: 'Carry these works a stage further',
    })
    await expect.element(steps.nth(1)).toBeDisabled()
    await steps.nth(0).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/public_works:advance'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/public_works:advance')[0].body
    ).toEqual({ works_id: 3 })
  })
})
