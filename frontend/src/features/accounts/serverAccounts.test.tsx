import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { libraryQueryClient } from '@/api/queryClients'
import { ServerAccountsScreen } from './ServerAccountsScreen'
import { account, signedIn } from './accountFixtures'
import { Providers } from './providerFixtures'

const OWNER = account()
const OREN = account({
  id: 2,
  username: 'oren',
  display_name: 'Oren Vell',
  email: 'oren@example.org',
  server_role: 'member',
  avatar_tone: 'info',
})

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: 0 },
    mutations: { retry: false },
  })
})

afterEach(() => libraryQueryClient.clear())

describe('the accounts of the server', () => {
  it('makes an account and shows its temporary password once', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <ServerAccountsScreen />
      </Providers>,
      {
        'GET /api/auth/state': signedIn(),
        'GET /api/accounts': [OWNER, OREN],
        'POST /api/accounts': {
          account: account({
            id: 3,
            username: 'ilse',
            display_name: 'Ilse Marr',
            server_role: 'member',
          }),
          temporary_password: 'ZK2P-8WQM-4TRA-7HEX',
        },
      }
    )
    await expect.element(screen.getByText('Oren Vell')).toBeVisible()
    await screen.getByRole('button', { name: 'Make an account' }).click()
    await userEvent.fill(screen.getByLabelText('Display name'), 'Ilse Marr')
    await userEvent.fill(screen.getByLabelText('Username'), 'ilse')
    await userEvent.fill(screen.getByLabelText('E-mail'), 'ilse@example.org')
    await screen.getByRole('button', { name: 'Make the account' }).click()
    await expect.element(screen.getByText('ZK2P-8WQM-4TRA-7HEX')).toBeVisible()
    expect(server.callsTo('POST /api/accounts')[0].body).toEqual({
      display_name: 'Ilse Marr',
      username: 'ilse',
      email: 'ilse@example.org',
      server_role: 'member',
    })
  })

  it('deletes an account only after a dialog that names it', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <ServerAccountsScreen />
      </Providers>,
      {
        'GET /api/auth/state': signedIn(),
        'GET /api/accounts': [OWNER, OREN],
        'DELETE /api/accounts/{id}': {},
      }
    )
    await screen.getByRole('button', { name: 'Acts on Oren Vell' }).click()
    await screen.getByRole('menuitem', { name: 'Delete the account' }).click()
    await expect
      .element(screen.getByText('Delete the account of Oren Vell?'))
      .toBeVisible()
    expect(server.callsTo('DELETE /api/accounts/{id}')).toHaveLength(0)
    await screen.getByRole('button', { name: 'Delete Oren Vell' }).click()
    await expect
      .poll(() => server.callsTo('DELETE /api/accounts/{id}').length)
      .toBe(1)
  })

  it('keeps the owner and oneself out of reach of the row acts', async () => {
    const { screen } = await renderScreen(
      <Providers>
        <ServerAccountsScreen />
      </Providers>,
      {
        'GET /api/auth/state': signedIn(),
        'GET /api/accounts': [OWNER, OREN],
      }
    )
    await expect
      .element(screen.getByRole('button', { name: 'Acts on Mara Ilven' }))
      .toBeDisabled()
  })

  it('tells a member the page is for server admins', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <ServerAccountsScreen />
      </Providers>,
      {
        'GET /api/auth/state': signedIn({ server_role: 'member' }),
      }
    )
    await expect
      .element(screen.getByText('Only server admins manage accounts'))
      .toBeVisible()
    expect(server.callsTo('GET /api/accounts')).toHaveLength(0)
  })
})
