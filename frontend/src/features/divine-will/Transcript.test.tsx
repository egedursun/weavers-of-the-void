import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { CycleList } from './Transcript'
import { willConfirmation, willCycle, willEvent } from './willFixtures'
import { useWill } from './willStore'

const ACTION = {
  id: 'raise_mountain',
  title: 'Raise a mountain',
  group: 'worlds',
  mode: 'ledgered',
  cost: '5 essence',
  confirmation: null,
  rows: [],
  path: '/api/actions/raise_mountain',
  method: 'POST',
  input_schema: { type: 'object', properties: {} },
}

const ROUTES = {
  'GET /api/actions': [ACTION],
  'GET /api/names': [
    { id: 12, name: 'Old Keep', kind: 'entity', type: 'structure' },
  ],
  'GET /api/state': {},
  'POST /api/ledger/{entry_id}/undo': {
    entry_id: 44,
    applied: [],
    conflicts: [],
  },
  'POST /api/divine-will/confirmations/{confirmation_id}': willConfirmation({
    status: 'approved',
  }),
}

function reset() {
  useWill.setState({ mode: 'command', live: {}, draft: '' })
}

beforeEach(reset)
afterEach(reset)

describe('Divine Will transcript', () => {
  it('shows thoughts, tool cards with cost and undo, and links the answer', async () => {
    const cycle = willCycle({
      final_text: 'The range stands above **Old Keep**: entity#12.',
      events: [
        willEvent('player', { text: 'Raise a mountain in the north' }),
        willEvent('thought', { text: 'The north has room.' }),
        willEvent(
          'tool_call',
          {
            call_id: 'c1',
            arguments: { action_id: 'raise_mountain', input: { region_id: 4 } },
          },
          'perform_action'
        ),
        willEvent(
          'tool_result',
          {
            call_id: 'c1',
            text: 'Done.',
            is_error: false,
            outcome: 'A range rises in the north.',
            details: {
              action_id: 'raise_mountain',
              ledger_entry_id: 44,
              essence: 5,
            },
          },
          'perform_action'
        ),
        willEvent('text', {
          text: 'The range stands above **Old Keep**: entity#12.',
        }),
      ],
    })
    const { screen, server } = await renderScreen(
      <CycleList cycles={[cycle]} boundary={1} />,
      ROUTES
    )
    await expect
      .element(screen.getByText('Raise a mountain in the north'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'A thought' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The north has room.'))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: 'A thought' }).click()
    await expect
      .element(screen.getByText('The north has room.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Raise a mountain', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('A range rises in the north.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('5', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Old Keep' }))
      .toBeInTheDocument()
    expect(screen.getByText('The range stands above').elements()).toHaveLength(
      1
    )
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/ledger/{entry_id}/undo'))
      .toHaveLength(1)
  })

  it('lets the player copy their words and the answer', async () => {
    const cycle = willCycle({
      player_text: 'Raise a mountain in the north',
      final_text: 'The range stands.',
    })
    const { screen } = await renderScreen(
      <CycleList cycles={[cycle]} boundary={1} />,
      ROUTES
    )
    await expect
      .element(screen.getByRole('button', { name: 'Copy your words' }))
      .toBeEnabled()
    await expect
      .element(screen.getByRole('button', { name: 'Copy the answer' }))
      .toBeEnabled()
  })

  it('streams the text and the tools of a running exchange', async () => {
    useWill.setState({
      live: {
        2: {
          text: 'The range ri',
          tools: [
            {
              callId: 'c9',
              tool: 'search_lore',
              phase: 'preparing',
              chars: 0,
              input: null,
              error: false,
            },
          ],
        },
      },
    })
    const cycle = willCycle({
      id: 2,
      status: 'running',
      final_text: '',
      finished_at: null,
    })
    const { screen } = await renderScreen(
      <CycleList cycles={[cycle]} boundary={1} />,
      ROUTES
    )
    await expect.element(screen.getByText('The range ri')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Searched the lore'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Choosing its words'))
      .toBeInTheDocument()
  })

  it('asks for approval with the rehearsal and sends the approval', async () => {
    const confirmation = willConfirmation()
    const cycle = willCycle({
      status: 'awaiting_confirmation',
      finished_at: null,
      confirmations: [confirmation],
      events: [
        willEvent(
          'confirmation_request',
          { confirmation_id: 7 },
          'smite_entity'
        ),
      ],
    })
    const { screen, server } = await renderScreen(
      <CycleList cycles={[cycle]} boundary={1} />,
      ROUTES
    )
    await expect
      .element(
        screen.getByRole('group', { name: 'Approval for Smite a record' })
      )
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Your word is needed'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('What is lost')).toBeInTheDocument()
    await expect.element(screen.getByText('30 essence')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Approve' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('POST /api/divine-will/confirmations/{confirmation_id}')
          .map((call) => call.body)
      )
      .toEqual([{ decision: 'approve' }])
  })

  it('declines an act', async () => {
    const cycle = willCycle({
      status: 'awaiting_confirmation',
      confirmations: [willConfirmation()],
      events: [willEvent('confirmation_request', { confirmation_id: 7 })],
    })
    const { screen, server } = await renderScreen(
      <CycleList cycles={[cycle]} boundary={1} />,
      ROUTES
    )
    await screen.getByRole('button', { name: 'Decline' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('POST /api/divine-will/confirmations/{confirmation_id}')
          .map((call) => call.body)
      )
      .toEqual([{ decision: 'decline' }])
  })

  it('draws the memory boundary above the first remembered exchange', async () => {
    const cycles = [1, 2, 3].map((ordinal) =>
      willCycle({
        id: ordinal,
        ordinal,
        player_text: `Wish ${String(ordinal)}`,
        final_text: `Answer ${String(ordinal)}`,
      })
    )
    const { screen } = await renderScreen(
      <CycleList cycles={cycles} boundary={3} />,
      ROUTES
    )
    const line = screen.getByRole('separator', { name: 'Beyond memory' })
    await expect.element(line).toBeInTheDocument()
    await expect
      .element(
        screen.getByText(/no longer keeps the 2 exchanges above in mind/)
      )
      .toBeInTheDocument()
    const order = [
      ...document.querySelectorAll(
        '[data-domain="will-cycle"],[data-domain="will-memory-boundary"]'
      ),
    ].map((element) => element.getAttribute('data-domain'))
    expect(order).toEqual([
      'will-cycle',
      'will-cycle',
      'will-memory-boundary',
      'will-cycle',
    ])
    await expect
      .element(screen.getByRole('article', { name: 'Exchange 1' }))
      .not.toHaveAttribute('data-remembered')
    await expect
      .element(screen.getByRole('article', { name: 'Exchange 3' }))
      .toHaveAttribute('data-remembered', 'true')
  })

  it('offers a one-click switch when the Divine Will suggests another mode', async () => {
    const cycle = willCycle({
      events: [
        willEvent(
          'notice',
          {
            notice: 'suggest_mode',
            mode: 'plan',
            reason: 'This takes many steps.',
          },
          'suggest_mode'
        ),
        willEvent('notice', {
          notice: 'vision_unavailable',
          text: 'You attached an image it could not see.',
        }),
      ],
    })
    const { screen } = await renderScreen(
      <CycleList cycles={[cycle]} boundary={1} />,
      ROUTES
    )
    await expect
      .element(screen.getByText('This is better done in Plan'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The model could not see your image'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Switch to Plan' }).click()
    expect(useWill.getState().mode).toBe('plan')
  })
})
