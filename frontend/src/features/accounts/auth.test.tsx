import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { raiseAuthSignal } from '@/api/authSignals'
import { libraryQueryClient } from '@/api/queryClients'
import { AuthGate } from './AuthGate'
import { SETUP, SIGNED_OUT, account, signedIn } from './accountFixtures'
import { Providers } from './providerFixtures'
import { type AuthState } from './types'

const GOOD = 'a long secret phrase'

function renderGate(routes: Record<string, unknown>) {
  return renderScreen(
    <Providers>
      <AuthGate>
        <p>Inside the app</p>
      </AuthGate>
    </Providers>,
    routes,
    '/',
    { realtime: false }
  )
}

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: 0 },
    mutations: { retry: false },
  })
})

afterEach(() => libraryQueryClient.clear())

describe('the gate of the app', () => {
  it('claims the server with an owner account on the first start', async () => {
    let state: AuthState = SETUP
    const { screen, server } = await renderGate({
      'GET /api/auth/state': () => state,
      'POST /api/auth/setup': () => {
        state = signedIn()
        return account()
      },
    })
    await expect.element(screen.getByText('Claim this server')).toBeVisible()
    const create = screen.getByRole('button', {
      name: 'Claim the server',
    })
    await expect.element(create).toBeDisabled()
    await userEvent.fill(screen.getByLabelText('Display name'), 'Mara Ilven')
    await userEvent.fill(screen.getByLabelText('Username'), 'Mara')
    await userEvent.fill(screen.getByLabelText('E-mail'), 'mara@example.org')
    await userEvent.fill(
      screen.getByLabelText('Password', { exact: true }),
      'mara12345678'
    )
    await userEvent.fill(
      screen.getByLabelText('Repeat the password'),
      'mara12345678'
    )
    await expect
      .element(
        screen.getByText(
          'Does not contain your username or e-mail name (not met)'
        )
      )
      .toBeInTheDocument()
    await expect.element(create).toBeDisabled()
    await userEvent.fill(
      screen.getByLabelText('Password', { exact: true }),
      GOOD
    )
    await userEvent.fill(screen.getByLabelText('Repeat the password'), GOOD)
    await create.click()
    await expect.element(screen.getByText('Inside the app')).toBeVisible()
    expect(server.callsTo('POST /api/auth/setup')[0].body).toEqual({
      display_name: 'Mara Ilven',
      username: 'mara',
      email: 'mara@example.org',
      password: GOOD,
    })
  })

  it('says why a sign-in fails and lets the person in with the right password', async () => {
    let state: AuthState = SIGNED_OUT
    const { screen, server } = await renderGate({
      'GET /api/auth/state': () => state,
      'POST /api/auth/sign-in': (request: { body: unknown }) => {
        const body = request.body as { password: string }
        if (body.password !== GOOD)
          return failure(401, 'The username or the password is wrong.')
        state = signedIn()
        return account()
      },
    })
    await expect.element(screen.getByText('Return to the void')).toBeVisible()
    await userEvent.fill(screen.getByLabelText('Username or e-mail'), 'mara')
    await userEvent.fill(
      screen.getByLabelText('Password', { exact: true }),
      'wrong one'
    )
    await screen.getByRole('button', { name: 'Sign in' }).click()
    await expect
      .element(screen.getByText('The username or the password is wrong.'))
      .toBeVisible()
    await userEvent.fill(
      screen.getByLabelText('Password', { exact: true }),
      GOOD
    )
    await screen.getByRole('button', { name: 'Sign in' }).click()
    await expect.element(screen.getByText('Inside the app')).toBeVisible()
    expect(server.callsTo('POST /api/auth/sign-in')).toHaveLength(2)
  })

  it('makes a person with a temporary password set their own first', async () => {
    let state: AuthState = signedIn({
      must_change_password: true,
      server_role: 'member',
    })
    const { screen, server } = await renderGate({
      'GET /api/auth/state': () => state,
      'POST /api/auth/password': () => {
        state = signedIn({ server_role: 'member' })
        return account({ server_role: 'member' })
      },
      'POST /api/auth/sign-out': {},
    })
    await expect.element(screen.getByText('Welcome, Mara Ilven')).toBeVisible()
    const set = screen.getByRole('button', { name: 'Set my password' })
    await expect.element(set).toBeDisabled()
    await userEvent.fill(
      screen.getByLabelText('Temporary password'),
      'TEMP-PASS-1234'
    )
    await userEvent.fill(screen.getByLabelText('Your new password'), GOOD)
    await userEvent.fill(screen.getByLabelText('Repeat the password'), GOOD)
    await set.click()
    await expect.element(screen.getByText('Inside the app')).toBeVisible()
    expect(server.callsTo('POST /api/auth/password')[0].body).toEqual({
      current: 'TEMP-PASS-1234',
      new: GOOD,
    })
  })

  it('returns to the sign-in when the server says the session ended', async () => {
    let state: AuthState = signedIn()
    const { screen } = await renderGate({
      'GET /api/auth/state': () => state,
    })
    await expect.element(screen.getByText('Inside the app')).toBeVisible()
    state = SIGNED_OUT
    raiseAuthSignal('signed_out')
    await expect.element(screen.getByText('Return to the void')).toBeVisible()
  })
})
