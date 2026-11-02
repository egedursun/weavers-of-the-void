import { serverEvent, worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { CompleteEpochButton } from './CompleteEpochButton'
import { EpochProgress } from './EpochProgress'
import { StopEpochButton } from './StopEpochButton'
import { useEpochRun } from './runStore'
import { remainingFrom } from './useEpochTiming'

const ESTIMATE = {
  samples: 5,
  average_epoch_seconds: 120,
  running: false,
  overrun: false,
}

beforeEach(() => useEpochRun.getState().reset())
afterEach(() => useEpochRun.getState().reset())

describe('complete epoch button', () => {
  it('shows the waiting son count and describes scope, estimate and the stop note', async () => {
    const { screen } = await renderScreen(<CompleteEpochButton />, {
      'GET /api/state': worldState({ pending_son_ids: [1, 2, 3] }),
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    const button = screen.getByRole('button', { name: /Complete the epoch/ })
    await expect.element(button).toBeEnabled()
    await expect
      .element(screen.getByText('3', { exact: true }))
      .toBeInTheDocument()
    const description =
      (await button.element()).getAttribute('aria-description') ?? ''
    expect(description).toContain('3 sons are waiting to act.')
    expect(description).toContain(
      'Completing runs 3 son turns, 4 mortal agents'
    )
    expect(description).toContain('Estimated time 2 min')
    expect(description).toContain('Stop halts it at a safe point')
  })

  it('says every son acted and that nothing was measured yet', async () => {
    const { screen } = await renderScreen(<CompleteEpochButton />, {
      'GET /api/state': worldState(),
      'GET /api/epochs/current/estimate': {
        ...ESTIMATE,
        samples: 0,
        average_epoch_seconds: null,
      },
    })
    const button = screen.getByRole('button', { name: /Complete the epoch/ })
    await expect.element(button).toBeEnabled()
    const description =
      (await button.element()).getAttribute('aria-description') ?? ''
    expect(description).toContain('Every son has acted this epoch.')
    expect(description).toContain('no time estimate')
  })

  it('runs the epoch on click and reports an error from the server', async () => {
    const { screen, server } = await renderScreen(<CompleteEpochButton />, {
      'GET /api/state': worldState(),
      'GET /api/epochs/current/estimate': ESTIMATE,
      'POST /api/epochs/current/complete': failure(
        409,
        'An epoch is already running.'
      ),
    })
    await screen.getByRole('button', { name: /Complete the epoch/ }).click()
    await expect
      .element(screen.getByText('An epoch is already running.'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/epochs/current/complete')).toHaveLength(1)
  })

  it('offers to resume a half epoch with its phase', async () => {
    const { screen } = await renderScreen(<CompleteEpochButton />, {
      'GET /api/state': worldState({ half_epoch: { epoch: 3, phase: 4 } }),
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    await expect
      .element(
        screen.getByRole('button', { name: 'Resume epoch 3 from phase 4' })
      )
      .toBeEnabled()
  })

  it('is replaced by a disabled running button while an epoch runs', async () => {
    const { screen } = await renderScreen(<CompleteEpochButton />, {
      'GET /api/state': worldState({ epoch_running: true }),
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    const button = screen.getByRole('button', { name: /Running/ })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
  })

  it('is disabled with a reason when no world exists', async () => {
    const { screen } = await renderScreen(<CompleteEpochButton />, {
      'GET /api/state': worldState({ world: null }),
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    await expect
      .element(screen.getByRole('button', { name: /Complete the epoch/ }))
      .toHaveAttribute(
        'aria-description',
        'Create a world before completing an epoch'
      )
  })
})

describe('stop epoch button', () => {
  it('is hidden when no epoch runs', async () => {
    const { screen } = await renderScreen(<StopEpochButton />, {
      'GET /api/state': worldState(),
    })
    await expect
      .element(screen.getByRole('button', { name: /Stop/ }))
      .not.toBeInTheDocument()
  })

  it('confirms, stops at a safe point and then shows the stopping state', async () => {
    const { screen, server } = await renderScreen(<StopEpochButton />, {
      'GET /api/state': worldState({ epoch_running: true }),
      'POST /api/epochs/current/stop': { message: 'Stopping after phase 2.' },
    })
    await screen.getByRole('button', { name: 'Stop' }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Stop the epoch?' }))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Stop at a safe point' }).click()
    await expect
      .element(screen.getByText('Stopping after phase 2.'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/epochs/current/stop')).toHaveLength(1)
    await expect
      .element(screen.getByRole('button', { name: /Stopping/ }))
      .toBeDisabled()
  })

  it('shows stopping as soon as the server reports a stop request', async () => {
    useEpochRun
      .getState()
      .apply(serverEvent('epoch.started', { epoch: 3, resuming: false }))
    useEpochRun.getState().apply(serverEvent('epoch.stop_requested', {}))
    const { screen } = await renderScreen(<StopEpochButton />, {
      'GET /api/state': worldState({ epoch_running: true }),
    })
    await expect
      .element(screen.getByRole('button', { name: /Stopping/ }))
      .toBeInTheDocument()
  })
})

describe('epoch progress strip', () => {
  it('shows nothing when idle', async () => {
    const { screen } = await renderScreen(<EpochProgress />, {
      'GET /api/state': worldState(),
      'GET /api/jobs': [],
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    await expect
      .element(screen.getByRole('progressbar'))
      .not.toBeInTheDocument()
  })

  it('mirrors the phase bar with percentage, phase name, ETA and son queue', async () => {
    const store = useEpochRun.getState()
    store.apply(
      serverEvent(
        'epoch.started',
        { epoch: 3, resuming: false },
        new Date().toISOString()
      )
    )
    store.apply(
      serverEvent('epoch.progress', {
        epoch: 3,
        no: 2,
        total: 5,
        name: 'Engine',
        elapsed_s: 3,
      })
    )
    store.apply(serverEvent('son.turn_queued', { no: 1, total: 3 }))
    const { screen } = await renderScreen(<EpochProgress />, {
      'GET /api/state': worldState({ epoch_running: true }),
      'GET /api/jobs': [],
      'GET /api/epochs/current/estimate': {
        ...ESTIMATE,
        running: true,
        elapsed_seconds: 10,
        remaining_seconds: 90,
      },
    })
    await expect
      .element(screen.getByText('Epoch 3', { exact: true }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('40%')).toBeInTheDocument()
    await expect
      .element(screen.getByText(/Phase 2\/5: Engine/))
      .toBeInTheDocument()
    await expect.element(screen.getByText(/about .+ left/)).toBeInTheDocument()
    await expect.element(screen.getByText(/son 1\/3/)).toBeInTheDocument()
  })

  it('announces the stop request in the subtitle', async () => {
    const store = useEpochRun.getState()
    store.apply(
      serverEvent(
        'epoch.started',
        { epoch: 3, resuming: false },
        new Date().toISOString()
      )
    )
    store.apply(serverEvent('epoch.stop_requested', {}))
    const { screen } = await renderScreen(<EpochProgress />, {
      'GET /api/state': worldState({ epoch_running: true }),
      'GET /api/jobs': [],
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    await expect
      .element(screen.getByText('Stopping at the next safe point'))
      .toBeInTheDocument()
  })

  it('shows an indeterminate job bar when no epoch runs but a job does', async () => {
    const { screen } = await renderScreen(<EpochProgress />, {
      'GET /api/state': worldState(),
      'GET /api/jobs': [
        {
          id: 'j',
          kind: 'backup',
          status: 'queued',
          progress: 0,
          stage: 'Waiting',
          params: {},
          result: null,
          error: null,
          created_at: 'x',
          started_at: null,
          finished_at: null,
        },
      ],
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    await expect.element(screen.getByText('Waiting')).toBeInTheDocument()
  })
})

describe('remaining time estimate', () => {
  it('prefers a fresh server estimate and shrinks it with age', () => {
    expect(remainingFrom(90, 1000, 11_000, 120, 5)).toBe(80)
  })

  it('falls back to the average minus elapsed and never goes negative', () => {
    expect(remainingFrom(null, 0, 0, 120, 30)).toBe(90)
    expect(remainingFrom(null, 0, 0, 120, 500)).toBe(0)
    expect(remainingFrom(undefined, 0, 0, null, 30)).toBeNull()
  })
})
