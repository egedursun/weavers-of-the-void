import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { setTeamGate } from '@/api/teamGate'
import { Button } from '@/components/ui/button'
import { UndoButton } from '@/features/divine-will/UndoButton'
import { LedgerFilters } from '@/features/ledger/LedgerFilters'
import { type LedgerQuery } from '@/features/ledger/api'
import { useGodAction } from '@/features/pantheon/godAction'

const QUEUED = {
  id: 3,
  source: 'lever',
  action_id: 'title:edit',
  title: 'Edit a title',
  payload: {},
  reason: null,
  author: { account_id: 1, name: 'Ana' },
  queued_epoch: 4,
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
}

const PROPOSAL = {
  id: 6,
  action_id: 'canon:strike',
  title: 'Strike the oath',
  payload: {},
  reason: null,
  preview: {},
  touches: ['canon_status'],
  held_node_ids: [],
  author: { account_id: 1, name: 'Ana' },
  proposed_epoch: 4,
  proposed_at: '2026-11-25T10:00:00Z',
  status: 'pending',
  decided_by: null,
  decided_at: null,
  note: '',
  result: '',
  ledger_entry_id: null,
}

const CATALOGUE = [
  {
    id: 'title:edit',
    title: 'Edit a title',
    group: 'cosmos',
    mode: 'instant',
    cost: '',
    confirmation: null,
    rows: [],
    path: '/api/actions/title:edit',
    permission: 'edit_world',
    hold_fields: [],
    method: 'POST',
    input_schema: {},
  },
]

function Lever() {
  const act = useGodAction({
    writes: [{ lever: 'title:edit' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/title:edit', {
          body: { title_id: 1, clear_liege: false, hold: false },
        })
      ),
    success: 'Title edited',
  })
  return (
    <Button act={act} onClick={() => act.mutate()}>
      Edit
    </Button>
  )
}

afterEach(() => setTeamGate(null))

describe('what the server did with an act', () => {
  it('says an act waits for the age instead of claiming it is done', async () => {
    const { screen } = await renderScreen(<Lever />, {
      'GET /api/actions': CATALOGUE,
      'POST /api/actions/title:edit': {
        action: 'title:edit',
        message: 'Queued',
        queued: QUEUED,
      },
    })
    await screen.getByRole('button', { name: 'Edit' }).click()
    await expect
      .element(
        screen.getByText('Waiting for the age to end — it runs right after')
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Title edited'))
      .not.toBeInTheDocument()
  })

  it('says an act went to canon review', async () => {
    const { screen } = await renderScreen(<Lever />, {
      'GET /api/actions': CATALOGUE,
      'POST /api/actions/title:edit': {
        action: 'title:edit',
        message: 'Proposed',
        proposal: PROPOSAL,
      },
    })
    await screen.getByRole('button', { name: 'Edit' }).click()
    await expect
      .element(screen.getByText('Sent for canon review'))
      .toBeVisible()
  })

  it('refuses a lever the catalogue gives to a permission the person lacks', async () => {
    setTeamGate({
      universe: 'Haluvra',
      refusals: { edit_world: 'Viewers of Haluvra cannot change it.' },
      adminRefusal: null,
    })
    const { screen } = await renderScreen(<Lever />, {
      'GET /api/actions': CATALOGUE,
    })
    await expect
      .element(screen.getByRole('button', { name: 'Edit' }))
      .toHaveAttribute(
        'aria-description',
        'Viewers of Haluvra cannot change it.'
      )
  })

  it('says an undo waits for the age', async () => {
    const { screen } = await renderScreen(<UndoButton entryId={12} />, {
      'POST /api/ledger/{entry_id}/undo': QUEUED,
    })
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .element(
        screen.getByText('Waiting for the age to end — it runs right after')
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('The act is undone.'))
      .not.toBeInTheDocument()
  })

  it('says an undo is done when it is', async () => {
    const { screen } = await renderScreen(<UndoButton entryId={12} />, {
      'POST /api/ledger/{entry_id}/undo': {
        entry_id: 12,
        applied: [],
        conflicts: [],
      },
    })
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect.element(screen.getByText('The act is undone.')).toBeVisible()
  })
})

describe('the ledger filters', () => {
  it('filters by kind of act and by dates', async () => {
    const changes: Partial<LedgerQuery>[] = []
    const query: LedgerQuery = {
      epoch: null,
      actorKind: null,
      actorId: null,
      limit: null,
      authorId: null,
      actionKind: null,
      since: null,
      until: null,
    }
    const { screen } = await renderScreen(
      <LedgerFilters query={query} onChange={(next) => changes.push(next)} />
    )
    await userEvent.fill(screen.getByLabelText('From'), '2026-11-01')
    expect(changes.at(-1)).toEqual({ since: '2026-11-01T00:00:00.000Z' })
    await userEvent.fill(screen.getByLabelText('To'), '2026-11-20')
    expect(changes.at(-1)).toEqual({ until: '2026-11-20T23:59:59.999Z' })
    await screen.getByRole('combobox', { name: 'Kind of act' }).click()
    await userEvent.keyboard('golden')
    await screen
      .getByRole('option', { name: /golden age/i })
      .first()
      .click()
    expect(changes.at(-1)).toEqual({ actionKind: 'golden_age' })
  })
})
