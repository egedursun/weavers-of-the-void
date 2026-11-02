import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { ModelMetrics } from './ModelMetrics'
import { stepAverageMs } from './api'

const METRICS = {
  totals: {
    calls: 1500,
    milliseconds: 90000,
    cost: 12.5,
    input_tokens: 2_000_000,
    output_tokens: 300_000,
  },
  epochs: [
    {
      epoch: 2,
      calls: 700,
      milliseconds: 40000,
      input_tokens: 900_000,
      output_tokens: 100_000,
      cost: 5,
      errors: 2,
      retried: 1,
      slow: 3,
    },
    {
      epoch: 3,
      calls: 800,
      milliseconds: 50000,
      input_tokens: 1_100_000,
      output_tokens: 200_000,
      cost: 7.5,
      errors: 0,
      retried: 0,
      slow: 0,
    },
  ],
  models: [
    {
      model: 'haiku',
      calls: 1500,
      milliseconds: 90000,
      average_ms: 60,
      input_tokens: 1,
      output_tokens: 1,
      cost: 1,
    },
  ],
  steps: [
    {
      step: 'fate.judge',
      calls: 10,
      average_ms: 1200,
      longest_ms: 4000,
      cost: 1,
      errors: 1,
    },
  ],
  slowest: [
    {
      id: 1,
      epoch: 3,
      job: 'son turn',
      role: 'Ithren',
      model: 'haiku',
      kind: 'agent',
      status: 'ok',
      duration_ms: 45000,
      attempts: 1,
      turns: 3,
      input_tokens: 1,
      output_tokens: 1,
      cost_usd: 0,
      error: null,
      created_at: 'x',
    },
  ],
  latest_errors: [
    {
      id: 2,
      epoch: null,
      job: 'genesis',
      role: null,
      model: 'haiku',
      kind: 'structured',
      status: 'error',
      duration_ms: 10,
      attempts: 2,
      turns: null,
      input_tokens: 0,
      output_tokens: 0,
      cost_usd: 0,
      error: 'Invalid JSON',
      created_at: 'x',
    },
  ],
  slow_threshold_ms: 30000,
}

function tileValue(label: string): string | null {
  const tile = [
    ...document.querySelectorAll<HTMLElement>('[data-domain="mini-stat"]'),
  ].find((item) => item.textContent?.endsWith(label))
  return tile?.querySelector('[title]')?.getAttribute('title') ?? null
}

const base = (metrics: unknown) => ({
  'GET /api/metrics/models': metrics,
  'GET /api/state': worldState(),
  'GET /api/epochs/current/estimate': {
    samples: 4,
    average_epoch_seconds: 90,
    running: false,
    overrun: false,
  },
})

describe('model metrics panel', () => {
  it('shows call, time, token and cost chips with the per-epoch table', async () => {
    const { screen } = await renderScreen(<ModelMetrics />, base(METRICS))
    await expect.poll(() => tileValue('Calls')).toBe('1.5K')
    await expect.poll(() => tileValue('Time spent')).toBe('1 min 30 s')
    await expect.poll(() => tileValue('Tokens in')).toBe('2M')
    await expect.poll(() => tileValue('Tokens out')).toBe('300K')
    await expect.poll(() => tileValue('API equivalent')).toBe('$12.5')
    await expect.poll(() => tileValue('Errors')).toBe('2')
    await expect
      .element(screen.getByRole('cell', { name: 'Epoch 2' }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('2 · 1 retried')).toBeInTheDocument()
    await expect
      .element(screen.getByText(/haiku · 1500 calls · average/))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Calls over 30 s count as slow.'))
      .toBeInTheDocument()
  })

  it('opens the by-step, slow and error folders', async () => {
    const { screen } = await renderScreen(<ModelMetrics />, base(METRICS))
    await screen.getByRole('button', { name: 'By step (1)' }).click()
    await expect
      .element(screen.getByRole('cell', { name: 'fate.judge' }))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Slow calls (1)' }).click()
    await expect
      .element(screen.getByText('son turn · Ithren'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Recent errors (1)' }).click()
    await expect.element(screen.getByText('Invalid JSON')).toBeInTheDocument()
    await expect.element(screen.getByText('Outside epochs')).toBeInTheDocument()
  })

  it('asks for a different epoch window', async () => {
    const { screen, server } = await renderScreen(
      <ModelMetrics />,
      base(METRICS)
    )
    await screen.getByRole('combobox', { name: 'Epoch window' }).click()
    await screen.getByRole('option', { name: 'Last 10 epochs' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/metrics/models')
          .some((call) => call.query.get('epochs') === '10')
      )
      .toBe(true)
  })

  it('has an empty state and the average epoch time', async () => {
    const { screen } = await renderScreen(
      <ModelMetrics />,
      base({ ...METRICS, totals: { ...METRICS.totals, calls: 0 } })
    )
    await expect
      .element(screen.getByText('No calls measured yet'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('An epoch takes')).toBeInTheDocument()
    await expect.poll(() => tileValue('An epoch takes')).toBe('1 min 30 s')
    await screen.getByText('An epoch takes').hover()
    await expect
      .element(screen.getByRole('tooltip'))
      .toHaveTextContent('Average of 4 epochs')
  })

  it('finds the average of the first step whose name contains a needle', () => {
    expect(stepAverageMs(METRICS as never, 'fate')).toBe(1200)
    expect(stepAverageMs(METRICS as never, 'deepen')).toBeNull()
    expect(stepAverageMs(undefined, 'fate')).toBeNull()
  })
})
