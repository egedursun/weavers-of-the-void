import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BeastSection } from './BeastSection'
import { BEAST, serveBasics } from './wildsFixtures'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

describe('creature anatomy', () => {
  beforeEach(resetApi)

  it('shows a monster’s body and nature and reshapes its skin', async () => {
    serveBasics()
    onApi('GET', '/api/entities/9/beast', BEAST)
    onApi('POST', '/api/actions/anatomy:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BeastSection beastId={9} />)
    await expect.element(screen.getByText('Body and nature')).toBeVisible()
    await expect.element(screen.getByText('Seizes prey').first()).toBeVisible()
    await expect.element(screen.getByText('Deep mining').first()).toBeVisible()
    await screen.getByRole('combobox', { name: 'Skin' }).click()
    await screen.getByRole('option', { name: 'Hide' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/anatomy:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/anatomy:edit')[0].body).toEqual({
      node_id: 9,
      values: { skin: 'hide' },
      release: [],
    })
  })

  it('sets what a monster hoards above all else', async () => {
    serveBasics()
    onApi('GET', '/api/entities/9/beast', BEAST)
    onApi('POST', '/api/actions/anatomy:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BeastSection beastId={9} />)
    await screen.getByRole('combobox', { name: 'Hoards' }).click()
    await screen.getByRole('option', { name: 'Silver' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/anatomy:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/anatomy:edit')[0].body).toEqual({
      node_id: 9,
      values: { hoards: 'silver' },
      release: [],
    })
  })
})
