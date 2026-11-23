import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RelationParts } from './RelationParts'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function serve(parts: unknown[]) {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/relations/10/20/parts', { parts })
}

describe('relation parts', () => {
  beforeEach(resetApi)

  it('names each part by its label and sets a part with the right body', async () => {
    serve([
      { component: 'language', value: 12, updated_epoch: 49, locked: [] },
      {
        component: 'war_memory',
        value: -30,
        updated_epoch: 49,
        locked: ['value'],
      },
    ])
    onApi('POST', '/api/actions/relation_component:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <RelationParts firstId={10} secondId={20} blocked={null} />
    )
    await expect.element(screen.getByText('Shared tongue +12')).toBeVisible()
    await expect.element(screen.getByText('Memory of war -30')).toBeVisible()
    await expect
      .element(screen.getByText('reckoned in epoch 49, held'))
      .toBeVisible()
    expect(screen.container.textContent).not.toContain('war_memory')
    await screen.getByRole('combobox', { name: 'Part' }).click()
    await screen.getByRole('option', { name: 'Kinship of values' }).click()
    await screen.getByRole('button', { name: 'Set it', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/relation_component:set'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/relation_component:set')[0].body
    ).toEqual({ first_id: 10, second_id: 20, component: 'values', value: 10 })
  })

  it('says the parts are reckoned later and keeps the control with its reason while blocked', async () => {
    serve([])
    const { screen } = await renderApp(
      <RelationParts
        firstId={10}
        secondId={20}
        blocked='The epoch is running.'
      />
    )
    await expect
      .element(screen.getByText('Its parts are reckoned at the next epoch.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Set it', exact: true }))
      .toHaveAccessibleDescription('The epoch is running.')
  })
})
