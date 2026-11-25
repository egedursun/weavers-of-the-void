import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { libraryQueryClient } from '@/api/queryClients'
import {
  WORKSPACE_HEADER,
  chooseWorkspace,
  currentWorkspace,
} from '@/api/workspaceStore'
import {
  access,
  member,
  signedIn,
  workspace,
} from '@/features/accounts/accountFixtures'
import { Providers } from '@/features/accounts/providerFixtures'
import { useUniverses, NO_UNIVERSE_FILTERS } from '@/features/universes/api'
import {
  universePage,
  universeSummary,
} from '@/features/universes/universeFixtures'
import { MembersPanel } from './MembersPanel'
import { UniverseAccessPanel } from './UniverseAccessPanel'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'

const TEAM = workspace()
const OREN = member({
  id: 2,
  username: 'oren',
  display_name: 'Oren Vell',
  email: 'oren@example.org',
  avatar_tone: 'info',
})
const MARA = member({ id: 1, server_role: 'owner' }, 'admin')

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: 0 },
    mutations: { retry: false },
  })
})

afterEach(() => {
  libraryQueryClient.clear()
  chooseWorkspace(null)
})

function memberRoutes(extra: Record<string, unknown> = {}) {
  return {
    'GET /api/auth/state': signedIn(),
    'GET /api/workspaces/{id}/members': [MARA, OREN],
    ...extra,
  }
}

describe('the members of a workspace', () => {
  it('adds a new account as a Viewer and shows its temporary password once', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <MembersPanel workspace={TEAM} />
      </Providers>,
      memberRoutes({
        'POST /api/workspaces/{id}/members': {
          member: member({
            id: 3,
            username: 'ilse',
            display_name: 'Ilse Marr',
          }),
          temporary_password: 'HXQ4-7MPA-2KRT-9WEZ',
        },
      })
    )
    await expect.element(screen.getByText('Oren Vell')).toBeVisible()
    await screen.getByRole('button', { name: 'Add a member' }).click()
    await screen.getByRole('tab', { name: 'A new account' }).click()
    await userEvent.fill(screen.getByLabelText('Display name'), 'Ilse Marr')
    await userEvent.fill(screen.getByLabelText('Username'), 'ilse')
    await userEvent.fill(screen.getByLabelText('E-mail'), 'ilse@example.org')
    await expect
      .element(screen.getByRole('radio', { name: /Viewer/ }))
      .toHaveAttribute('aria-checked', 'true')
    await screen
      .getByRole('button', { name: 'Make the account and add it' })
      .click()
    await expect.element(screen.getByText('HXQ4-7MPA-2KRT-9WEZ')).toBeVisible()
    await expect.element(screen.getByText('Shown only this once')).toBeVisible()
    expect(server.callsTo('POST /api/workspaces/{id}/members')[0].body).toEqual(
      {
        username: 'ilse',
        email: 'ilse@example.org',
        display_name: 'Ilse Marr',
        role: 'viewer',
      }
    )
    await screen.getByRole('button', { name: /^Done/ }).click()
    await expect
      .element(screen.getByText('HXQ4-7MPA-2KRT-9WEZ'))
      .not.toBeInTheDocument()
  })

  it('finds an existing account only by its exact username and adds it', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <MembersPanel workspace={TEAM} />
      </Providers>,
      memberRoutes({
        'GET /api/workspaces/{id}/candidates': (request: {
          query: URLSearchParams
        }) =>
          request.query.get('q') === 'sela'
            ? [
                {
                  id: 4,
                  username: 'sela',
                  display_name: 'Sela Dorn',
                  avatar_tone: 'gold',
                },
              ]
            : [],
        'POST /api/workspaces/{id}/members': {
          member: member({
            id: 4,
            username: 'sela',
            display_name: 'Sela Dorn',
          }),
          temporary_password: null,
        },
      })
    )
    await expect.element(screen.getByText('Oren Vell')).toBeVisible()
    await screen.getByRole('button', { name: 'Add a member' }).click()
    await expect
      .element(screen.getByText('Type their exact username or e-mail'))
      .toBeVisible()
    await userEvent.fill(
      screen.getByLabelText('Exact username or e-mail'),
      'sel'
    )
    await expect.element(screen.getByText('No account to add')).toBeVisible()
    await userEvent.fill(
      screen.getByLabelText('Exact username or e-mail'),
      'sela'
    )
    await screen.getByRole('button', { name: /Sela Dorn/ }).click()
    await screen.getByRole('button', { name: 'Add the member' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/workspaces/{id}/members')[0]?.body)
      .toEqual({ account_id: 4, role: 'viewer' })
  })

  it('resets a password and deactivates an account only after a confirmation', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <MembersPanel workspace={TEAM} />
      </Providers>,
      memberRoutes({
        'POST /api/workspaces/{id}/members/{account}/reset-password': {
          account: OREN.account,
          temporary_password: 'NEW1-TEMP-PASS-0001',
        },
        'POST /api/workspaces/{id}/members/{account}/deactivate': OREN,
      })
    )
    await screen.getByRole('button', { name: 'Acts on Oren Vell' }).click()
    await screen.getByRole('menuitem', { name: 'Reset the password' }).click()
    await screen.getByRole('button', { name: 'Reset the password' }).click()
    await expect.element(screen.getByText('NEW1-TEMP-PASS-0001')).toBeVisible()
    await screen.getByRole('button', { name: /^Done/ }).click()
    await screen.getByRole('button', { name: 'Acts on Oren Vell' }).click()
    await screen
      .getByRole('menuitem', { name: 'Deactivate the account' })
      .click()
    await expect
      .element(screen.getByText('Deactivate Oren Vell?'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Deactivate' }).click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'POST /api/workspaces/{id}/members/{account}/deactivate'
          ).length
      )
      .toBe(1)
  })

  it('keeps the acts of a member disabled with a reason for a Viewer', async () => {
    const { screen } = await renderScreen(
      <Providers>
        <MembersPanel workspace={workspace({ role: 'viewer' })} />
      </Providers>,
      memberRoutes()
    )
    const add = screen.getByRole('button', { name: 'Add a member' })
    await expect.element(add).toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Acts on Oren Vell' }))
      .toBeDisabled()
  })
})

describe('the access to one universe', () => {
  const routes = (extra: Record<string, unknown> = {}) => ({
    'GET /api/auth/state': signedIn(),
    'GET /api/library/universes': universePage([universeSummary()]),
    'GET /api/workspaces/{id}/universes/{universe}/access': access(),
    ...extra,
  })

  it('turns a permission on for Viewers and back to the defaults', async () => {
    const { screen, server } = await renderScreen(
      <Providers>
        <UniverseAccessPanel workspace={TEAM} />
      </Providers>,
      routes({
        'PUT /api/workspaces/{id}/universes/{universe}/access/permissions':
          access(),
        'DELETE /api/workspaces/{id}/universes/{universe}/access/permissions':
          access(),
      })
    )
    const viewerEdits = screen.getByRole('switch', {
      name: 'Viewers: Shape the world',
    })
    await viewerEdits.click()
    const puts = () =>
      server.callsTo(
        'PUT /api/workspaces/{id}/universes/{universe}/access/permissions'
      )
    await expect.poll(() => puts().length).toBe(1)
    expect(puts()[0].body).toEqual({ viewer: { edit_world: true } })
    await expect
      .element(
        screen.getByRole('switch', { name: 'Viewers: Read the universe' })
      )
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Back to defaults' }))
      .toBeDisabled()
  })

  it('sets an exception for one person and takes it back', async () => {
    const changed = access({
      people: [{ ...access().people[0], overridden: true, role: 'none' }],
    })
    const { screen, server } = await renderScreen(
      <Providers>
        <UniverseAccessPanel workspace={TEAM} />
      </Providers>,
      routes({
        'GET /api/workspaces/{id}/universes/{universe}/access': changed,
        'DELETE /api/workspaces/{id}/universes/{universe}/access/overrides/{account}':
          access(),
      })
    )
    await expect.element(screen.getByText('Exception').first()).toBeVisible()
    await expect.element(screen.getByText('No access').first()).toBeVisible()
    await screen
      .getByRole('button', { name: 'Back to the workspace role' })
      .click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'DELETE /api/workspaces/{id}/universes/{universe}/access/overrides/{account}'
          ).length
      )
      .toBe(1)
  })
})

describe('the workspace switcher', () => {
  it('moves the library to the chosen workspace', async () => {
    const own = workspace({
      id: 1,
      name: 'Mara Ilven',
      kind: 'personal',
      member_count: 1,
    })
    const { screen, server } = await renderScreen(
      <Providers>
        <WorkspaceSwitcher />
      </Providers>,
      {
        'GET /api/auth/state': signedIn(),
        'GET /api/workspaces': [own, TEAM],
        'GET /api/library/universes': universePage([]),
      }
    )
    const trigger = screen.getByRole('button', {
      name: 'Mara Ilven: switch workspace',
    })
    await expect.element(trigger).toBeVisible()
    await trigger.click()
    await screen.getByRole('menuitem', { name: /Studio Team/ }).click()
    await expect
      .element(
        screen.getByRole('button', { name: 'Studio Team: switch workspace' })
      )
      .toBeVisible()
    expect(currentWorkspace()).toBe(String(TEAM.id))
    expect(server.callsTo('GET /api/workspaces').length).toBeGreaterThan(0)
  })

  it('shows the universes of the workspace just chosen', async () => {
    const own = workspace({
      id: 1,
      name: 'Mara Ilven',
      kind: 'personal',
      member_count: 1,
    })
    const { screen } = await renderScreen(
      <Providers>
        <WorkspaceSwitcher />
        <ShelfNames />
      </Providers>,
      {
        'GET /api/auth/state': signedIn(),
        'GET /api/workspaces': [own, TEAM],
        'GET /api/library/universes': ({ headers }: { headers: Headers }) =>
          universePage(
            headers.get(WORKSPACE_HEADER) === String(TEAM.id)
              ? [universeSummary({ name: 'Team World' })]
              : [universeSummary({ name: 'Own World' })]
          ),
      }
    )
    await expect.element(screen.getByText('Own World')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Mara Ilven: switch workspace' })
      .click()
    await screen.getByRole('menuitem', { name: /Studio Team/ }).click()
    await expect.element(screen.getByText('Team World')).toBeVisible()
    expect(screen.getByText('Own World').query()).toBeNull()
  })
})

function ShelfNames() {
  const universes = useUniverses(NO_UNIVERSE_FILTERS)
  const first = universes.data?.pages[0]?.items[0]
  return <span>{first?.name ?? ''}</span>
}
