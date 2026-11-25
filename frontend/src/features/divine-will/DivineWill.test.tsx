import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { page } from 'vitest/browser'
import { SidebarProvider } from '@/components/ui/sidebar'
import {
  PANEL_DEFAULT_REM,
  useWillDock,
} from '@/components/layout/divine-will/dockStore'
import { DivineWill } from './DivineWill'
import { willActive, willCycle } from './willFixtures'
import { useWill } from './willStore'

const DONE = willCycle({ final_text: 'The range stands.' })
const RUNNING = willCycle({
  id: 3,
  ordinal: 2,
  status: 'running',
  final_text: '',
  finished_at: null,
})

const PAST = {
  id: 9,
  title: 'The first session',
  opened_epoch: 1,
  opened_at: '2026-11-01T10:00:00Z',
  closed_epoch: 2,
  closed_at: '2026-11-02T10:00:00Z',
  cycle_count: 1,
}

function routes(cycles = [DONE]) {
  return {
    'GET /api/divine-will/session': willActive(cycles),
    'GET /api/divine-will/modes': { modes: [] },
    'GET /api/divine-will/index': {
      status: 'ready',
      note: '',
      semantic: true,
      passages: 10,
      embedded: 10,
      pending: 0,
      sources: [],
      built_at: null,
      model: 'multilingual-e5-small',
    },
    'GET /api/divine-will/cycles/{cycle_id}': RUNNING,
    'POST /api/divine-will/session/reset': willActive([]),
    'GET /api/divine-will/sessions': { sessions: [PAST] },
    'GET /api/divine-will/sessions/{session_id}': {
      session: PAST,
      cycles: [
        willCycle({
          id: 20,
          player_text: 'An old wish',
          final_text: 'An old answer',
        }),
      ],
      memory_boundary: 2,
      has_earlier: false,
    },
    'GET /api/names': [],
    'GET /api/state': {},
  }
}

function reset() {
  useWillDock.setState({ open: false, width: PANEL_DEFAULT_REM, view: 'chat' })
  useWill.setState({
    mode: 'command',
    draft: '',
    live: {},
    unread: 0,
    seed: null,
  })
}

beforeEach(async () => {
  reset()
  await page.viewport(1440, 900)
})
afterEach(reset)

function shell() {
  return (
    <SidebarProvider>
      <DivineWill />
    </SidebarProvider>
  )
}

describe('Divine Will panel', () => {
  it('shows the memory meter and resets the session after a clear warning', async () => {
    useWillDock.setState({ open: true })
    const { screen, server } = await renderScreen(shell(), routes())
    await expect
      .element(screen.getByText('The range stands.'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('1 / 10')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Begin a new session' }).click()
    await expect
      .element(
        screen.getByRole('alertdialog', { name: 'Begin a new session?' })
      )
      .toBeInTheDocument()
    await expect
      .element(screen.getByText(/Nothing is lost/))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByText(/stays in Past sessions, the lore book and the Codex/)
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Begin anew' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/divine-will/session/reset'))
      .toHaveLength(1)
  })

  it('cannot reset while the Divine Will is at work', async () => {
    useWillDock.setState({ open: true })
    const { screen } = await renderScreen(shell(), routes([DONE, RUNNING]))
    await expect
      .element(screen.getByRole('button', { name: 'Begin a new session' }))
      .toHaveAttribute(
        'aria-description',
        'Wait until the Divine Will has answered, or stop it first.'
      )
  })

  it('streams the words of its own exchange only', async () => {
    useWillDock.setState({ open: true })
    const { screen, emit } = await renderScreen(
      shell(),
      routes([DONE, RUNNING])
    )
    await expect
      .element(screen.getByRole('button', { name: 'Stop' }))
      .toBeInTheDocument()
    emit('agent.stream', {
      channel: 'divine_will:3',
      text: 'Lifting the stone',
      chars: 17,
    })
    emit('agent.stream', {
      channel: 'divine_will:99',
      text: 'Not this one',
      chars: 12,
    })
    emit('agent.stream', {
      actor_kind: 'son',
      actor_id: 2,
      text: 'A son speaks',
      chars: 12,
    })
    await expect
      .element(screen.getByText('Lifting the stone'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Not this one'))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByText('A son speaks'))
      .not.toBeInTheDocument()
  })

  it('counts answers that arrive while closed and clears them on open', async () => {
    const { screen, emit } = await renderScreen(shell(), routes())
    await expect
      .element(screen.getByRole('button', { name: 'Open the Divine Will' }))
      .toBeInTheDocument()
    emit('divine_will.cycle_finished', {
      cycle_id: 1,
      session_id: 1,
      ordinal: 1,
      mode: 'command',
      status: 'done',
    })
    const orb = screen.getByRole('button', {
      name: 'Open the Divine Will, one new answer',
    })
    await expect.element(orb).toBeInTheDocument()
    await orb.click()
    await expect
      .element(screen.getByRole('complementary', { name: 'The Divine Will' }))
      .toBeInTheDocument()
    expect(useWill.getState().unread).toBe(0)
  })

  it('opens a past session from the record', async () => {
    useWillDock.setState({ open: true })
    const { screen } = await renderScreen(shell(), routes())
    await screen.getByRole('tab', { name: 'Past sessions' }).click()
    await screen.getByRole('button', { name: /The first session/ }).click()
    await expect.element(screen.getByText('An old answer')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('separator', { name: 'Beyond memory' }))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Every past session' }).click()
    await expect
      .element(screen.getByText('Closed sessions'))
      .toBeInTheDocument()
  })
})
