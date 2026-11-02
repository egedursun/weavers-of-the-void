import { failure, type MockRequest } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { SearchProvider } from '@/context/SearchProvider'
import { useFeedPreferences } from '@/features/feed/feedStore'
import { CommandPalette } from './CommandPalette'

afterEach(() => useFeedPreferences.setState({ open: false }))

const ACTIONS = [
  {
    id: 'bless_essence',
    title: 'Bless with essence',
    group: 'sons',
    mode: 'ledgered',
    cost: '20 essence',
    confirmation: null,
    rows: [],
    path: '/api/sons/{son_id}/bless-essence',
    method: 'POST',
    input_schema: {
      type: 'object',
      required: ['son_id', 'amount'],
      properties: {
        son_id: { type: 'integer', title: 'Son id' },
        amount: { type: 'integer', title: 'Amount' },
      },
    },
  },
  {
    id: 'kill_son',
    title: 'Kill a son',
    group: 'death',
    mode: 'ledgered',
    cost: '100 essence',
    confirmation: 'KILL',
    rows: [],
    path: '/api/sons/{son_id}/kill',
    method: 'POST',
    input_schema: {
      type: 'object',
      required: ['son_id', 'confirm'],
      properties: {
        son_id: { type: 'integer', title: 'Son id' },
        confirm: { type: 'string', title: 'Confirm' },
      },
    },
  },
]

function routes(extra: Record<string, unknown> = {}) {
  return {
    'GET /api/actions': ACTIONS,
    'GET /api/favorites': [
      { id: 3, name: 'Stonehold', entity_type: 'settlement' },
    ],
    'GET /api/search': [],
    'GET /api/state': {},
    ...extra,
  }
}

async function openPalette(extra: Record<string, unknown> = {}, path = '/') {
  const rendered = await renderScreen(
    <SearchProvider>
      <CommandPalette />
    </SearchProvider>,
    routes(extra),
    path
  )
  await userEvent.keyboard('{Control>}k{/Control}')
  await expect.element(rendered.screen.getByRole('dialog')).toBeInTheDocument()
  return rendered
}

describe('command palette open and close', () => {
  it('toggles with Ctrl K, shows favourites when empty and clears the query on close', async () => {
    const { screen } = await openPalette()
    await expect
      .element(screen.getByRole('option', { name: /Stonehold/ }))
      .toBeInTheDocument()
    const input = screen.getByPlaceholder(
      'Search the world, a screen or an action'
    )
    await input.fill('zzz')
    await expect
      .element(screen.getByText('Nothing matches “zzz”.'))
      .toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    await expect.element(screen.getByRole('dialog')).not.toBeInTheDocument()
    await userEvent.keyboard('{Control>}k{/Control}')
    await expect
      .element(
        screen.getByPlaceholder('Search the world, a screen or an action')
      )
      .toHaveValue('')
  })

  it('opens the favourite record in a drawer', async () => {
    const { screen, router } = await openPalette()
    await screen.getByRole('option', { name: /Stonehold/ }).click()
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('entity:3')
    await expect.element(screen.getByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('command palette global search', () => {
  const hits = [
    {
      category: 'son',
      id: 7,
      title: 'Ithren',
      subtitle: 'Mythic son',
      snippet: null,
    },
    { category: 'word', id: 2, title: 'Vael', subtitle: 'moon', snippet: null },
    {
      category: 'chronicle',
      id: 9,
      title: 'The flood',
      subtitle: null,
      snippet: 'Waters rose',
      epoch: 4,
    },
    {
      category: 'council',
      id: 1,
      title: 'On the war',
      subtitle: null,
      snippet: null,
    },
    {
      category: 'map_note',
      id: 5,
      title: 'Camp here',
      subtitle: null,
      snippet: null,
    },
    {
      category: 'message',
      id: 6,
      title: 'A prayer',
      subtitle: null,
      snippet: null,
    },
    { category: 'star', id: 8, title: 'Sol', subtitle: null, snippet: null },
    {
      category: 'world',
      id: 1,
      title: 'Aerona',
      subtitle: null,
      snippet: null,
    },
    {
      category: 'foreign_god',
      id: 4,
      title: 'Old Nyx',
      subtitle: null,
      snippet: null,
    },
    {
      category: 'note',
      id: 11,
      title: 'My note',
      subtitle: null,
      snippet: null,
    },
  ]

  async function searchFor(term = 'it') {
    const searched = await openPalette({
      'GET /api/search': (request: MockRequest) =>
        request.query.get('q') === term ? hits : [],
    })
    await searched.screen
      .getByPlaceholder('Search the world, a screen or an action')
      .fill(term)
    await expect
      .element(searched.screen.getByText('In the world'))
      .toBeInTheDocument()
    return searched
  }

  it('waits for two letters before searching', async () => {
    const { screen, server } = await openPalette()
    await screen
      .getByPlaceholder('Search the world, a screen or an action')
      .fill('i')
    await expect
      .element(screen.getByText('In the world'))
      .not.toBeInTheDocument()
    expect(server.callsTo('GET /api/search')).toHaveLength(0)
  })

  it('lists hits with type label, subtitle or snippet and hides favourites while searching', async () => {
    const { screen } = await searchFor()
    await expect
      .element(screen.getByRole('option', { name: /Ithren.*Mythic son.*Son/ }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('option', { name: /The flood.*Waters rose/ }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Favourites')).not.toBeInTheDocument()
  })

  it('routes a son hit to the son drawer', async () => {
    const { screen, router } = await searchFor()
    await screen.getByRole('option', { name: /Ithren/ }).click()
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('son:7')
  })

  it('routes world, foreign god and note hits to drawers', async () => {
    const world = await searchFor()
    await world.screen.getByRole('option', { name: /Aerona/ }).click()
    await expect
      .poll(
        () => (world.router.state.location.search as { drawer?: string }).drawer
      )
      .toBe('world:1')
  })

  it('routes a foreign god hit to its drawer', async () => {
    const { screen, router } = await searchFor()
    await screen.getByRole('option', { name: /Old Nyx/ }).click()
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('foreign-god:4')
  })

  it('routes a note hit to the record drawer', async () => {
    const { screen, router } = await searchFor()
    await screen.getByRole('option', { name: /My note/ }).click()
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('entity:11')
  })
})

describe('command palette navigation by hit category', () => {
  const cases: [string, string, string][] = [
    ['word', 'Vael', '/languages'],
    ['chronicle', 'The flood', '/chronicle'],
    ['epoch', 'Epoch four', '/chronicle'],
    ['council', 'On the war', '/council'],
    ['map_note', 'Camp here', '/map'],
    ['message', 'A prayer', '/prayers'],
  ]
  for (const [category, title, path] of cases)
    it(`sends a ${category} hit to ${path}`, async () => {
      const { screen, router } = await openPalette({
        'GET /api/search': [
          { category, id: 1, title, subtitle: null, snippet: null },
        ],
      })
      await screen
        .getByPlaceholder('Search the world, a screen or an action')
        .fill('zz')
      await screen.getByRole('option', { name: new RegExp(title) }).click()
      await expect.poll(() => router.state.location.pathname).toBe(path)
    })
})

it('sends a star hit to its wiki drawer', async () => {
  const { screen, router } = await openPalette({
    'GET /api/search': [
      { category: 'star', id: 1, title: 'Sol', subtitle: null, snippet: null },
    ],
  })
  await screen
    .getByPlaceholder('Search the world, a screen or an action')
    .fill('zz')
  await screen.getByRole('option', { name: /Sol/ }).click()
  await expect
    .poll(() => (router.state.location.search as { drawer?: string }).drawer)
    .toBe('star:1')
})

describe('command palette keyboard', () => {
  it('moves the highlight with the arrows, opens with Enter and closes with Escape', async () => {
    const { screen, router } = await openPalette({
      'GET /api/search': [
        {
          category: 'son',
          id: 7,
          title: 'Zorvak',
          subtitle: null,
          snippet: null,
        },
        {
          category: 'son',
          id: 8,
          title: 'Zorvik',
          subtitle: null,
          snippet: null,
        },
      ],
    })
    await screen
      .getByPlaceholder('Search the world, a screen or an action')
      .fill('zorv')
    const selected = () =>
      document.querySelector('[cmdk-item][data-selected="true"]')
        ?.textContent ?? ''
    await expect.poll(selected).toContain('Zorvak')
    await userEvent.keyboard('{ArrowDown}')
    await expect.poll(selected).toContain('Zorvik')
    await userEvent.keyboard('{ArrowUp}')
    await expect.poll(selected).toContain('Zorvak')
    await userEvent.keyboard('{ArrowDown}')
    await userEvent.keyboard('{Enter}')
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('son:8')
  })
})

describe('command palette actions', () => {
  it('runs the epoch from the palette and toasts the result', async () => {
    const { screen, server } = await openPalette({
      'POST /api/epochs/current/complete': { job_id: 'j1' },
    })
    await screen.getByRole('option', { name: 'Complete the epoch' }).click()
    await expect
      .element(screen.getByText('The epoch begins'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/epochs/current/complete')).toHaveLength(1)
    await expect.element(screen.getByRole('dialog')).not.toBeInTheDocument()
  })

  it('reports an error when the epoch cannot run', async () => {
    const { screen } = await openPalette({
      'POST /api/epochs/current/complete': failure(
        409,
        'An epoch is already running.'
      ),
    })
    await screen.getByRole('option', { name: 'Complete the epoch' }).click()
    await expect
      .element(screen.getByText('An epoch is already running.'))
      .toBeInTheDocument()
  })

  it('takes a backup, marks notifications read and opens the live feed', async () => {
    const { screen, server } = await openPalette({
      'POST /api/backups': { file: 'b.db', size: 1, modified: 'x', label: '' },
      'POST /api/notifications/read': { changed: 3 },
    })
    await screen.getByRole('option', { name: 'Take a backup now' }).click()
    await expect.element(screen.getByText('Backup taken')).toBeInTheDocument()
    expect(server.callsTo('POST /api/backups')).toHaveLength(1)
    await userEvent.keyboard('{Control>}k{/Control}')
    await screen
      .getByRole('option', { name: 'Mark all notifications read' })
      .click()
    await expect
      .element(screen.getByText('Every notification is read'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/notifications/read')[0].body).toEqual({
      every: true,
      unread: false,
    })
    await userEvent.keyboard('{Control>}k{/Control}')
    await screen.getByRole('option', { name: 'Open the live feed' }).click()
    expect(useFeedPreferences.getState().open).toBe(true)
  })

  it('lists catalogue actions with their cost and runs one through its form', async () => {
    const { screen, server } = await openPalette({
      'POST /api/sons/7/bless-essence': {
        action: 'bless_essence',
        message: 'Ithren is blessed',
        ledger_entry_id: 21,
      },
    })
    await screen
      .getByRole('option', { name: /Bless with essence.*20 essence/ })
      .click()
    await expect
      .element(screen.getByRole('heading', { name: 'Bless with essence' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Written to the ledger; you can undo it.'))
      .toBeInTheDocument()
    await screen.getByLabelText('Son id *').fill('7')
    await screen.getByLabelText('Amount *').fill('15')
    await screen.getByRole('button', { name: 'Run' }).click()
    await expect
      .element(screen.getByText('Ithren is blessed'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Undo' }))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/{id}/bless-essence')[0].body).toEqual(
      { amount: 15 }
    )
  })

  it('requires the typed confirmation word before a destructive action can run', async () => {
    const { screen, server } = await openPalette({
      'POST /api/sons/7/kill': {
        action: 'kill_son',
        message: 'Ithren is dead',
      },
    })
    await screen.getByRole('option', { name: /Kill a son/ }).click()
    const run = screen.getByRole('button', { name: 'Run' })
    await expect
      .element(run)
      .toHaveAttribute('aria-description', 'Type KILL first')
    await screen.getByLabelText('Son id *').fill('7')
    await userEvent.type(screen.getByLabelText('Type KILL to confirm'), 'KIL')
    await expect.element(run).toHaveAttribute('aria-disabled', 'true')
    await userEvent.type(screen.getByLabelText('Type KILL to confirm'), 'L')
    await run.click()
    await expect.element(screen.getByText('Ithren is dead')).toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/7/kill')[0].body).toEqual({
      confirm: 'KILL',
    })
  })

  it('shows the server error inside the action form', async () => {
    const { screen } = await openPalette({
      'POST /api/sons/7/bless-essence': failure(400, 'Not enough essence.'),
    })
    await screen.getByRole('option', { name: /Bless with essence/ }).click()
    await screen.getByLabelText('Son id *').fill('7')
    await screen.getByLabelText('Amount *').fill('15')
    await screen.getByRole('button', { name: 'Run' }).click()
    await expect
      .element(screen.getByRole('alert'))
      .toHaveTextContent('Not enough essence.')
  })
})

describe('command palette screens and interface', () => {
  it('jumps to a screen', async () => {
    const { screen, router } = await openPalette()
    await screen
      .getByRole('option', { name: /^Chronicle/ })
      .first()
      .click()
    await expect.poll(() => router.state.location.pathname).toBe('/chronicle')
  })

  it('opens help in a drawer', async () => {
    const { screen, router } = await openPalette()
    await screen.getByRole('option', { name: /Help/ }).click()
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('help')
  })

  it('switches the theme', async () => {
    const { screen } = await openPalette()
    await screen.getByRole('option', { name: 'Light theme' }).click()
    await expect
      .poll(() => document.documentElement.classList.contains('light'))
      .toBe(true)
  })
})
