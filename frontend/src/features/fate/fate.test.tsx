import { jobRecord, worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { FateControlsPage } from './FateControlsPage'
import { FateStatusCard } from './FateStatusCard'
import { type FateControls } from './api'
import {
  NO_DEBT_REASON,
  NO_FAILED_BIRTH_REASON,
  NO_LIMBO_REASON,
  NO_RUN_REASON,
  jobBlocker,
  urgentJobs,
} from './fateModel'

const ACTION = (id: string, cost: string) => ({
  id,
  title: id,
  group: 'fate',
  mode: 'job',
  cost,
  confirmation: null,
  rows: [],
  path: `/api/actions/${id}`,
  method: 'POST',
  input_schema: {},
})

const CATALOGUE = [
  ACTION('fate:retry', '30 essence'),
  ACTION('fate:rejudge_debt', '30 essence'),
  ACTION('fate:rejudge_limbo', '30 essence'),
  ACTION('fate:override_verdict', '15 essence'),
  ACTION('voices:retry', '20 essence'),
  ACTION('voices:edit_view', '5 essence'),
  ACTION('voices:delete_view', '5 essence'),
  ACTION('births:retry', '25 essence'),
]

function controls(overrides: Partial<FateControls> = {}): FateControls {
  return {
    last_epoch: 6,
    fate_debt_epoch: 5,
    limbo: [
      {
        entity_id: 42,
        name: 'The Glass Ossuary',
        born_epoch: 5,
        rationale: 'Too old to be sure.',
      },
    ],
    steps: [
      {
        step: 'fate_judgment',
        status: 'failed',
        error: 'The model did not answer.',
      },
      { step: 'voices', status: 'done', error: null },
    ],
    failed_births: 0,
    views: [
      {
        id: 9,
        people_entity_id: 44,
        historian: 'Ossa',
        text: 'We remember the salt.',
      },
    ],
    ...overrides,
  }
}

function routes(
  view: FateControls = controls(),
  state: Record<string, unknown> = {}
) {
  return {
    'GET /api/state': worldState({ creator: { essence: 100 }, ...state }),
    'GET /api/fate/controls': view,
    'GET /api/actions': CATALOGUE,
    'GET /api/names': [
      { kind: 'entity', id: 44, name: 'The Salt Harbours', type: 'people' },
    ],
    'GET /api/jobs': [],
  }
}

describe('fate model', () => {
  it('explains why a job cannot run', () => {
    expect(jobBlocker(controls({ last_epoch: null }), 'fate:retry')).toBe(
      NO_RUN_REASON
    )
    expect(
      jobBlocker(controls({ fate_debt_epoch: null }), 'fate:rejudge_debt')
    ).toBe(NO_DEBT_REASON)
    expect(jobBlocker(controls({ limbo: [] }), 'fate:rejudge_limbo')).toBe(
      NO_LIMBO_REASON
    )
    expect(jobBlocker(controls(), 'births:retry')).toBe(NO_FAILED_BIRTH_REASON)
    expect(
      jobBlocker(controls({ failed_births: 2 }), 'births:retry')
    ).toBeNull()
    expect(jobBlocker(controls(), 'voices:retry')).toBeNull()
  })

  it('surfaces only the work that is waiting', () => {
    expect(urgentJobs(controls()).map((job) => job.action)).toEqual([
      'fate:retry',
      'fate:rejudge_debt',
      'fate:rejudge_limbo',
    ])
    expect(
      urgentJobs(controls({ fate_debt_epoch: null, limbo: [], steps: [] }))
    ).toEqual([])
  })
})

describe('fate controls page', () => {
  it('shows the ledger, step states, limbo and historian accounts', async () => {
    const { screen } = await renderScreen(<FateControlsPage />, routes())
    await expect.element(screen.getByText('Owes epoch 5')).toBeInTheDocument()
    await expect
      .element(screen.getByText('The model did not answer.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The Glass Ossuary'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The Salt Harbours'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('We remember the salt.'))
      .toBeInTheDocument()
  })

  it('runs a retry with its cost and follows the job', async () => {
    const { screen, server } = await renderScreen(<FateControlsPage />, {
      ...routes(),
      'POST /api/actions/fate:retry': {
        action: 'fate:retry',
        message: 'Aeron paid 30 essence: fate:retry began.',
        essence_spent: 30,
        job_id: 'job-fate',
      },
      'GET /api/jobs/job-fate': jobRecord({
        id: 'job-fate',
        kind: 'retry',
        status: 'failed',
        error: 'The model did not answer.',
      }),
    })
    const row = screen.getByText('Retry Fate for the last epoch')
    await expect.element(row).toBeInTheDocument()
    await screen.getByRole('button', { name: /Run/ }).first().click()
    await expect
      .element(
        screen.getByText(
          'The work did not finish, so your 30 essence was returned.'
        )
      )
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/actions/fate:retry')).toHaveLength(1)
  })

  it('blocks retries while the model is off', async () => {
    const { screen } = await renderScreen(
      <FateControlsPage />,
      routes(controls(), { llm_enabled: false })
    )
    await expect
      .element(screen.getByText('Retry Fate for the last epoch'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: /Run/ }).first())
      .toBeDisabled()
  })

  it('overrules a verdict in limbo with a reason', async () => {
    const { screen, server } = await renderScreen(<FateControlsPage />, {
      ...routes(),
      'POST /api/actions/fate:override_verdict': {
        action: 'fate:override_verdict',
        message: 'The Creator overruled Fate.',
        essence_spent: 15,
      },
    })
    await screen.getByRole('button', { name: /^Accept/ }).click()
    await userEvent.fill(
      screen.getByLabelText('Your reason'),
      'It was always there.'
    )
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Accept' })
      .click()
    await expect
      .poll(
        () => server.callsTo('POST /api/actions/fate:override_verdict').length
      )
      .toBe(1)
    expect(
      server.callsTo('POST /api/actions/fate:override_verdict')[0].body
    ).toEqual({
      entity_id: 42,
      choice: 'accept',
      rationale: 'It was always there.',
    })
  })

  it('amends and strikes a historian account', async () => {
    const { screen, server } = await renderScreen(<FateControlsPage />, {
      ...routes(),
      'POST /api/actions/voices:edit_view': {
        action: 'voices:edit_view',
        message: 'Amended.',
      },
      'POST /api/actions/voices:delete_view': {
        action: 'voices:delete_view',
        message: 'Struck.',
      },
    })
    await screen.getByRole('button', { name: 'Amend' }).click()
    await userEvent.fill(
      screen.getByLabelText('The amended account'),
      'We remember the tide.'
    )
    await screen.getByRole('button', { name: /Save the account/ }).click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/voices:edit_view').length)
      .toBe(1)
    expect(
      server.callsTo('POST /api/actions/voices:edit_view')[0].body
    ).toEqual({
      view_id: 9,
      text: 'We remember the tide.',
    })
    await screen.getByRole('button', { name: /^Strike/ }).click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Strike' })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/voices:delete_view').length)
      .toBe(1)
  })

  it('shows the server error when the controls cannot load', async () => {
    const { screen } = await renderScreen(<FateControlsPage />, {
      ...routes(),
      'GET /api/fate/controls': failure(500, 'Fate is silent.'),
    })
    await expect
      .element(screen.getByText('Fate is silent.'))
      .toBeInTheDocument()
  })
})

describe('fate status card', () => {
  it('is calm when nothing waits', async () => {
    const { screen } = await renderScreen(
      <FateStatusCard />,
      routes(controls({ fate_debt_epoch: null, limbo: [], steps: [] }))
    )
    await expect
      .element(screen.getByText(/Fate is at rest/))
      .toBeInTheDocument()
  })

  it('lists the waiting work with its retries', async () => {
    const { screen } = await renderScreen(<FateStatusCard />, routes())
    await expect
      .element(screen.getByText('Fate owes epoch 5'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText("Fate's judgment failed"))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Re-judge the creations in limbo'))
      .toBeInTheDocument()
  })
})
