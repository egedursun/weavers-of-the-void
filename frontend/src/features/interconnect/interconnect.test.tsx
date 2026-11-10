import { onApi, renderApp, resetApi } from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InterconnectionExplorer } from './InterconnectionExplorer'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WRITERS = Array.from({ length: 20 }, (_, index) => `writer_${index}`)

describe('the interconnection explorer', () => {
  beforeEach(() => resetApi())

  it('pages the mechanics that write and read a link instead of listing them all', async () => {
    onApi('GET', '/api/mechanics/graph', {
      subsystems: [
        { key: 'war', mechanics: 20, outgoing: 1, incoming: 0 },
        { key: 'law', mechanics: 1, outgoing: 0, incoming: 1 },
      ],
      links: [
        {
          source: 'war',
          target: 'law',
          kinds: ['flow'],
          edges: 20,
          carriers: ['war.toll'],
          writers: WRITERS,
          readers: ['reader_0'],
        },
      ],
      mechanics: [],
    })
    const { screen } = await renderApp(<InterconnectionExplorer />)
    await screen.getByRole('button', { name: 'War to Law: 1 carriers' }).click()
    await expect.element(screen.getByText('Written by (20)')).toBeVisible()
    await expect.element(screen.getByText('writer 7')).toBeVisible()
    expect(screen.getByText('writer 8').elements()).toHaveLength(0)
    await screen.getByRole('button', { name: 'Show all 20' }).click()
    await expect.element(screen.getByText('writer 19')).toBeVisible()
  })
})
