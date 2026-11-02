import { fetchHealth } from '@/api/system'
import { afterEach, describe, expect, it } from 'vitest'
import { installFetch, takeNetworkViolations } from './networkGuard'
import { startMockServer } from './mockServer'

const HEALTH = { status: 'ok' }

describe('network guard', () => {
  afterEach(() => installFetch(null))

  it('routes a client created before the mock server to the mock', async () => {
    const server = startMockServer({ 'GET /api/health': HEALTH })
    await expect(fetchHealth()).resolves.toEqual(HEALTH)
    expect(server.callsTo('GET /api/health')).toHaveLength(1)
    server.stop()
    expect(takeNetworkViolations()).toEqual([])
  })

  it('blocks and records an unmocked API call', async () => {
    await expect(fetchHealth()).rejects.toBeTruthy()
    const violations = takeNetworkViolations()
    expect(violations).toHaveLength(1)
    expect(violations[0]).toContain('/api/health')
  })

  it('blocks a cross-origin request', async () => {
    const response = await fetch('https://example.invalid/data.json')
    expect(response.ok).toBe(false)
    expect(takeNetworkViolations()).toEqual([
      'fetch https://example.invalid/data.json',
    ])
  })

  it('never opens a real event stream', () => {
    const source = new EventSource('/api/events')
    expect(source.readyState).toBe(EventSource.CLOSED)
    expect(takeNetworkViolations()).toEqual(['EventSource /api/events'])
  })

  it('blocks a cross-origin request made through XMLHttpRequest', () => {
    const request = new XMLHttpRequest()
    request.open('GET', 'https://example.invalid/data.json')
    request.send()
    expect(takeNetworkViolations()).toEqual([
      'xhr https://example.invalid/data.json',
    ])
  })

  it('refuses to open a socket to the API', () => {
    expect(() => new WebSocket(`ws://${window.location.host}/api/socket`)).toThrow()
    expect(takeNetworkViolations()).toEqual([
      `websocket ws://${window.location.host}/api/socket`,
    ])
  })
})
