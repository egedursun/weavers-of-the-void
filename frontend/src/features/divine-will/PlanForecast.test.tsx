import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { ForecastCard } from './ForecastCard'
import { PlanCard } from './PlanCard'
import { type WillPlan } from './types'
import { DONE_REPORT, willForecast, willPlan, willStep } from './willFixtures'

const ACTIONS = [
  {
    id: 'raise_mountain',
    title: 'Raise a mountain',
    group: 'worlds',
    mode: 'ledgered',
    cost: '5 essence',
    confirmation: null,
    rows: [],
    path: '/api/actions/raise_mountain',
    method: 'POST',
    input_schema: {
      type: 'object',
      required: ['region_id'],
      properties: { region_id: { type: 'integer', title: 'Region' } },
    },
  },
  {
    id: 'seed_forest',
    title: 'Seed a forest',
    group: 'worlds',
    mode: 'ledgered',
    cost: '3 essence',
    confirmation: null,
    rows: [],
    path: '/api/actions/seed_forest',
    method: 'POST',
    input_schema: { type: 'object', properties: {} },
  },
]

function planRoutes(plan: WillPlan) {
  return {
    'GET /api/actions': ACTIONS,
    'GET /api/names': [],
    'GET /api/divine-will/plans/{plan_id}': plan,
    'PUT /api/divine-will/plans/{plan_id}/steps': plan,
    'POST /api/divine-will/plans/{plan_id}/approve': plan,
    'POST /api/divine-will/plans/{plan_id}/execute': plan,
    'POST /api/divine-will/plans/{plan_id}/pause': plan,
    'POST /api/divine-will/plans/{plan_id}/resume': plan,
    'POST /api/divine-will/plans/{plan_id}/abandon': plan,
    'POST /api/divine-will/plans/{plan_id}/steps/{ordinal}/skip': plan,
    'POST /api/divine-will/plans/{plan_id}/steps/{ordinal}/undo': plan,
  }
}

describe('plan card', () => {
  it('names the records a step acts on instead of their numbers', async () => {
    const plan = willPlan({
      steps: [
        willStep({
          input: {
            entity_id: 18,
            stat: 'defense',
            value: 30,
            ledger_entry_id: 4,
          },
        }),
      ],
    })
    const { screen } = await renderScreen(<PlanCard planId={5} />, {
      ...planRoutes(plan),
      'GET /api/names': [
        { id: 18, name: 'Sohmar', kind: 'entity', type: 'settlement' },
      ],
    })
    await expect
      .element(
        screen.getByText(
          'entity: Sohmar · stat: defense · value: 30 · ledger entry id: 4'
        )
      )
      .toBeInTheDocument()
  })

  it('approves a draft and tells that nothing changes before it runs', async () => {
    const { screen, server } = await renderScreen(
      <PlanCard planId={5} />,
      planRoutes(willPlan())
    )
    await expect
      .element(screen.getByRole('group', { name: 'Plan: Shape the north' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('1. Raise the range'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Waits on 1')).toBeInTheDocument()
    await expect
      .element(
        screen.getByText(/Nothing in the world changes until you approve/)
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Approve' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/divine-will/plans/{plan_id}/approve')
      )
      .toHaveLength(1)
  })

  it('edits the steps as forms, keeps waits in order and saves them', async () => {
    const { screen, server } = await renderScreen(
      <PlanCard planId={5} />,
      planRoutes(willPlan())
    )
    await screen.getByRole('button', { name: 'Edit steps' }).click()
    await expect
      .element(screen.getByRole('spinbutton', { name: /Region/ }))
      .toHaveValue(4)
    await screen.getByRole('button', { name: 'Move step 2 up' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Save the steps' }))
      .toHaveAttribute(
        'aria-description',
        'Step 1 waits on a step that comes after it; move it below.'
      )
    await screen.getByRole('button', { name: 'Delete step 1' }).click()
    const region = screen.getByRole('spinbutton', { name: /Region/ })
    await region.clear()
    await expect
      .element(screen.getByText('Region is required.').first())
      .toBeInTheDocument()
    await region.click()
    await userEvent.keyboard('7')
    await screen.getByRole('button', { name: 'Save the steps' }).click()
    await expect
      .poll(() => server.callsTo('PUT /api/divine-will/plans/{plan_id}/steps'))
      .toHaveLength(1)
    expect(
      server.callsTo('PUT /api/divine-will/plans/{plan_id}/steps')[0].body
    ).toEqual({
      title: 'Shape the north',
      steps: [
        {
          title: 'Raise the range',
          action_id: 'raise_mountain',
          input: { region_id: 7 },
          depends_on: [],
          declared_impact: 'safe',
          estimated_essence: 5,
        },
      ],
    })
  })

  it('pauses a running plan', async () => {
    const plan = willPlan({
      status: 'running',
      steps: [willStep({ status: 'running' })],
    })
    const { screen, server } = await renderScreen(
      <PlanCard planId={5} />,
      planRoutes(plan)
    )
    await screen.getByRole('button', { name: 'Pause' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/divine-will/plans/{plan_id}/pause'))
      .toHaveLength(1)
  })

  it('shows a waiting step and resumes, skips and undoes steps', async () => {
    const plan = willPlan({
      status: 'paused',
      waiting_step: 2,
      steps: [
        willStep({ status: 'done', ledger_entry_id: 40 }),
        willStep({
          ordinal: 2,
          title: 'Seed the valleys',
          action_id: 'seed_forest',
          error: 'It would end a forest it did not declare.',
        }),
      ],
    })
    const { screen, server } = await renderScreen(
      <PlanCard planId={5} />,
      planRoutes(plan)
    )
    await expect
      .element(screen.getByText('Step 2 waits for your word'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Skip' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('POST /api/divine-will/plans/{plan_id}/steps/{ordinal}/skip')
          .map((call) => call.path)
      )
      .toEqual(['/api/divine-will/plans/5/steps/2/skip'])
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('POST /api/divine-will/plans/{plan_id}/steps/{ordinal}/undo')
          .map((call) => call.path)
      )
      .toEqual(['/api/divine-will/plans/5/steps/1/undo'])
    await screen.getByRole('button', { name: 'Resume' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/divine-will/plans/{plan_id}/resume')
      )
      .toHaveLength(1)
  })

  it('abandons only after a warning', async () => {
    const { screen, server } = await renderScreen(
      <PlanCard planId={5} />,
      planRoutes(willPlan({ status: 'approved' }))
    )
    await screen.getByRole('button', { name: 'Abandon' }).click()
    await expect
      .element(screen.getByRole('alertdialog', { name: 'Abandon this plan?' }))
      .toBeInTheDocument()
    expect(
      server.callsTo('POST /api/divine-will/plans/{plan_id}/abandon')
    ).toHaveLength(0)
    await screen.getByRole('button', { name: 'Abandon the plan' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/divine-will/plans/{plan_id}/abandon')
      )
      .toHaveLength(1)
  })
})

function forecastRoutes(forecast: ReturnType<typeof willForecast>) {
  return {
    'GET /api/actions': ACTIONS,
    'GET /api/names': [],
    'GET /api/divine-will/forecasts/{forecast_id}': forecast,
    'POST /api/divine-will/forecasts/{forecast_id}/cancel': {
      ...forecast,
      status: 'cancelled',
    },
  }
}

describe('forecast card', () => {
  it('shows the expected time before it starts and cancels', async () => {
    const { screen, server } = await renderScreen(
      <ForecastCard forecastId={9} />,
      forecastRoutes(willForecast())
    )
    await expect
      .element(screen.getByText('Expected to take about 1 min 10 s'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Raise a mountain'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Cancel the forecast' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/divine-will/forecasts/{forecast_id}/cancel')
      )
      .toHaveLength(1)
  })

  it('counts down epoch by epoch while it runs', async () => {
    const running = willForecast({
      status: 'running',
      epochs_done: 1,
      started_at: new Date().toISOString(),
    })
    const { screen } = await renderScreen(
      <ForecastCard forecastId={9} />,
      forecastRoutes(running)
    )
    await expect.element(screen.getByText(/Epoch 2 of 2/)).toBeInTheDocument()
    await expect.element(screen.getByText(/left$/)).toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('progressbar', { name: /Forecast progress, 50%/ })
      )
      .toBeInTheDocument()
  })

  it('compares both worlds when it is done', async () => {
    const done = willForecast({
      status: 'done',
      epochs_done: 2,
      report: DONE_REPORT,
      finished_at: '2026-11-20T10:02:00Z',
    })
    const { screen } = await renderScreen(
      <ForecastCard forecastId={9} />,
      forecastRoutes(done)
    )
    await expect
      .element(screen.getByText('From epoch 3 to epoch 5', { exact: false }))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('img', {
          name: 'Change of each measure in both worlds',
        })
      )
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('img', { name: 'Deaths by cause in both worlds' })
      )
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The range sheltered the valleys.'))
      .toBeInTheDocument()
    await screen.getByRole('tab', { name: 'Without your hand' }).click()
    await expect
      .element(screen.getByText('The harvest failed in the east.'))
      .toBeInTheDocument()
  })

  it('tells why a forecast failed', async () => {
    const failed = willForecast({
      status: 'failed',
      error: 'The copy could not be made.',
    })
    const { screen } = await renderScreen(
      <ForecastCard forecastId={9} />,
      forecastRoutes(failed)
    )
    await expect
      .element(screen.getByRole('alert'))
      .toHaveTextContent('The copy could not be made.')
  })
})
