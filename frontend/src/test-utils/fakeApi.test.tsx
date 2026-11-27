import { afterEach, describe, expect, it } from 'vitest'
import { createFakeClient, onApi, resetApi } from './fakeApi'
import { worldState } from './fixtures'

describe('the fake API', () => {
  afterEach(() => resetApi())

  it('fills a partial world state with every field the real state carries', async () => {
    onApi('GET', '/api/state', { world: { epoch: 12 }, read_only: true })
    const { data } = await createFakeClient().GET('/api/state')
    const full = worldState()
    expect(Object.keys(data ?? {}).sort()).toEqual(Object.keys(full).sort())
    expect(data?.role_models).toEqual(full.role_models)
    expect(data?.read_only).toBe(true)
  })

  it('fills a world state answered by a function too', async () => {
    onApi('GET', '/api/state', () => ({ epoch_running: true }))
    const { data } = await createFakeClient().GET('/api/state')
    expect(data?.epoch_running).toBe(true)
    expect(data?.role_models).toEqual(worldState().role_models)
  })
})
