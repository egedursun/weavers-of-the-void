import { worldState } from '@/test-utils/fixtures'
import { failure, type MockRequest } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import { useFeedPreferences } from '@/features/feed/feedStore'
import { useFeedOverlay } from '@/features/feed/useFeedDock'
import { useOnboarding } from '@/features/onboarding/onboardingStore'
import { FeedSoundSettings } from './FeedSoundSettings'
import { GameSettings } from './GameSettings'
import { GuideSettings } from './GuideSettings'
import { HealthPanel } from './HealthPanel'
import { RecordsSettings } from './RecordsSettings'
import { ResetWorld } from './ResetWorld'
import { SettingsPage } from './SettingsPage'

const CHEAT_RULE = {
  namespace: 'server',
  key: 'cheat_essence_max',
  value: 5000,
  default: 5000,
  minimum: 1,
  maximum: 100000,
  group: 'server',
  label: 'Cheat cap',
  integer: true,
}

const BULK_IDLE = {
  state: {
    running: false,
    stop_requested: false,
    total: 0,
    done: 0,
    failed: 0,
    skipped: 0,
  },
  log: [],
  waiting: 0,
  unnamed: 0,
}

const METRICS_EMPTY = {
  totals: {
    calls: 0,
    milliseconds: 0,
    cost: 0,
    input_tokens: 0,
    output_tokens: 0,
  },
  epochs: [],
  models: [],
  steps: [],
  slowest: [],
  latest_errors: [],
  slow_threshold_ms: 30000,
}

function gameRoutes(state: Record<string, unknown> = {}) {
  return {
    'GET /api/state': worldState({ creator: { essence: 250 }, ...state }),
    'GET /api/settings': failure(500, 'unused'),
    'GET /api/rules': [CHEAT_RULE],
    'GET /api/batch-deepen': BULK_IDLE,
    'GET /api/metrics/models': METRICS_EMPTY,
  }
}

async function miniStat(label: string) {
  const name = page.getByText(label, { exact: true })
  await expect.element(name).toBeInTheDocument()
  const card = name.element().closest('[data-domain="mini-stat"]')
  expect(card).not.toBeNull()
  return page.elementLocator(card as HTMLElement)
}

beforeEach(() => {
  useOnboarding.setState({ done: [], dismissed: false })
  useFeedPreferences.setState({
    open: false,
    sounds: false,
    ambient: false,
    muted: [],
  })
})
afterEach(() => localStorage.clear())

describe('settings shell', () => {
  it('offers the four tabs plus world rules and marks the current one', async () => {
    const { screen } = await renderScreen(
      <SettingsPage />,
      {},
      '/settings/records'
    )
    for (const name of ['Appearance', 'Game', 'Records', 'Data'])
      await expect
        .element(screen.getByRole('tab', { name }))
        .toBeInTheDocument()
    await expect
      .element(screen.getByRole('tab', { name: 'Records' }))
      .toHaveAttribute('aria-selected', 'true')
    await expect
      .element(screen.getByRole('tab', { name: 'Data' }))
      .toHaveAttribute('aria-selected', 'false')
  })

  it('falls back to the first tab on an unknown path', async () => {
    const { screen } = await renderScreen(<SettingsPage />, {}, '/settings')
    await expect
      .element(screen.getByRole('tab', { name: 'Appearance' }))
      .toHaveAttribute('aria-selected', 'true')
  })
})

describe('game settings', () => {
  it('shows an empty state when there is no world', async () => {
    const { screen } = await renderScreen(
      <GameSettings />,
      gameRoutes({ world: null })
    )
    await expect
      .element(screen.getByText('No world to configure'))
      .toBeInTheDocument()
  })

  it('shows the lore language as a fixed choice', async () => {
    const { screen } = await renderScreen(
      <GameSettings />,
      gameRoutes({
        world: { id: 1, name: 'Aerona', epoch: 3, lore_language: 'turkish' },
      })
    )
    const language = screen
      .getByRole('region', { name: 'Model and lore language' })
      .getByText('Turkish', { exact: true })
    await expect.element(language).toBeInTheDocument()
    await language.hover()
    await expect
      .element(
        screen.getByText('Chosen once at genesis; it cannot be changed').first()
      )
      .toBeVisible()
  })

  it('counts missing image prompts and writes them all on request', async () => {
    const { screen, server } = await renderScreen(<GameSettings />, {
      ...gameRoutes({ promptless_count: 7 }),
      'POST /api/entities/prompts/write-missing': {},
    })
    const missing = screen.getByRole('region', { name: 'Image prompts' })
    await expect
      .element(missing.getByText('Records without a prompt'))
      .toBeInTheDocument()
    await expect
      .element(missing.getByText('7', { exact: true }))
      .toBeInTheDocument()
    await screen
      .getByRole('button', { name: 'Write all missing prompts now' })
      .click()
    await expect
      .element(screen.getByText('Writing the missing prompts'))
      .toBeInTheDocument()
    expect(
      server.callsTo('POST /api/entities/prompts/write-missing')
    ).toHaveLength(1)
  })

  it('explains why prompts cannot be written', async () => {
    const none = await renderScreen(
      <GameSettings />,
      gameRoutes({ promptless_count: 0 })
    )
    await expect
      .element(
        none.screen.getByRole('button', {
          name: 'Write all missing prompts now',
        })
      )
      .toHaveAttribute('aria-description', 'No record is missing a prompt')
  })

  it('explains that writing prompts needs the model', async () => {
    const { screen } = await renderScreen(
      <GameSettings />,
      gameRoutes({ promptless_count: 3, llm_enabled: false })
    )
    await expect
      .element(
        screen.getByRole('button', { name: 'Write all missing prompts now' })
      )
      .toHaveAttribute(
        'aria-description',
        'Writing prompts needs the language model, which is turned off'
      )
  })

  it('adds cheat essence within the rule cap and shows the current essence', async () => {
    const { screen, server } = await renderScreen(<GameSettings />, {
      ...gameRoutes(),
      'POST /api/cheats/essence': (request: MockRequest) => ({
        message: `Added ${(request.body as { amount: number }).amount}`,
      }),
    })
    await expect
      .element(screen.getByText(/At most 5,000 at once/))
      .toBeInTheDocument()
    await expect
      .element(
        screen
          .getByRole('region', { name: 'Cheat: divine essence' })
          .getByText('250', { exact: true })
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Add' }).click()
    await expect.element(screen.getByText('Added 1000')).toBeInTheDocument()
    expect(server.callsTo('POST /api/cheats/essence')[0].body).toEqual({
      amount: 1000,
    })
  })

  it('blocks a cheat amount above the cap or not a whole number', async () => {
    const { screen } = await renderScreen(<GameSettings />, gameRoutes())
    const amount = screen.getByLabelText('Amount')
    await amount.fill('9000')
    await expect
      .element(screen.getByRole('button', { name: 'Add' }))
      .toHaveAttribute(
        'aria-description',
        'Enter a whole number within the limit'
      )
    await amount.fill('12.5')
    await expect
      .element(screen.getByRole('button', { name: 'Add' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('disables cheating in a guest world', async () => {
    const { screen } = await renderScreen(
      <GameSettings />,
      gameRoutes({ read_only: true })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Add' }))
      .toHaveAttribute('aria-description', 'A guest world is read-only')
  })
})

describe('records settings', () => {
  it('links the ledger, the book and the codex download', async () => {
    const { screen } = await renderScreen(<RecordsSettings />, {
      'GET /api/state': worldState(),
      'GET /api/metrics/models': METRICS_EMPTY,
    })
    await expect
      .element(screen.getByRole('link', { name: /^Action ledger/ }))
      .toHaveAttribute('href', '/ledger')
    await expect
      .element(screen.getByRole('link', { name: /^The book/ }))
      .toHaveAttribute('href', '/api/book')
    await expect
      .element(screen.getByRole('link', { name: /^Codex with pictures/ }))
      .toHaveAttribute('href', '/api/codex.zip')
    await expect
      .element(screen.getByRole('link', { name: /^Markdown only/ }))
      .toHaveAttribute('href', '/api/codex.md')
  })

  it('disables the book before a world exists', async () => {
    const { screen } = await renderScreen(<RecordsSettings />, {
      'GET /api/state': worldState({ world: null }),
      'GET /api/metrics/models': METRICS_EMPTY,
    })
    await expect
      .element(screen.getByRole('button', { name: /^The book/ }))
      .toHaveAttribute(
        'aria-description',
        'There is no world to write down yet'
      )
  })
})

describe('guide settings', () => {
  it('brings the guide back only after it was dismissed', async () => {
    useOnboarding.setState({ dismissed: true })
    const { screen } = await renderScreen(<GuideSettings />)
    const button = screen.getByRole('button', { name: 'Show the guide again' })
    await button.click()
    await expect
      .element(screen.getByText('The guide is back on the overview'))
      .toBeInTheDocument()
    expect(useOnboarding.getState().dismissed).toBe(false)
    await expect
      .element(button)
      .toHaveAttribute('aria-description', 'The guide is already shown')
  })

  it('opens the shortcuts and terms drawer', async () => {
    const { screen, router } = await renderScreen(<GuideSettings />)
    await screen.getByRole('button', { name: 'Shortcuts and terms' }).click()
    await expect
      .poll(() => (router.state.location.search as { drawer?: string }).drawer)
      .toBe('help')
  })
})

describe('feed and sound settings', () => {
  it('remembers the docked feed panel and reveals the per-category mute list with sounds', async () => {
    await page.viewport(1900, 900)
    const { screen } = await renderScreen(<FeedSoundSettings />)
    await expect
      .element(screen.getByText('Which events make a sound', { exact: true }))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByText('The event feed stays docked beside the page.'))
      .toBeVisible()
    await screen.getByRole('switch', { name: 'Live feed open' }).click()
    expect(useFeedPreferences.getState().open).toBe(true)
    await screen.getByRole('switch', { name: 'Feed sounds' }).click()
    await expect
      .element(screen.getByText('Which events make a sound', { exact: true }))
      .toBeInTheDocument()
    await screen.getByRole('switch', { name: 'Wars' }).click()
    expect(useFeedPreferences.getState().muted).toEqual(['war'])
    await expect
      .element(screen.getByRole('button', { name: 'Listen to Wars' }))
      .toBeInTheDocument()
  })

  it('slides the feed in over a screen too narrow to dock it', async () => {
    await page.viewport(1512, 900)
    const { screen } = await renderScreen(<FeedSoundSettings />)
    await expect
      .element(
        screen.getByText(
          'The event feed slides in over the page; the screen is too narrow to dock it beside the page.'
        )
      )
      .toBeVisible()
    await screen.getByRole('switch', { name: 'Live feed open' }).click()
    expect(useFeedOverlay.getState().open).toBe(true)
    useFeedOverlay.setState({ open: false })
  })

  it('stores the ambient hum preference', async () => {
    const { screen } = await renderScreen(<FeedSoundSettings />)
    await screen.getByRole('switch', { name: 'Ambient sound' }).click()
    expect(useFeedPreferences.getState().ambient).toBe(true)
    await screen.getByRole('switch', { name: 'Ambient sound' }).click()
    expect(useFeedPreferences.getState().ambient).toBe(false)
  })
})

describe('health panel', () => {
  const report = {
    status: 'ok',
    version: '0.1.0',
    uptime_seconds: 3700,
    database: {
      file: 'aerona.db',
      size: 4096,
      wal_size: 1024,
      quick_check: 'ok',
    },
    latest_backup: 'epoch-3.db',
    latest_backup_age_minutes: 5,
    backup_count: 4,
    running_jobs: 1,
    read_only: true,
    log_file: 'aerona.log',
    recent_errors: [{ level: 'error', at: '12:00', text: 'The disk is slow' }],
  }

  it('reports status, database integrity, backups and recent errors', async () => {
    const { screen } = await renderScreen(<HealthPanel />, {
      'GET /api/health/report': { report },
    })
    await expect.element(screen.getByText('All good')).toBeInTheDocument()
    await expect.element(screen.getByText('Read-only')).toBeInTheDocument()
    const database = await miniStat('Database')
    await expect.element(database.getByText('4 KB')).toBeInTheDocument()
    ;(database.element() as HTMLElement).focus()
    await expect
      .element(screen.getByText('aerona.db with 1 KB of journal').first())
      .toBeVisible()
    const integrity = await miniStat('Integrity')
    await expect.element(integrity.getByText('Sound')).toBeInTheDocument()
    const backups = await miniStat('Backups')
    await expect
      .element(backups.getByText('4', { exact: true }))
      .toBeInTheDocument()
    const last = await miniStat('Last backup')
    await expect.element(last.getByText('5 min ago')).toBeInTheDocument()
    ;(last.element() as HTMLElement).focus()
    await expect.element(screen.getByText('epoch-3.db').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Show the recent error' }).click()
    await expect.element(screen.getByText('12:00 · error')).toBeInTheDocument()
    await expect
      .element(screen.getByText('The disk is slow'))
      .toBeInTheDocument()
  })

  it('flags a failing database check and an empty backup list', async () => {
    const { screen } = await renderScreen(<HealthPanel />, {
      'GET /api/health/report': {
        report: {
          ...report,
          status: 'degraded',
          read_only: false,
          backup_count: 0,
          recent_errors: [],
          database: { ...report.database, quick_check: 'page 3 corrupt' },
        },
      },
    })
    await expect.element(screen.getByText('degraded')).toBeInTheDocument()
    const integrity = await miniStat('Integrity')
    await expect
      .element(integrity.getByText('page 3 corrupt'))
      .toBeInTheDocument()
    const backups = await miniStat('Backups')
    await expect
      .element(backups.getByText('0', { exact: true }))
      .toBeInTheDocument()
    const errors = await miniStat('Recent errors')
    await expect
      .element(errors.getByText('0', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Show the recent error' }))
      .not.toBeInTheDocument()
  })

  it('shows the server error when the report cannot load', async () => {
    const { screen } = await renderScreen(<HealthPanel />, {
      'GET /api/health/report': failure(500, 'The report failed.'),
    })
    await expect
      .element(screen.getByText('The report failed.'))
      .toBeInTheDocument()
  })
})

describe('reset the world', () => {
  it('resets only after typing RESET and reports the safety copy', async () => {
    const { screen, server } = await renderScreen(
      <ResetWorld hasWorld readOnly={false} />,
      {
        'POST /api/world/reset': { safety_backup: 'safe-1.db' },
      }
    )
    await screen.getByRole('button', { name: 'Reset the world' }).click()
    const confirm = screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Reset the world' })
    await expect.element(confirm).toBeDisabled()
    await userEvent.type(
      screen.getByLabelText('Type RESET to confirm'),
      'RESET'
    )
    await confirm.click()
    await expect
      .element(screen.getByText('World reset. Safety copy: safe-1.db'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/world/reset')[0].body).toEqual({
      confirm: 'RESET',
    })
  })

  it('is disabled without a world', async () => {
    const { screen } = await renderScreen(
      <ResetWorld hasWorld={false} readOnly={false} />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Reset the world' }))
      .toHaveAttribute('aria-description', 'There is no world to reset')
  })

  it('is disabled in a guest world', async () => {
    const { screen } = await renderScreen(<ResetWorld hasWorld readOnly />)
    await expect
      .element(screen.getByRole('button', { name: 'Reset the world' }))
      .toHaveAttribute('aria-description', 'A guest world is read-only')
  })

  it('shows the server error when the reset is refused', async () => {
    const { screen } = await renderScreen(
      <ResetWorld hasWorld readOnly={false} />,
      {
        'POST /api/world/reset': failure(409, 'An epoch is running.'),
      }
    )
    await screen.getByRole('button', { name: 'Reset the world' }).click()
    await userEvent.type(
      screen.getByLabelText('Type RESET to confirm'),
      'RESET'
    )
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Reset the world' })
      .click()
    await expect
      .element(screen.getByText('An epoch is running.'))
      .toBeInTheDocument()
  })
})
