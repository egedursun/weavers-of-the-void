import { jobRecord, worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { MaintenancePage } from './MaintenancePage'
import { VerifyBackupButton } from './VerifyBackupButton'
import { counterLabel, resultCounters, resultLedgerEntry } from './jobResult'

const TASK = (
  task: string,
  title: string,
  options: Record<string, unknown> = {}
) => ({
  task,
  title,
  description: `${title} description.`,
  automatic: 'At startup',
  rows: [],
  ledgered: true,
  needs_llm: false,
  running: false,
  ...options,
})

const MISSING = {
  portrait: true,
  son_powers: [7],
  sky_body: false,
  first_people: false,
  image_prompts: 3,
  undeepened_gods: [],
  pending_names: 0,
  past_narratives: [2],
  anything_missing: true,
}

const NETWORK = {
  nodes: 40,
  edges: 90,
  past_edges: 4,
  active_edges: 86,
  mean_degree: 4.3,
  median_degree: 4,
  density: 0.1,
  components: 1,
  largest_component: 40,
  largest_share_pct: 100,
  isolated: 0,
  single_link: 2,
  weak: 2,
  related: 6,
  related_undescribed: 0,
  related_to_review: 0,
  weakest: [],
  log: [],
  priority: 0,
  healthy: true,
}

function routes(
  state: Record<string, unknown> = {},
  missing: unknown = MISSING
) {
  return {
    'GET /api/state': worldState(state),
    'GET /api/names': [{ kind: 'son', id: 7, name: 'Ithren', type: 'Rare' }],
    'GET /api/jobs': [],
    'GET /api/maintenance/tasks': [
      TASK('completion', 'Complete missing content', {
        ledgered: false,
        needs_llm: true,
      }),
      TASK('importance', 'Recompute importance'),
      TASK('prune', 'Prune old data', { ledgered: false }),
    ],
    'GET /api/maintenance/missing': missing,
    'GET /api/graph/health': NETWORK,
    'GET /api/rules': [],
  }
}

describe('job results', () => {
  it('reads nested and flat counters and the ledger entry', () => {
    expect(
      resultCounters({
        task: 'prune',
        counters: { media: 2 },
        ledger_entry_id: 4,
      })
    ).toEqual([{ key: 'media', label: 'Media', value: 2 }])
    expect(
      resultCounters({ epoch: 6, born: 1, son_id: 7 }).map((item) => item.key)
    ).toEqual(['epoch', 'born'])
    expect(resultLedgerEntry({ ledger_entry_id: 4 })).toBe(4)
    expect(resultLedgerEntry(null)).toBeNull()
    expect(counterLabel('change_log')).toBe('Change log')
  })
})

describe('maintenance page', () => {
  it('lists missing content and every task', async () => {
    const { screen } = await renderScreen(<MaintenancePage />, routes())
    await expect
      .element(screen.getByText('Not written yet'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Epoch 2')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Recompute importance', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Prune old data', { exact: true }))
      .toBeInTheDocument()
  })

  it('runs a task and shows its counters and ledger entry', async () => {
    const { screen, server } = await renderScreen(<MaintenancePage />, {
      ...routes(),
      'POST /api/maintenance/tasks/{task}/run': { job_id: 'job-task' },
      'GET /api/jobs/job-task': jobRecord({
        id: 'job-task',
        kind: 'maintenance',
        status: 'succeeded',
        progress: 1,
        result: {
          task: 'importance',
          counters: { records: 12 },
          ledger_entry_id: 31,
        },
      }),
    })
    const row = screen.getByText('Recompute importance', { exact: true })
    await expect.element(row).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Run now' }).nth(1).click()
    await expect.element(screen.getByText('Records 12')).toBeInTheDocument()
    await expect
      .element(screen.getByText(/Ledger entry 31/))
      .toBeInTheDocument()
    expect(
      server.callsTo('POST /api/maintenance/tasks/{task}/run')[0].path
    ).toBe('/api/maintenance/tasks/importance/run')
  })

  it('shows the conflict message when the epoch holds the world', async () => {
    const { screen } = await renderScreen(<MaintenancePage />, {
      ...routes(),
      'POST /api/maintenance/chronicles': failure(
        409,
        'An epoch is running; wait for it to finish or stop it.'
      ),
    })
    await screen.getByRole('button', { name: 'Write chronicles' }).click()
    await expect
      .element(
        screen.getByText(
          'An epoch is running; wait for it to finish or stop it.'
        )
      )
      .toBeInTheDocument()
  })

  it('writes a son powers for the suggested son', async () => {
    const { screen, server } = await renderScreen(<MaintenancePage />, {
      ...routes(),
      'POST /api/maintenance/sons/{son_id}/powers': { job_id: 'job-powers' },
      'GET /api/jobs/job-powers': jobRecord({
        id: 'job-powers',
        kind: 'content',
        status: 'running',
      }),
    })
    await expect
      .element(screen.getByRole('combobox').first())
      .toHaveTextContent('Ithren')
    await screen.getByRole('button', { name: 'Write powers' }).click()
    await expect
      .poll(
        () =>
          server.callsTo('POST /api/maintenance/sons/{son_id}/powers').length
      )
      .toBe(1)
    expect(
      server.callsTo('POST /api/maintenance/sons/{son_id}/powers')[0].path
    ).toBe('/api/maintenance/sons/7/powers')
  })

  it('disables model work when the model is off', async () => {
    const { screen } = await renderScreen(
      <MaintenancePage />,
      routes({ llm_enabled: false })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Write chronicles' }))
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Complete now' }))
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Run now' }).first())
      .toBeDisabled()
  })

  it('says when nothing is missing', async () => {
    const { screen } = await renderScreen(
      <MaintenancePage />,
      routes(
        {},
        {
          ...MISSING,
          portrait: false,
          son_powers: [],
          image_prompts: 0,
          past_narratives: [],
          anything_missing: false,
        }
      )
    )
    await expect
      .element(screen.getByText('8 of 8 in place'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Complete', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByLabelText('Missing', { exact: true }))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Complete now' }))
      .toHaveAttribute('aria-description', 'Nothing is missing.')
  })
})

describe('verify backup', () => {
  it('reports a sound backup', async () => {
    const { screen, server } = await renderScreen(
      <VerifyBackupButton file='epoch-0006.db' />,
      {
        'POST /api/maintenance/backups/{file_name}/verify': {
          file: 'epoch-0006.db',
          ok: true,
        },
      }
    )
    await screen.getByRole('button', { name: 'Verify' }).click()
    await expect
      .element(screen.getByText('epoch-0006.db is sound and can be restored.'))
      .toBeInTheDocument()
    expect(
      server.callsTo('POST /api/maintenance/backups/{file_name}/verify')
    ).toHaveLength(1)
  })

  it('shows why a backup is broken', async () => {
    const { screen } = await renderScreen(
      <VerifyBackupButton file='broken.db' />,
      {
        'POST /api/maintenance/backups/{file_name}/verify': failure(
          422,
          'The backup is not a world database.'
        ),
      }
    )
    await screen.getByRole('button', { name: 'Verify' }).click()
    await expect
      .element(screen.getByText('The backup is not a world database.'))
      .toBeInTheDocument()
  })
})
