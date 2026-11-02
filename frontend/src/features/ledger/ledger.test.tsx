import { QueryClient } from '@tanstack/react-query'
import { worldState } from '@/test-utils/fixtures'
import {
  failure,
  startMockServer,
  type MockRequest,
} from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { toast } from 'sonner'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { ThemeProvider } from '@/context/ThemeProvider'
import { Toaster } from '@/components/ui/sonner'
import { ActionLedger } from './ActionLedger'
import { Bookmarks } from './Bookmarks'
import { LedgerScreen } from './LedgerScreen'
import { MyNotes } from './MyNotes'
import { UNDO_TOAST_MS, toastWithUndo, undoMessage } from './undoToast'

type Page = {
  id: number
  epoch?: number
  actor?: string
  label?: string
  changes?: number
  undone?: boolean
  dependents?: number[]
  rows?: string[]
  summary?: string | null
  conflicts?: string[]
}

function view(page: Page) {
  return {
    entry: {
      id: page.id,
      epoch: page.epoch ?? 3,
      actor_kind: 'creator',
      actor_node_id: null,
      actor_name: page.actor ?? 'Ana',
      tool: 'bless',
      action_kind: 'god',
      input_summary: page.summary ?? null,
      undone: page.undone ?? false,
      undone_at: null,
      applied: [],
      conflicts: page.conflicts ?? [],
      created_at: '2026-01-01T12:00:00Z',
    },
    label: page.label ?? 'Blessed a son',
    change_count: page.changes ?? 2,
    rows: page.rows ?? [],
    dependents: page.dependents ?? [],
  }
}

function ledgerRoutes(
  pages: Page[],
  extra: Record<string, unknown> = {},
  state: Record<string, unknown> = {}
) {
  return {
    'GET /api/ledger': (request: MockRequest) => {
      const epoch = request.query.get('epoch')
      const rows = pages.filter(
        (page) => !epoch || String(page.epoch ?? 3) === epoch
      )
      return {
        current_epoch: 3,
        epochs: [
          { epoch: 3, entries: 2, undone: 1 },
          { epoch: 2, entries: 1, undone: 0 },
        ],
        entries: rows.map(view),
      }
    },
    'GET /api/state': worldState(state),
    'GET /api/names': [],
    'GET /api/rules': [
      {
        namespace: 'ledger',
        key: 'keep_epochs',
        value: 40,
        default: 40,
        minimum: 1,
        maximum: 100,
        group: 'ledger',
        label: 'Keep',
        integer: true,
      },
      {
        namespace: 'server',
        key: 'ledger_page_size',
        value: 2,
        default: 2,
        minimum: 1,
        maximum: 50,
        group: 'server',
        label: 'Page',
        integer: true,
      },
      {
        namespace: 'server',
        key: 'ledger_page_max',
        value: 6,
        default: 6,
        minimum: 1,
        maximum: 50,
        group: 'server',
        label: 'Max',
        integer: true,
      },
    ],
    'GET /api/catalogue/enums': failure(404, 'none'),
    ...extra,
  }
}

beforeEach(() => localStorage.clear())
afterEach(() => localStorage.clear())

describe('action ledger list', () => {
  it('shows each page with actor, label, change count, summary and details', async () => {
    const { screen } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes([
        {
          id: 7,
          actor: 'Ana',
          label: 'Blessed Ithren',
          changes: 3,
          summary: 'amount 20',
          rows: ['Ithren essence +20'],
        },
        { id: 6, epoch: 2, undone: true, label: 'Cursed Valka', changes: 1 },
      ])
    )
    await expect.element(screen.getByText('#7 · Epoch 3')).toBeInTheDocument()
    await expect.element(screen.getByText('Blessed Ithren')).toBeInTheDocument()
    await expect.element(screen.getByText('3 changes')).toBeInTheDocument()
    await expect.element(screen.getByText('amount 20')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Undone', { exact: true }))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Details' }).click()
    await expect
      .element(screen.getByText('Ithren essence +20'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText(/Pages of the last 40 epochs are kept/))
      .toBeInTheDocument()
  })

  it('filters by epoch and explains an empty filter', async () => {
    const { screen, server } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes([{ id: 7 }])
    )
    await expect.element(screen.getByText('#7 · Epoch 3')).toBeInTheDocument()
    await screen.getByRole('combobox', { name: 'Epoch' }).click()
    await screen.getByRole('option', { name: 'Epoch 2 · 1 pages' }).click()
    await expect
      .element(screen.getByText('No page matches this filter'))
      .toBeInTheDocument()
    expect(
      server
        .callsTo('GET /api/ledger')
        .some((call) => call.query.get('epoch') === '2')
    ).toBe(true)
  })

  it('filters by actor including each son', async () => {
    const { screen, server } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes(
        [{ id: 7 }],
        {},
        { sons: [{ son: { id: 4, name: 'Ithren' } }], creator: { name: 'Ana' } }
      )
    )
    await screen.getByRole('combobox', { name: 'Who acted' }).click()
    await screen.getByRole('option', { name: 'Ithren' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/ledger')
          .some(
            (call) =>
              call.query.get('actor_kind') === 'son' &&
              call.query.get('actor_id') === '4'
          )
      )
      .toBe(true)
  })

  it('grows the page up to the cap and then asks for an epoch', async () => {
    const pages = [8, 7, 6, 5, 4, 3, 2].map((id) => ({ id }))
    const { screen, server } = await renderScreen(<ActionLedger />, {
      ...ledgerRoutes([]),
      'GET /api/ledger': (request: MockRequest) => {
        const limit = Number(request.query.get('limit') ?? 2)
        return {
          current_epoch: 3,
          epochs: [],
          entries: pages.slice(0, limit).map(view),
        }
      },
    })
    await expect.element(screen.getByText('2 pages shown')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'More older pages' }).click()
    await expect.element(screen.getByText('4 pages shown')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'More older pages' }).click()
    await expect.element(screen.getByText('6 pages shown')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Pick an epoch to see older pages.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'More older pages' }))
      .not.toBeInTheDocument()
    expect(
      server.callsTo('GET /api/ledger').map((call) => call.query.get('limit'))
    ).toContain('6')
  })

  it('shows the empty ledger', async () => {
    const { screen } = await renderScreen(<ActionLedger />, ledgerRoutes([]))
    await expect
      .element(screen.getByText('The ledger is empty'))
      .toBeInTheDocument()
  })
})

describe('undoing a ledger page', () => {
  it('confirms, undoes, refunds and lists the conflicts in a result box', async () => {
    const pages: Page[] = [
      { id: 7, label: 'Blessed Ithren', dependents: [8, 9] },
    ]
    const { screen, server } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes(pages, {
        'POST /api/ledger/7/undo': () => {
          pages[0].undone = true
          return {
            entry_id: 7,
            applied: ['Ithren essence -20'],
            conflicts: ['Ithren was renamed later'],
          }
        },
      })
    )
    await expect
      .element(
        screen.getByText(
          'The next 2 pages touched what this one created: #8, #9'
        )
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Undo page #7?' }))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByText(
          /The next 2 pages depend on this one.*Spent essence is refunded/
        )
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Undo anyway' }).click()
    await expect
      .element(
        screen
          .getByText('Undone: 1 change reverted, 1 conflict skipped')
          .first()
      )
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Ithren was renamed later'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Undone', { exact: true }))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/ledger/7/undo')).toHaveLength(1)
  })

  it('uses the plain confirm without dependants and says the page was torn out', async () => {
    const pages: Page[] = [{ id: 7 }]
    const { screen } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes(pages, {
        'POST /api/ledger/7/undo': () => {
          pages[0].undone = true
          return { entry_id: 7, applied: ['a', 'b'], conflicts: [] }
        },
      })
    )
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .element(
        screen.getByText(
          'Its changes are reverted and any essence it spent is refunded.'
        )
      )
      .toBeInTheDocument()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Undo' })
      .click()
    await expect
      .element(
        screen.getByText('Page torn from the ledger: 2 changes undone').first()
      )
      .toBeInTheDocument()
  })

  it('refuses while an epoch runs and for pages that changed nothing', async () => {
    const running = await renderScreen(
      <ActionLedger />,
      ledgerRoutes([{ id: 7 }], {}, { epoch_running: true })
    )
    await expect
      .element(running.screen.getByRole('button', { name: 'Undo' }))
      .toHaveAttribute(
        'aria-description',
        'A page cannot be torn out while the epoch runs'
      )
  })

  it('refuses a page that changed nothing', async () => {
    const { screen } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes([{ id: 7, changes: 0 }])
    )
    await expect
      .element(screen.getByRole('button', { name: 'Undo' }))
      .toHaveAttribute('aria-description', 'This page changed nothing')
  })

  it('shows the server refusal', async () => {
    const { screen } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes([{ id: 7 }], {
        'POST /api/ledger/7/undo': failure(409, 'The page cannot be undone.'),
      })
    )
    await screen.getByRole('button', { name: 'Undo' }).click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Undo' })
      .click()
    await expect
      .element(screen.getByText('The page cannot be undone.'))
      .toBeInTheDocument()
  })

  it('keeps conflicts of an already undone page visible', async () => {
    const { screen } = await renderScreen(
      <ActionLedger />,
      ledgerRoutes([{ id: 7, undone: true, conflicts: ['Valka moved away'] }])
    )
    await expect
      .element(screen.getByText('Valka moved away'))
      .toBeInTheDocument()
  })
})

describe('undo message text', () => {
  it('words conflicts and clean undos differently', () => {
    expect(undoMessage(2, 0)).toBe(
      'Page torn from the ledger: 2 changes undone'
    )
    expect(undoMessage(1, 3)).toBe(
      'Undone: 1 change reverted, 3 conflicts skipped'
    )
  })
})

describe('undo offer in the success toast', () => {
  function Host() {
    return (
      <ThemeProvider>
        <Toaster />
      </ThemeProvider>
    )
  }

  it('carries an Undo button for seven seconds that runs the undo', async () => {
    toast.dismiss()
    const server = startMockServer({
      'POST /api/ledger/12/undo': {
        entry_id: 12,
        applied: ['x'],
        conflicts: [],
      },
    })
    const screen = await render(<Host />)
    const client = new QueryClient()
    toastWithUndo(client, 'Blessed Ithren', 12)
    expect(UNDO_TOAST_MS).toBe(7000)
    await expect.element(screen.getByText('Blessed Ithren')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .element(screen.getByText('Page torn from the ledger: 1 change undone'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/ledger/12/undo')).toHaveLength(1)
    server.stop()
  })

  it('has no button when the action wrote no ledger page', async () => {
    toast.dismiss()
    const screen = await render(<Host />)
    toastWithUndo(new QueryClient(), 'Nothing to undo here', null)
    await expect
      .element(screen.getByText('Nothing to undo here'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Undo' }))
      .not.toBeInTheDocument()
  })

  it('reports an undo that fails', async () => {
    toast.dismiss()
    const server = startMockServer({
      'POST /api/ledger/13/undo': failure(409, 'Already undone.'),
    })
    const screen = await render(<Host />)
    toastWithUndo(new QueryClient(), 'Cursed Valka', 13)
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .element(screen.getByText('Already undone.'))
      .toBeInTheDocument()
    server.stop()
  })
})

describe('records screen', () => {
  const routes = {
    ...ledgerRoutes([{ id: 7 }]),
    'GET /api/notes': { entity_notes: [] },
    'GET /api/map-notes': [],
    'GET /api/notifications': {
      unread: 0,
      counts: [],
      settings: {},
      categories: [],
      items: [],
    },
    'GET /api/favorites': [],
  }

  it('opens on the ledger tab and remembers the chosen tab', async () => {
    const { screen } = await renderScreen(<LedgerScreen />, routes)
    await expect
      .element(screen.getByRole('tab', { name: 'Ledger' }))
      .toHaveAttribute('aria-selected', 'true')
    await screen.getByRole('tab', { name: 'Bookmarks' }).click()
    await expect
      .element(screen.getByText('No favourites yet'))
      .toBeInTheDocument()
    expect(localStorage.getItem('aerona.records-tab')).toBe('bookmarks')
  })

  it('restores the remembered tab', async () => {
    localStorage.setItem('aerona.records-tab', 'notes')
    const { screen } = await renderScreen(<LedgerScreen />, routes)
    await expect
      .element(screen.getByRole('tab', { name: 'Notes' }))
      .toHaveAttribute('aria-selected', 'true')
    await expect
      .element(screen.getByText('No record notes yet'))
      .toBeInTheDocument()
  })

  it('ignores an unknown remembered tab', async () => {
    localStorage.setItem('aerona.records-tab', 'garbage')
    const { screen } = await renderScreen(<LedgerScreen />, routes)
    await expect
      .element(screen.getByRole('tab', { name: 'Ledger' }))
      .toHaveAttribute('aria-selected', 'true')
  })
})

describe('bookmarks tab', () => {
  it('lists favourite records with their type', async () => {
    const { screen } = await renderScreen(<Bookmarks />, {
      'GET /api/favorites': [
        { id: 3, name: 'Stonehold', entity_type: 'settlement' },
        { id: 4, name: 'Old Nyx', entity_type: 'creature' },
      ],
    })
    await expect
      .element(screen.getByText('Favourite records (2)'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Stonehold' }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Settlement')).toBeInTheDocument()
  })

  it('shows the error of a failed load', async () => {
    const { screen } = await renderScreen(<Bookmarks />, {
      'GET /api/favorites': failure(500, 'No favourites today.'),
    })
    await expect
      .element(screen.getByText('No favourites today.'))
      .toBeInTheDocument()
  })
})

describe('my notes', () => {
  const noteRoutes = (notes: unknown[] = []) => ({
    'GET /api/state': worldState({ worlds: [{ id: 1, name: 'Aerona' }] }),
    'GET /api/notes': { entity_notes: notes },
    'GET /api/map-notes': [
      {
        id: 1,
        world_id: 1,
        x: 0,
        y: 0,
        text: 'Camp here',
        color: null,
        created_at: 'x',
      },
    ],
    'GET /api/notifications': {
      unread: 0,
      counts: [],
      settings: {},
      categories: [],
      items: [
        {
          id: 5,
          epoch: 2,
          category: 'note',
          severity: 1,
          title: 'Reconcile the sons',
          body: 'Soon',
          target_node_id: null,
          chronicle_id: null,
          is_read: false,
          created_at: 'x',
        },
      ],
    },
  })

  it('collects record notes, notes to yourself and map notes', async () => {
    const { screen } = await renderScreen(
      <MyNotes />,
      noteRoutes([
        {
          entity_id: 3,
          entity_name: 'Stonehold',
          entity_type: 'settlement',
          world_id: 1,
          text: 'Wall is weak',
        },
      ])
    )
    await expect
      .element(screen.getByText('Record notes (1)'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Wall is weak')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Notes to yourself (1)'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Reconcile the sons'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Map notes (1)')).toBeInTheDocument()
    await expect.element(screen.getByText('Camp here')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'On the map' }))
      .toBeInTheDocument()
  })

  it('deletes a record note after confirmation', async () => {
    const notes = [
      {
        entity_id: 3,
        entity_name: 'Stonehold',
        entity_type: 'settlement',
        world_id: 1,
        text: 'Wall is weak',
      },
    ]
    const { screen, server } = await renderScreen(<MyNotes />, {
      ...noteRoutes(),
      'GET /api/notes': () => ({ entity_notes: notes }),
      'DELETE /api/entities/3/note': () => {
        notes.length = 0
        return {}
      },
    })
    await screen
      .getByRole('button', { name: 'Delete the note on Stonehold' })
      .click()
    await expect
      .element(
        screen.getByRole('heading', { name: 'Delete the note on Stonehold?' })
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Delete note' }).click()
    await expect
      .element(screen.getByText('No record notes yet'))
      .toBeInTheDocument()
    expect(server.callsTo('DELETE /api/entities/3/note')).toHaveLength(1)
  })

  it('shows empty states with a way forward', async () => {
    const { screen } = await renderScreen(<MyNotes />, {
      ...noteRoutes(),
      'GET /api/map-notes': [],
      'GET /api/notifications': {
        unread: 0,
        counts: [],
        settings: {},
        categories: [],
        items: [],
      },
    })
    await expect
      .element(screen.getByRole('link', { name: 'Open the atlas' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Open notifications' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Open the map' }))
      .toBeInTheDocument()
  })
})
