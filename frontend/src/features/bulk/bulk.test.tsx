import { worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { BulkDeepenPanel } from './BulkDeepenPanel'

const IDLE = {
  total: 0,
  done: 0,
  failed: 0,
  skipped: 0,
  running: false,
  stop_requested: false,
}

function routes(
  status: Record<string, unknown>,
  extra: Record<string, unknown> = {},
  state = {}
) {
  return {
    'GET /api/batch-deepen': {
      state: IDLE,
      log: [],
      waiting: 12,
      unnamed: 0,
      ...status,
    },
    'GET /api/state': worldState(state),
    'GET /api/metrics/models': {
      totals: { calls: 1 },
      epochs: [],
      models: [],
      steps: [
        {
          step: 'deepen',
          calls: 4,
          average_ms: 2000,
          longest_ms: 5000,
          cost: 0,
          errors: 0,
        },
      ],
      slowest: [],
      latest_errors: [],
      slow_threshold_ms: 30000,
    },
    ...extra,
  }
}

describe('bulk deepening panel', () => {
  it('estimates the time from the measured step average and asks before starting', async () => {
    const { screen, server } = await renderScreen(<BulkDeepenPanel />, {
      ...routes({}),
      'POST /api/batch-deepen/start': {},
    })
    await expect
      .element(screen.getByText('About 24 s for 12 records.'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Deepen 12 records' }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Deepen 12 records?' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText(/Each record is one model call.*About 24 s/))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/batch-deepen/start')).toHaveLength(0)
    await screen.getByRole('button', { name: 'Start deepening' }).click()
    await expect
      .element(screen.getByText('Bulk deepening started'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/batch-deepen/start')).toHaveLength(1)
  })

  it('has no estimate before anything was measured', async () => {
    const { screen } = await renderScreen(<BulkDeepenPanel />, {
      ...routes({}),
      'GET /api/metrics/models': {
        totals: { calls: 0 },
        epochs: [],
        models: [],
        steps: [],
        slowest: [],
        latest_errors: [],
        slow_threshold_ms: 30000,
      },
    })
    await expect
      .element(
        screen.getByText(
          'No deepening has been measured yet, so there is no time estimate.'
        )
      )
      .toBeInTheDocument()
  })

  it('is disabled with a reason when every record is already deepened', async () => {
    const done = await renderScreen(<BulkDeepenPanel />, routes({ waiting: 0 }))
    await expect
      .element(done.screen.getByRole('button', { name: 'Deepen 0 records' }))
      .toHaveAttribute('aria-description', 'Every record is deepened')
  })

  it('explains that deepening needs the model', async () => {
    const { screen } = await renderScreen(
      <BulkDeepenPanel />,
      routes({}, {}, { llm_enabled: false })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Deepen 12 records' }))
      .toHaveAttribute(
        'aria-description',
        'Deepening needs the language model, which is turned off'
      )
  })

  it('is read-only in a guest world', async () => {
    const { screen } = await renderScreen(
      <BulkDeepenPanel />,
      routes({}, {}, { read_only: true })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Deepen 12 records' }))
      .toHaveAttribute('aria-description', 'A guest world is read-only')
  })

  it('shows progress, the current records and a colour-coded log, and offers Stop', async () => {
    const { screen, server } = await renderScreen(<BulkDeepenPanel />, {
      ...routes({
        state: {
          running: true,
          stop_requested: false,
          total: 10,
          done: 3,
          failed: 1,
          skipped: 1,
          current: [{ name: 'Stonehold' }, { name: 'Old Nyx' }],
        },
        log: [
          {
            level: 'info',
            at: '2026-01-01T12:00:00Z',
            text: 'Stonehold deepened',
          },
          {
            level: 'error',
            at: '2026-01-01T12:00:01Z',
            text: 'Mistmoor failed',
          },
        ],
      }),
      'POST /api/batch-deepen/stop': {},
    })
    await expect.element(screen.getByText('Running')).toBeInTheDocument()
    await expect
      .element(
        screen.getByText(/of 10 processed · 3 done · 1 failed · 1 skipped/)
      )
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Now: Stonehold, Old Nyx'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('progressbar', { name: 'Bulk deepening progress' })
      )
      .toHaveAttribute('aria-valuenow', '50')
    await expect
      .element(screen.getByText('Stonehold deepened'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Mistmoor failed'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Stop' }).click()
    await expect
      .element(
        screen.getByText('It stops when the current record finishes').first()
      )
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/batch-deepen/stop')).toHaveLength(1)
  })

  it('shows Stopping and disables Stop once stop was requested', async () => {
    const { screen } = await renderScreen(
      <BulkDeepenPanel />,
      routes({
        state: { ...IDLE, running: true, stop_requested: true, total: 4 },
      })
    )
    await expect.element(screen.getByText('Stopping')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Stop' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('names the unnamed records on demand', async () => {
    const { screen, server } = await renderScreen(<BulkDeepenPanel />, {
      ...routes({ unnamed: 3 }),
      'POST /api/names/assign-missing': {},
    })
    await expect
      .element(
        screen.getByText(
          /also named at the end of each epoch, on startup and before bulk deepening/
        )
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Name 3 unnamed records' }).click()
    await expect
      .element(screen.getByText('The unnamed records are being named'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/names/assign-missing')).toHaveLength(1)
  })

  it('shows the empty state when nothing ran yet', async () => {
    const { screen } = await renderScreen(<BulkDeepenPanel />, routes({}))
    await expect
      .element(screen.getByText('No deepening yet'))
      .toBeInTheDocument()
  })

  it('reports a start failure from the server', async () => {
    const { screen } = await renderScreen(<BulkDeepenPanel />, {
      ...routes({}),
      'POST /api/batch-deepen/start': failure(409, 'Another job is running.'),
    })
    await screen.getByRole('button', { name: 'Deepen 12 records' }).click()
    await screen.getByRole('button', { name: 'Start deepening' }).click()
    await expect
      .element(screen.getByText('Another job is running.'))
      .toBeInTheDocument()
  })

  it('merges live bulk log events into the panel by refetching the status', async () => {
    let log: unknown[] = []
    const { screen, emit } = await renderScreen(<BulkDeepenPanel />, {
      ...routes({}),
      'GET /api/batch-deepen': () => ({
        state: IDLE,
        log,
        waiting: 12,
        unnamed: 0,
      }),
    })
    await expect
      .element(screen.getByText('No deepening yet'))
      .toBeInTheDocument()
    log = [
      {
        level: 'warning',
        at: '2026-01-01T12:00:00Z',
        text: 'Skipped Dustfall',
      },
    ]
    emit('batch_deepen.log', { text: 'Skipped Dustfall', level: 'warning' })
    await expect
      .element(screen.getByText('Skipped Dustfall'))
      .toBeInTheDocument()
  })
})
