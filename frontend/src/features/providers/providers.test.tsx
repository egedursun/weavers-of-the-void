import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { libraryQueryClient } from '@/api/queryClients'
import { signedIn, workspace } from '@/features/accounts/accountFixtures'
import { Providers } from '@/features/accounts/providerFixtures'
import { ConnectModelStep } from './ConnectModelStep'
import { ModelsSettings } from './ModelsSettings'
import { ProvidersPanel } from './ProvidersPanel'
import { useConnectStep } from './connectStep'
import { connection, entry, loginView, providersView } from './providerFixtures'

const KEY = 'sk-live-0123456789abcdef'
const TEAM_REASON =
  'A subscription belongs to one person, so it can only be logged in to in a personal workspace.'

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: 0 },
    mutations: { retry: false },
  })
})

afterEach(() => {
  libraryQueryClient.clear()
  useConnectStep.getState().finish()
})

function routes(view: unknown, extra: Record<string, unknown> = {}) {
  return {
    'GET /api/auth/state': signedIn(),
    'GET /api/workspaces/{id}/providers': view,
    'GET /api/server/providers': view,
    ...extra,
  }
}

function panel(scope: { workspaceId: number } | 'server' = { workspaceId: 7 }) {
  return (
    <Providers>
      <ProvidersPanel scope={scope} />
    </Providers>
  )
}

describe('the providers of a scope', () => {
  it('keeps subscriptions out of a team workspace with the reason', async () => {
    const { screen } = await renderScreen(panel(), routes(providersView()))
    await expect.element(screen.getByText('This team workspace')).toBeVisible()
    await screen.getByRole('button', { name: 'Connect a provider' }).click()
    const claude = screen.getByRole('button', { name: /Claude Pro or Max/ })
    await expect.element(claude).toBeDisabled()
    await expect
      .element(claude)
      .toHaveAttribute('aria-description', TEAM_REASON)
    await expect
      .element(screen.getByRole('button', { name: /^OpenAI/ }))
      .not.toBeDisabled()
  })

  it('warns about the terms in a personal workspace and logs in after connecting', async () => {
    const claude = connection({
      id: 9,
      kind: 'claude_subscription',
      label: 'Claude Pro or Max',
      secret_hint: '',
      unusable: 'This subscription is not logged in yet.',
    })
    const { screen, server } = await renderScreen(
      panel(),
      routes(providersView({ personal: true }), {
        'POST /api/workspaces/{id}/providers/connections': claude,
        'POST /api/workspaces/{id}/providers/connections/{cid}/login':
          loginView(),
      })
    )
    await expect
      .element(screen.getByText('Your personal workspace', { exact: true }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Connect a provider' }).click()
    await screen.getByRole('button', { name: /Claude Pro or Max/ }).click()
    await expect
      .element(screen.getByText('Mind the terms of the provider'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Connect', exact: true }).click()
    expect(
      server.callsTo('POST /api/workspaces/{id}/providers/connections')[0].body
    ).toEqual({
      kind: 'claude_subscription',
      label: '',
      secret: '',
      base_url: '',
    })
    await expect
      .element(
        screen.getByRole('heading', { name: 'Log in to Claude Pro or Max' })
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Start logging in' }).click()
    await expect.element(screen.getByText('ABCD-1234').first()).toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Open the sign-in page' }))
      .toHaveAttribute('href', 'https://github.com/login/device')
    await userEvent.fill(screen.getByLabelText('Paste a code back'), '4/abc')
    await screen.getByRole('button', { name: 'Send', exact: true }).click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'POST /api/workspaces/{id}/providers/connections/{cid}/login/input'
          )[0]?.body
      )
      .toEqual({ text: '4/abc' })
    await screen.getByRole('button', { name: 'Press Enter' }).click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'POST /api/workspaces/{id}/providers/connections/{cid}/login/input'
          )[1]?.body
      )
      .toEqual({ text: '' })
  })

  it('shows the card logged in as soon as the login succeeds, without a reload', async () => {
    const waiting = connection({
      id: 9,
      kind: 'copilot_subscription',
      label: 'GitHub Copilot',
      secret_hint: '',
      logged_in_at: null,
      unusable: 'This subscription is not logged in yet.',
    })
    const done = connection({
      ...waiting,
      logged_in_at: '2026-11-26T08:01:00+00:00',
      unusable: null,
    })
    let logins = 0
    let finished = false
    const { screen } = await renderScreen(
      panel(),
      routes(
        () =>
          providersView({
            personal: true,
            connections: [finished ? done : waiting],
          }),
        {
          'POST /api/workspaces/{id}/providers/connections/{cid}/login':
            loginView(),
          'GET /api/workspaces/{id}/providers/connections/{cid}/login': () => {
            logins += 1
            finished = logins > 1
            return finished
              ? loginView({
                  state: 'succeeded',
                  ended_at: '2026-11-26T08:01:00+00:00',
                })
              : loginView()
          },
        }
      )
    )
    await expect.element(screen.getByText('Not logged in')).toBeVisible()
    await screen.getByRole('button', { name: 'Log in', exact: true }).click()
    await expect
      .element(screen.getByText(/^Logged in/).first(), { timeout: 5000 })
      .toBeVisible()
    await expect
      .element(screen.getByText('Not logged in'))
      .not.toBeInTheDocument()
  })

  it('drops the dead code and sign-in page once a login has stopped', async () => {
    const copilot = connection({
      id: 9,
      kind: 'copilot_subscription',
      label: 'GitHub Copilot',
      secret_hint: '',
      logged_in_at: null,
      unusable: 'This subscription is not logged in yet.',
    })
    const { screen } = await renderScreen(
      panel(),
      routes(providersView({ personal: true, connections: [copilot] }), {
        'POST /api/workspaces/{id}/providers/connections/{cid}/login':
          loginView({
            state: 'cancelled',
            ended_at: '2026-11-26T08:01:00+00:00',
          }),
      })
    )
    await screen.getByRole('button', { name: 'Log in', exact: true }).click()
    await screen.getByRole('button', { name: 'Start logging in' }).click()
    await expect.element(screen.getByText('Stopped')).toBeVisible()
    await expect.element(screen.getByText('What the agent says')).toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Open the sign-in page' }))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByText('The code to enter'))
      .not.toBeInTheDocument()
  })

  it('shows one scope at a time, the server default on its own tab', async () => {
    const { screen } = await renderScreen(
      <Providers>
        <ModelsSettings workspaceId={7} showServer />
      </Providers>,
      routes(providersView({ personal: true }))
    )
    await expect
      .element(screen.getByText('Your personal workspace', { exact: true }))
      .toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Connections' }).elements()
    ).toHaveLength(1)
    await screen.getByRole('tab', { name: 'Server default' }).click()
    await expect.element(screen.getByText('The server default')).toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Connections' }).elements()
    ).toHaveLength(1)
  })

  it('names the server default and seals a pasted key', async () => {
    const { screen, server } = await renderScreen(
      panel('server'),
      routes(providersView({ workspace_id: null }), {
        'POST /api/server/providers/connections': connection({
          id: 4,
          label: 'Studio',
          secret_hint: 'cdef',
        }),
      })
    )
    await expect.element(screen.getByText('The server default')).toBeVisible()
    await screen.getByRole('button', { name: 'Connect a provider' }).click()
    await screen.getByRole('button', { name: /^OpenAI/ }).click()
    await expect
      .element(screen.getByRole('link', { name: 'Get a key from OpenAI' }))
      .toHaveAttribute('href', 'https://platform.openai.com/api-keys')
    await userEvent.fill(
      screen.getByLabelText('Name of the connection'),
      'Studio'
    )
    await userEvent.fill(screen.getByLabelText('Key', { exact: true }), KEY)
    await screen.getByRole('button', { name: 'Connect', exact: true }).click()
    await expect
      .poll(
        () => server.callsTo('POST /api/server/providers/connections')[0]?.body
      )
      .toEqual({ kind: 'openai', label: 'Studio', secret: KEY, base_url: '' })
    await expect
      .element(screen.getByRole('heading', { name: 'Connect OpenAI' }))
      .not.toBeInTheDocument()
    expect(document.body.textContent).not.toContain(KEY)
    await expect.element(screen.getByText(/Key ending in cdef/)).toBeVisible()
  })

  it('saves a chain in the order it is set', async () => {
    const view = providersView({
      connections: [
        connection({ id: 1 }),
        connection({ id: 2, label: 'Fallback' }),
      ],
      writing: [
        entry({ id: 11, connection_id: 1, model: 'quick' }),
        entry({ id: 12, connection_id: 2, model: 'steady' }),
      ],
    })
    const { screen, server } = await renderScreen(
      panel(),
      routes(view, {
        'PUT /api/workspaces/{id}/providers/roles/{role}': view.roles[1],
      })
    )
    const writing = screen.getByRole('region', { name: 'Writing' })
    await expect
      .element(writing.getByLabelText('Model of entry 1'))
      .toHaveValue('quick')
    await writing.getByRole('button', { name: 'Move entry 1 down' }).click()
    await writing.getByRole('button', { name: 'Add a model' }).click()
    await userEvent.fill(writing.getByLabelText('Model of entry 3'), 'last')
    await writing.getByRole('button', { name: 'Save the chain' }).click()
    await expect
      .poll(
        () =>
          server.callsTo('PUT /api/workspaces/{id}/providers/roles/{role}')[0]
            ?.body
      )
      .toEqual({
        entries: [
          { connection_id: 2, model: 'steady' },
          { connection_id: 1, model: 'quick' },
          { connection_id: 1, model: 'last' },
        ],
      })
  })

  it('shows what a check found and checks again on request', async () => {
    const view = providersView({
      writing: [
        entry({
          id: 11,
          connection_id: 1,
          tools_work: true,
          checked_at: '2026-11-26T08:00:00+00:00',
        }),
      ],
      conversation: [
        entry({
          id: 12,
          connection_id: 1,
          model: 'deep',
          tools_work: true,
          sees_images: true,
        }),
      ],
      serverImages: [entry({ id: 13, connection_id: 1, model: 'painter' })],
    })
    const { screen, server } = await renderScreen(
      panel(),
      routes(view, {
        'POST /api/workspaces/{id}/providers/roles/{role}/check': view.roles[2],
      })
    )
    const conversation = screen.getByRole('region', { name: 'Conversation' })
    await expect.element(conversation.getByText('Uses tools')).toBeVisible()
    await expect.element(conversation.getByText('Sees pictures')).toBeVisible()
    await expect
      .element(
        screen
          .getByRole('region', { name: 'Images' })
          .getByText('Uses the server default')
      )
      .toBeVisible()
    await conversation.getByRole('button', { name: 'Check the models' }).click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'POST /api/workspaces/{id}/providers/roles/{role}/check'
          ).length
      )
      .toBe(1)
  })

  it('shows a viewer everything with every control disabled and its reason', async () => {
    const { screen } = await renderScreen(
      panel(),
      routes(
        providersView({
          editable: false,
          writing: [entry({ id: 11, connection_id: 1 })],
        })
      )
    )
    const reason = 'Only administrators of the workspace change its models.'
    await expect.element(screen.getByText(reason).first()).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Connect a provider' }))
      .toHaveAttribute('aria-description', reason)
    await expect
      .element(screen.getByRole('button', { name: 'Acts on Studio key' }))
      .toBeDisabled()
    await expect
      .element(
        screen
          .getByRole('region', { name: 'Writing' })
          .getByRole('button', { name: 'Check the models' })
      )
      .toBeDisabled()
    await expect
      .element(
        screen
          .getByRole('region', { name: 'Writing' })
          .getByRole('button', { name: 'Save the chain' })
      )
      .not.toBeInTheDocument()
  })
})

describe('the step after setup', () => {
  it('waits for a model before going on and can be skipped', async () => {
    useConnectStep.getState().show()
    const { screen } = await renderScreen(
      <Providers>
        <ConnectModelStep />
      </Providers>,
      routes(providersView({ personal: true }), {
        'GET /api/workspaces': [workspace({ id: 7, kind: 'personal' })],
      })
    )
    await expect
      .element(screen.getByText('Your personal workspace', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Continue' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Skip for now' }).click()
    expect(useConnectStep.getState().open).toBe(false)
  })

  it('goes on once a role has a model', async () => {
    useConnectStep.getState().show()
    const { screen } = await renderScreen(
      <Providers>
        <ConnectModelStep />
      </Providers>,
      routes(
        providersView({
          personal: true,
          writing: [entry({ id: 11, connection_id: 1 })],
        }),
        { 'GET /api/workspaces': [workspace({ id: 7, kind: 'personal' })] }
      )
    )
    const go = screen.getByRole('button', { name: 'Continue' })
    await expect.element(go).not.toBeDisabled()
    await go.click()
    expect(useConnectStep.getState().open).toBe(false)
  })
})
