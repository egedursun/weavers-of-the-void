import { useQuery } from '@tanstack/react-query'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { currentAccountScope } from '@/api/accountScope'
import { raiseAuthSignal } from '@/api/authSignals'
import { libraryQueryClient, queryClientFor } from '@/api/queryClients'
import { chooseUniverse, currentUniverse } from '@/api/universeStore'
import { viewerExit } from '@/api/viewerExit'
import { chooseWorkspace, currentWorkspace } from '@/api/workspaceStore'
import { storeItem, storedItem, universeKey } from '@/lib/universeStorage'
import { AuthGate } from './AuthGate'
import { SIGNED_OUT, signedIn } from './accountFixtures'
import { refreshAuth } from './api'
import { Providers } from './providerFixtures'
import { type AuthState } from './types'

const UNIVERSE = 'aaaaaaaaaaaa'
const SECRET_KEY = ['library', 'secret'] as const
const DRAFT = 'aerona.divine-will.composer'

function Inside() {
  const secret = useQuery(
    {
      queryKey: SECRET_KEY,
      queryFn: () => 'fresh for whoever is signed in',
      staleTime: Number.POSITIVE_INFINITY,
    },
    libraryQueryClient
  )
  return (
    <>
      <p>{`Cache: ${secret.data ?? 'reading'}`}</p>
      <p>{`Draft: ${storedItem(universeKey(DRAFT)) ?? 'none'}`}</p>
    </>
  )
}

const reload = vi.fn()
const quietReload = viewerExit.reload

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: Number.POSITIVE_INFINITY },
    mutations: { retry: false },
  })
  reload.mockClear()
  viewerExit.reload = reload
})

afterEach(() => {
  viewerExit.reload = quietReload
  libraryQueryClient.clear()
  chooseUniverse(null)
  chooseWorkspace(null)
  window.localStorage.clear()
})

describe('a new person on the same browser', () => {
  it('sees nothing the person before them left', async () => {
    let state: AuthState = signedIn({ id: 1 })
    const { screen } = await renderScreen(
      <Providers>
        <AuthGate>
          <Inside />
        </AuthGate>
      </Providers>,
      { 'GET /api/auth/state': () => state },
      '/',
      { realtime: false }
    )
    chooseUniverse(UNIVERSE)
    chooseWorkspace('7')
    await expect.element(screen.getByText(/^Cache: fresh/)).toBeVisible()
    expect(currentAccountScope()).toBe(1)
    storeItem(universeKey(DRAFT), 'the first person’s unsent words')
    libraryQueryClient.setQueryData(
      SECRET_KEY,
      'what only the first person saw'
    )
    queryClientFor(UNIVERSE).setQueryData(['world'], 'the first person’s world')

    state = SIGNED_OUT
    raiseAuthSignal('signed_out')
    await expect.element(screen.getByText('Return to the void')).toBeVisible()
    await expect.poll(() => reload.mock.calls.length).toBe(1)
    expect(libraryQueryClient.getQueryData(SECRET_KEY)).toBeUndefined()
    expect(queryClientFor(UNIVERSE).getQueryData(['world'])).toBeUndefined()
    expect(currentUniverse()).toBeNull()
    expect(currentWorkspace()).toBeNull()
    expect(currentAccountScope()).toBeNull()

    state = signedIn({ id: 2, username: 'oren', display_name: 'Oren Vell' })
    chooseUniverse(UNIVERSE)
    await refreshAuth()
    await expect
      .element(screen.getByText('Cache: fresh for whoever is signed in'))
      .toBeVisible()
    await expect.element(screen.getByText('Draft: none')).toBeVisible()
    expect(currentAccountScope()).toBe(2)
  })
})
