import { type ReactNode } from 'react'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { takeReason } from '@/api/actReason'
import { actNoteMiddleware } from '@/api/conflicts'
import { noteRevision, settleEdit, watchEditing } from '@/api/editSession'
import { useMutation } from '@/api/mutation'
import { setTeamGate } from '@/api/teamGate'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { ConfirmDialog } from '@/components/domain'
import { ConflictDialog } from './ConflictDialog'
import { PresentFaces } from './Presence'
import { ProposalCard } from './Proposals'
import { QueuedRow } from './Queue'
import { ShareToggle } from './share'
import { TeamContext, type TeamContextValue } from './teamContext'
import {
  type CanonProposalView,
  type QueuedActView,
  type TeamView,
} from './types'

const VIEWER_REFUSAL = 'Viewers of Haluvra cannot change it.'

function team(change: Partial<TeamView> = {}): TeamView {
  return {
    role: 'editor',
    permissions: [],
    canon_approval: false,
    present: [],
    queued: 0,
    proposals: 0,
    revision: 4,
    world_busy: false,
    me: { account_id: 1, name: 'Ana' },
    heartbeat_seconds: 30,
    presence_ttl_seconds: 90,
    ...change,
  }
}

function context(change: Partial<TeamContextValue> = {}): TeamContextValue {
  return {
    team: team(),
    universe: 'Haluvra',
    role: 'editor',
    me: 1,
    can: () => true,
    ...change,
  }
}

function inTeam(node: ReactNode, value: TeamContextValue = context()) {
  return <TeamContext value={value}>{node}</TeamContext>
}

function queued(change: Partial<QueuedActView> = {}): QueuedActView {
  return {
    id: 7,
    source: 'lever',
    action_id: 'title:edit',
    title: 'Edit a title',
    payload: {},
    reason: 'The crown passes',
    author: { account_id: 1, name: 'Ana' },
    queued_epoch: 3,
    queued_at: '2026-11-25T10:00:00Z',
    status: 'queued',
    result: '',
    applied_at: null,
    ledger_entry_id: null,
    cancelled_by: null,
    plan_id: null,
    plan_ordinal: null,
    presence_session_id: null,
    conflict: [],
    proposal_id: null,
    ...change,
  }
}

function proposal(change: Partial<CanonProposalView> = {}): CanonProposalView {
  return {
    id: 9,
    action_id: 'canon:strike',
    title: 'Strike the old oath',
    payload: { record_id: 4 },
    reason: 'It never happened',
    preview: { status: 'struck' },
    touches: ['canon_status'],
    held_node_ids: [],
    author: { account_id: 2, name: 'Bora' },
    proposed_epoch: 3,
    proposed_at: '2026-11-25T10:00:00Z',
    status: 'pending',
    decided_by: null,
    decided_at: null,
    note: '',
    result: '',
    ledger_entry_id: null,
    ...change,
  }
}

function Act() {
  const act = useMutation({
    writes: [{ method: 'PATCH', path: '/api/rules' }],
    mutationFn: () => Promise.resolve(null),
  })
  return (
    <Button act={act} onClick={() => act.mutate()}>
      Change the rules
    </Button>
  )
}

afterEach(() => {
  setTeamGate(null)
  settleEdit()
})

describe('the team gate', () => {
  it('disables a refused act and says why, and lets it run once allowed', async () => {
    setTeamGate({
      universe: 'Haluvra',
      refusals: { change_rules: VIEWER_REFUSAL },
      adminRefusal: 'Only administrators of Haluvra can do this.',
    })
    const { screen } = await renderScreen(<Act />)
    const button = screen.getByRole('button', { name: 'Change the rules' })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(button)
      .toHaveAttribute('aria-description', VIEWER_REFUSAL)
    setTeamGate({ universe: 'Haluvra', refusals: {}, adminRefusal: null })
    await expect.element(button).not.toHaveAttribute('aria-disabled')
  })

  it('turns a hold switch off and explains when canon may not be locked', async () => {
    setTeamGate({
      universe: 'Haluvra',
      refusals: {
        lock_canon: 'Editors of Haluvra cannot lock or release its canon.',
      },
      adminRefusal: null,
    })
    const { screen } = await renderScreen(
      <Switch permission='lock_canon' checked aria-label='Hold what I set' />
    )
    const toggle = screen.getByRole('switch', { name: 'Hold what I set' })
    await expect.element(toggle).toBeDisabled()
    await expect.element(toggle).toHaveAttribute('aria-checked', 'false')
  })
})

describe('the reason of an act', () => {
  it('passes the reason typed in the confirmation to the next write', async () => {
    let confirmed = false
    function Confirm() {
      const act = useMutation({
        writes: [{ method: 'PATCH', path: '/api/rules' }],
        mutationFn: () => Promise.resolve(null),
      })
      return (
        <ConfirmDialog
          act={act}
          open
          onOpenChange={() => undefined}
          title='Reset the rules?'
          desc='Every rule goes back to its default.'
          handleConfirm={() => {
            confirmed = true
          }}
        />
      )
    }
    const { screen } = await renderScreen(<Confirm />)
    await userEvent.fill(
      screen.getByLabelText('Why (optional)'),
      'The world grew too harsh'
    )
    await screen.getByRole('button', { name: 'Continue' }).click()
    expect(confirmed).toBe(true)
    expect(takeReason()).toBe('The world grew too harsh')
    expect(takeReason()).toBeNull()
  })
})

describe('people here now', () => {
  it('shows the faces of others with where they are and hides those gone quiet', async () => {
    const value = context({
      team: team({
        present: [
          {
            account_id: 1,
            name: 'Ana',
            screen: '/atlas',
            node_id: null,
            editing: false,
            seen_seconds_ago: 2,
          },
          {
            account_id: 2,
            name: 'Bora Kaya',
            screen: '/atlas',
            node_id: null,
            editing: true,
            seen_seconds_ago: 5,
          },
          {
            account_id: 3,
            name: 'Cem',
            screen: '/map',
            node_id: null,
            editing: false,
            seen_seconds_ago: 300,
          },
        ],
      }),
    })
    const { screen } = await renderScreen(inTeam(<PresentFaces />, value), {
      'GET /api/names': [],
    })
    const faces = screen.getByRole('button', { name: 'Here now: Bora Kaya' })
    await expect.element(faces).toBeVisible()
    await faces.click()
    await expect.element(screen.getByText('Bora Kaya')).toBeVisible()
    await expect.element(screen.getByText('Editing')).toBeVisible()
    await expect.element(screen.getByText('Cem')).not.toBeInTheDocument()
  })
})

describe('the queue', () => {
  it('lets the author cancel a waiting act and tells another person why not', async () => {
    const { screen, server } = await renderScreen(
      inTeam(
        <ul>
          <QueuedRow act={queued()} />
          <QueuedRow
            act={queued({ id: 8, author: { account_id: 5, name: 'Deniz' } })}
          />
        </ul>
      ),
      { 'DELETE /api/team/queue/{act_id}': queued({ status: 'cancelled' }) }
    )
    const buttons = screen.getByRole('button', { name: 'Cancel it' })
    await expect
      .element(buttons.nth(1))
      .toHaveAttribute('aria-disabled', 'true')
    await buttons.nth(0).click()
    await expect
      .poll(() => server.callsTo('DELETE /api/team/queue/{act_id}').length)
      .toBe(1)
    expect(server.calls.at(-1)?.path).toBe('/api/team/queue/7')
    await expect
      .element(screen.getByText('Made in epoch 3').first())
      .toBeVisible()
    await expect
      .element(screen.getByText('“The crown passes”').first())
      .toBeVisible()
  })

  it('offers a failed act again', async () => {
    const { screen, server } = await renderScreen(
      inTeam(
        <ul>
          <QueuedRow
            act={queued({ status: 'failed', plan_id: 2, plan_ordinal: 3 })}
          />
        </ul>
      ),
      { 'POST /api/team/queue/{act_id}/retry': queued() }
    )
    await expect
      .element(screen.getByText('Step 3 of a Divine Will plan'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Try again' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/team/queue/{act_id}/retry').length)
      .toBe(1)
  })
})

describe('canon proposals', () => {
  it('lets an administrator approve or reject with a note', async () => {
    const { screen, server } = await renderScreen(
      inTeam(
        <ul>
          <ProposalCard proposal={proposal()} />
        </ul>,
        context({ role: 'admin' })
      ),
      {
        'GET /api/names': [],
        'POST /api/team/proposals/{proposal_id}/approve': proposal({
          status: 'approved',
        }),
        'POST /api/team/proposals/{proposal_id}/reject': proposal({
          status: 'rejected',
        }),
      }
    )
    await userEvent.fill(
      screen.getByLabelText('Note to the author (optional)'),
      'Agreed'
    )
    await screen.getByRole('button', { name: 'Approve' }).click()
    await expect
      .poll(
        () =>
          server.callsTo('POST /api/team/proposals/{proposal_id}/approve')
            .length
      )
      .toBe(1)
    expect(
      server.callsTo('POST /api/team/proposals/{proposal_id}/approve')[0].body
    ).toEqual({ note: 'Agreed' })
    await screen.getByRole('button', { name: 'Reject' }).click()
    await expect
      .poll(
        () =>
          server.callsTo('POST /api/team/proposals/{proposal_id}/reject').length
      )
      .toBe(1)
    await expect
      .element(screen.getByRole('button', { name: 'Withdraw' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('lets only the author withdraw, and an editor cannot decide', async () => {
    const { screen, server } = await renderScreen(
      inTeam(
        <ul>
          <ProposalCard
            proposal={proposal({ author: { account_id: 1, name: 'Ana' } })}
          />
        </ul>
      ),
      {
        'GET /api/names': [],
        'POST /api/team/proposals/{proposal_id}/withdraw': proposal({
          status: 'withdrawn',
        }),
      }
    )
    await expect
      .element(screen.getByRole('button', { name: 'Approve' }))
      .toHaveAttribute('aria-disabled', 'true')
    await screen.getByRole('button', { name: 'Withdraw' }).click()
    await expect
      .poll(
        () =>
          server.callsTo('POST /api/team/proposals/{proposal_id}/withdraw')
            .length
      )
      .toBe(1)
  })
})

describe('an edit that meets someone else’s change', () => {
  async function conflicted() {
    const unwatch = watchEditing()
    noteRevision(4)
    const field = document.createElement('input')
    document.body.append(field)
    field.focus()
    const request = new Request('http://localhost/api/actions/title:edit', {
      method: 'POST',
      body: JSON.stringify({ rank: 'king' }),
      headers: { 'content-type': 'application/json' },
    })
    const sent = (await actNoteMiddleware.onRequest?.({
      request,
    } as never)) as Request
    field.remove()
    unwatch()
    expect(new URL(sent.url).searchParams.get('expected_revision')).toBe('4')
    const response = new Response(
      JSON.stringify({
        error: 'Someone else changed this since you opened it.',
        code: 'edit_conflict',
        changes: [
          {
            table: 'titles',
            node_id: 3,
            field: 'rank',
            before: 'duke',
            after: 'prince',
            by: 'Bora',
            by_account_id: 2,
            at: null,
          },
        ],
      }),
      { status: 409, headers: { 'content-type': 'application/json' } }
    )
    return actNoteMiddleware.onResponse?.({
      request: sent,
      response,
    } as never) as Promise<Response>
  }

  it('keeps their change when asked', async () => {
    const { screen } = await renderScreen(<ConflictDialog />)
    const answer = conflicted()
    await expect.element(screen.getByText('prince')).toBeVisible()
    await expect.element(screen.getByText('king')).toBeVisible()
    await screen.getByRole('button', { name: 'Keep theirs' }).click()
    const response = await answer
    expect(response.status).toBe(409)
    expect(await response.json()).toMatchObject({ code: 'edit_kept' })
  })

  it('applies mine over theirs without the revision check', async () => {
    const { screen, server } = await renderScreen(<ConflictDialog />, {
      'POST /api/actions/title:edit': { action: 'title:edit', message: 'Done' },
    })
    const answer = conflicted()
    await screen.getByRole('button', { name: 'Apply mine over theirs' }).click()
    const response = await answer
    expect(response.status).toBe(200)
    const call = server.callsTo('POST /api/actions/title:edit')[0]
    expect(call.query.get('expected_revision')).toBeNull()
  })
})

describe('sharing a private session', () => {
  it('shares one’s own and shows who shared another', async () => {
    const { screen, server } = await renderScreen(
      <>
        <ShareToggle kind='session' id={4} shared={false} mine author='Ana' />
        <ShareToggle kind='plan' id={5} shared mine={false} author='Bora' />
      </>,
      { 'PATCH /api/divine-will/sessions/{session_id}': { ok: true } }
    )
    await expect.element(screen.getByText('Shared by Bora')).toBeVisible()
    await screen
      .getByRole('switch', { name: 'Share this session with the team' })
      .click()
    await expect
      .poll(
        () =>
          server.callsTo('PATCH /api/divine-will/sessions/{session_id}').length
      )
      .toBe(1)
    expect(
      server.callsTo('PATCH /api/divine-will/sessions/{session_id}')[0].body
    ).toEqual({ shared: true })
  })
})
