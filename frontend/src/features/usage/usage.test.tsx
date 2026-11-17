import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { page } from 'vitest/browser'
import { UsageScreen } from './UsageScreen'

const share = (name: string, input: number, output: number, errors = 0) => ({
  name,
  calls: 4,
  input_tokens: input,
  output_tokens: output,
  errors,
  milliseconds: 8000,
})

const REPORT = {
  tokenizer: 'tiktoken o200k_base',
  totals: {
    calls: 12,
    input_tokens: 90_000,
    output_tokens: 10_000,
    turns: 30,
    errors: 1,
    partial: 2,
    retried: 1,
    milliseconds: 64_000,
    largest_call: 24_000,
    median_call: 6000,
    p95_call: 20_000,
    epochs: 3,
    first_at: '2026-11-15T10:00:00Z',
    last_at: '2026-11-17T10:00:00Z',
  },
  timeline: [
    {
      epoch: 1,
      start: null,
      calls: 4,
      input_tokens: 30_000,
      output_tokens: 3000,
      errors: 0,
    },
    {
      epoch: 2,
      start: null,
      calls: 8,
      input_tokens: 60_000,
      output_tokens: 7000,
      errors: 1,
    },
  ],
  models: [share('opus', 70_000, 8000), share('haiku', 20_000, 2000)],
  roles: [share('Son turn', 60_000, 6000), share('Fate', 30_000, 4000)],
  steps: [share('Son turns', 60_000, 6000, 1), share('Fate', 30_000, 4000)],
  kinds: [
    { kind: 'agent', calls: 8, input_tokens: 60_000, output_tokens: 6000 },
    { kind: 'structured', calls: 4, input_tokens: 30_000, output_tokens: 4000 },
  ],
  statuses: [
    { status: 'ok', calls: 9, input_tokens: 80_000, output_tokens: 9000 },
    { status: 'error', calls: 1, input_tokens: 2000, output_tokens: 0 },
    { status: 'partial', calls: 2, input_tokens: 8000, output_tokens: 1000 },
  ],
  facets: {
    calls: 40,
    tokens: 2_500_000,
    models: ['haiku', 'opus'],
    roles: ['Fate', 'Son turn'],
    steps: ['Fate', 'Son turns'],
    epoch_low: 1,
    epoch_high: 3,
  },
}

const CALL = {
  id: 7,
  epoch: 2,
  job: 'Son turn: Ithren',
  role: 'Son turn',
  model: 'opus',
  kind: 'agent',
  status: 'error',
  duration_ms: 4000,
  attempts: 2,
  turns: 5,
  input_tokens: 1200,
  output_tokens: 300,
  actions: 3,
  error: 'refused the tool',
  created_at: '2026-11-17T10:00:00Z',
}

const RULES = [
  {
    namespace: 'metrics',
    key: 'keep_epochs',
    value: 100,
    default: 100,
    minimum: 1,
    maximum: 10000,
    group: 'records',
    label: 'Keep',
    integer: true,
  },
]

function routes(report: unknown = REPORT, total = 60) {
  return {
    'GET /api/usage/summary': report,
    'GET /api/usage/calls': {
      items: [CALL],
      total,
      offset: 0,
      limit: 50,
    },
    'GET /api/rules': RULES,
  }
}

describe('usage page', () => {
  afterEach(async () => {
    await page.viewport(1280, 900)
  })

  it('shows token totals, charts, the breakdown and the call log without prices', async () => {
    const { screen } = await renderScreen(<UsageScreen />, routes())
    await expect
      .element(screen.getByText('Total tokens', { exact: true }).first())
      .toBeVisible()
    await expect.element(screen.getByText('12 of 40 calls match')).toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Tokens in and out per epoch' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Share of tokens by model' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('cell', { name: 'Son turn: Ithren' }))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Calls of the last 100 epochs are kept.', {
          exact: false,
        })
      )
      .toBeVisible()
    expect(document.body.textContent).not.toContain('$')
  })

  it('ranks the usage, names the tokenizer and compares the latest epoch', async () => {
    const { screen } = await renderScreen(<UsageScreen />, routes())
    await expect
      .element(screen.getByText('Rare', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('7.5M more tokens to Epic at 10M.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Counted with tiktoken o200k_base'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Latest · Epoch 2', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('103% more than Epoch 1'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Heaviest' }).first())
      .toBeVisible()
  })

  it('fits a phone screen without sideways scrolling', async () => {
    await page.viewport(390, 900)
    const { screen } = await renderScreen(<UsageScreen />, routes())
    await expect
      .element(screen.getByRole('cell', { name: 'Son turn: Ithren' }))
      .toBeVisible()
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(
      window.innerWidth
    )
  })

  it('filters by a picked model and sends the filter to both reads', async () => {
    const { screen, server, router } = await renderScreen(
      <UsageScreen />,
      routes()
    )
    await screen.getByRole('button', { name: 'Filter to model opus' }).click()
    await expect
      .element(
        screen.getByRole('button', { name: 'Remove filter: Model opus' })
      )
      .toBeVisible()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/usage/calls')
          .some((call) => call.query.getAll('model').includes('opus'))
      )
      .toBe(true)
    expect(
      server
        .callsTo('GET /api/usage/summary')
        .some((call) => call.query.getAll('model').includes('opus'))
    ).toBe(true)
    expect(router.state.location.search).toMatchObject({ model: ['opus'] })
    await expect
      .element(screen.getByRole('link', { name: 'Export CSV' }))
      .toHaveAttribute(
        'href',
        '/api/usage/calls/export?model=opus&sort=time&descending=true'
      )
    await screen
      .getByRole('button', { name: 'Remove filter: Model opus' })
      .click()
    await expect
      .element(screen.getByRole('button', { name: 'Clear filters' }))
      .toBeDisabled()
  })

  it('sorts the log on the server, pages it and opens a call', async () => {
    const { screen, server } = await renderScreen(<UsageScreen />, routes())
    await screen.getByRole('button', { name: 'Sort by total tokens' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/usage/calls')
          .some(
            (call) =>
              call.query.get('sort') === 'total_tokens' &&
              call.query.get('descending') === 'true'
          )
      )
      .toBe(true)
    await screen.getByRole('button', { name: 'Next' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/usage/calls')
          .some((call) => call.query.get('offset') === '50')
      )
      .toBe(true)
    await screen.getByRole('button', { name: 'Show details of call 7' }).click()
    await expect.element(screen.getByText('refused the tool')).toBeVisible()
  })

  it('debounces the search into the request', async () => {
    const { screen, server } = await renderScreen(<UsageScreen />, routes())
    await screen
      .getByRole('textbox', {
        name: 'Search calls by step, role, model or error',
      })
      .fill('refused')
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/usage/summary')
          .some((call) => call.query.get('search') === 'refused')
      )
      .toBe(true)
  })

  it('tells an empty server apart from a filter that matches nothing', async () => {
    const empty = {
      ...REPORT,
      totals: { ...REPORT.totals, calls: 0, first_at: null, last_at: null },
      timeline: [],
      models: [],
      roles: [],
      steps: [],
      kinds: [],
      statuses: [],
      facets: { ...REPORT.facets, calls: 0, models: [], roles: [], steps: [] },
    }
    const { screen } = await renderScreen(<UsageScreen />, routes(empty, 0))
    await expect.element(screen.getByText('No tokens spent yet')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Clear filters' }))
      .toBeDisabled()
  })
})
