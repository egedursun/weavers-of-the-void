import { useQueryClient } from '@tanstack/react-query'
import { FakeEventSource } from '@/test-utils/fakeEventSource'
import { installFetch } from '@/test-utils/networkGuard'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { api } from '@/api/client'
import { dropQueryClient, queryClientFor } from '@/api/queryClients'
import {
  UNIVERSE_HEADER,
  chooseUniverse,
  currentUniverse,
  onUniverseRefused,
  releaseDocument,
  universeFromSearch,
} from '@/api/universeStore'
import { apiUrl } from '@/api/url'
import { adoptLegacyStorage, universeKey } from '@/lib/universeStorage'
import { useOnboarding } from '@/features/onboarding/onboardingStore'
import { UniverseBoundary } from './UniverseBoundary'
import { FIRST_ID, SECOND_ID } from './universeFixtures'

const LAST_KEY = 'aerona.universe.last'

afterEach(() => {
  installFetch(null)
  chooseUniverse(null)
  releaseDocument()
  localStorage.removeItem(LAST_KEY)
})

function capture(): Request[] {
  const seen: Request[] = []
  installFetch((input, init) => {
    seen.push(new Request(input as RequestInfo, init))
    return Promise.resolve(
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    )
  })
  return seen
}

describe('the universe a tab holds', () => {
  it('reads a well formed universe id from the address only', () => {
    expect(universeFromSearch(`?universe=${FIRST_ID}`)).toBe(FIRST_ID)
    expect(universeFromSearch('?universe=../etc')).toBeNull()
    expect(universeFromSearch('?entry=son:1')).toBeNull()
  })

  it('keeps the last opened universe as the default for a new tab', () => {
    chooseUniverse(FIRST_ID)
    expect(sessionStorage.getItem('aerona.universe')).toBe(FIRST_ID)
    expect(localStorage.getItem(LAST_KEY)).toBe(FIRST_ID)
  })
})

describe('apiUrl', () => {
  it('names the universe on every raw API address', () => {
    chooseUniverse(FIRST_ID)
    expect(apiUrl('/api/media/a%20b.png', { w: 320 })).toBe(
      `/api/media/a%20b.png?w=320&universe=${FIRST_ID}`
    )
    expect(apiUrl('/api/book', { son_id: null })).toBe(
      `/api/book?universe=${FIRST_ID}`
    )
  })

  it('leaves the address bare without a universe and on library routes', () => {
    expect(apiUrl('/api/book')).toBe('/api/book')
    chooseUniverse(FIRST_ID)
    expect(apiUrl('/api/library/universes', { limit: 1 })).toBe(
      '/api/library/universes?limit=1'
    )
  })
})

describe('the API client', () => {
  it('sends the universe header with every universe call', async () => {
    const seen = capture()
    chooseUniverse(SECOND_ID)
    await api.GET('/api/health')
    expect(seen[0].headers.get(UNIVERSE_HEADER)).toBe(SECOND_ID)
  })

  it('sends no header before a universe is chosen', async () => {
    const seen = capture()
    await api.GET('/api/health')
    expect(seen[0].headers.get(UNIVERSE_HEADER)).toBeNull()
  })

  it('returns to the library when the server refuses the universe', async () => {
    installFetch(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            error: 'That universe is archived.',
            code: 'universe_required',
          }),
          { status: 409, headers: { 'content-type': 'application/json' } }
        )
      )
    )
    chooseUniverse(FIRST_ID)
    const heard: string[] = []
    const stop = onUniverseRefused((message) => heard.push(message))
    await api.GET('/api/health')
    stop()
    expect(heard).toEqual(['That universe is archived.'])
    expect(currentUniverse()).toBeNull()
    expect(localStorage.getItem(LAST_KEY)).toBeNull()
  })

  it('keeps the universe on an ordinary conflict', async () => {
    installFetch(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: 'Busy.' }), {
          status: 409,
          headers: { 'content-type': 'application/json' },
        })
      )
    )
    chooseUniverse(FIRST_ID)
    await api.GET('/api/health')
    expect(currentUniverse()).toBe(FIRST_ID)
  })
})

describe('the query cache', () => {
  it('gives every universe a client of its own', () => {
    const first = queryClientFor(FIRST_ID)
    expect(queryClientFor(FIRST_ID)).toBe(first)
    expect(queryClientFor(SECOND_ID)).not.toBe(first)
    first.setQueryData(['probe'], 1)
    expect(queryClientFor(SECOND_ID).getQueryData(['probe'])).toBeUndefined()
    dropQueryClient(FIRST_ID)
    expect(queryClientFor(FIRST_ID)).not.toBe(first)
    expect(queryClientFor(FIRST_ID).getQueryData(['probe'])).toBeUndefined()
  })

  it('renders the shell inside the client of its universe', async () => {
    chooseUniverse(FIRST_ID)
    let used: unknown = null
    function Probe() {
      used = useQueryClient()
      return <p>inside</p>
    }
    const { screen } = await renderScreen(
      <UniverseBoundary createSource={(url) => new FakeEventSource(url)}>
        <Probe />
      </UniverseBoundary>,
      {},
      '/atlas',
      { realtime: false }
    )
    await expect.element(screen.getByText('inside')).toBeInTheDocument()
    expect(used).toBe(queryClientFor(FIRST_ID))
    expect(FakeEventSource.latest().url).toBe(
      `/api/events?universe=${FIRST_ID}`
    )
  })

  it('sends a tab without a universe to the library', async () => {
    const { router, screen } = await renderScreen(
      <UniverseBoundary createSource={(url) => new FakeEventSource(url)}>
        <p>inside</p>
      </UniverseBoundary>,
      {},
      '/atlas',
      { realtime: false }
    )
    await expect.poll(() => router.state.location.pathname).toBe('/')
    await expect.element(screen.getByText('inside')).not.toBeInTheDocument()
  })

  it('leaves a refused universe even when the address still names it', async () => {
    const { router } = await renderScreen(
      <UniverseBoundary createSource={(url) => new FakeEventSource(url)}>
        <p>inside</p>
      </UniverseBoundary>,
      {},
      `/overview?universe=${FIRST_ID}`,
      { realtime: false }
    )
    await expect.poll(() => currentUniverse()).toBe(FIRST_ID)
    installFetch(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ error: 'Gone.', code: 'universe_required' }),
          { status: 409, headers: { 'content-type': 'application/json' } }
        )
      )
    )
    await api.GET('/api/health')
    await expect.poll(() => router.state.location.pathname).toBe('/')
    expect(currentUniverse()).toBeNull()
  })

  it('takes the universe named in the address', async () => {
    const { screen } = await renderScreen(
      <UniverseBoundary createSource={(url) => new FakeEventSource(url)}>
        <p>inside</p>
      </UniverseBoundary>,
      {},
      `/overview?universe=${SECOND_ID}`,
      { realtime: false }
    )
    await expect.element(screen.getByText('inside')).toBeInTheDocument()
    expect(currentUniverse()).toBe(SECOND_ID)
  })
})

describe('universe storage', () => {
  it('keeps the data of each universe under its own key', async () => {
    chooseUniverse(FIRST_ID)
    expect(universeKey('aerona.bookmarks')).toBe(`aerona.bookmarks@${FIRST_ID}`)
    useOnboarding.getState().mark('map')
    expect(localStorage.getItem(`aerona.onboarding@${FIRST_ID}`)).toContain(
      'map'
    )
    chooseUniverse(SECOND_ID)
    await expect.poll(() => useOnboarding.getState().done).toEqual([])
    chooseUniverse(FIRST_ID)
    await expect.poll(() => useOnboarding.getState().done).toEqual(['map'])
    localStorage.removeItem(`aerona.onboarding@${FIRST_ID}`)
    localStorage.removeItem(`aerona.onboarding@${SECOND_ID}`)
  })

  it('moves the data of the old single universe into the adopted one', () => {
    localStorage.setItem('aerona.bookmarks', '["son:1"]')
    localStorage.setItem('aerona.map.layer', '"terrain"')
    localStorage.setItem('aerona.probe-preference', 'dark')
    adoptLegacyStorage(FIRST_ID)
    expect(localStorage.getItem(`aerona.bookmarks@${FIRST_ID}`)).toBe(
      '["son:1"]'
    )
    expect(localStorage.getItem(`aerona.map.layer@${FIRST_ID}`)).toBe(
      '"terrain"'
    )
    expect(localStorage.getItem('aerona.bookmarks')).toBeNull()
    expect(localStorage.getItem('aerona.probe-preference')).toBe('dark')
    localStorage.removeItem(`aerona.bookmarks@${FIRST_ID}`)
    localStorage.removeItem(`aerona.map.layer@${FIRST_ID}`)
    localStorage.removeItem('aerona.probe-preference')
  })
})
