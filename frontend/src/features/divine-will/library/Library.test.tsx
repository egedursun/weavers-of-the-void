import { type MockRequest } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import {
  PANEL_DEFAULT_REM,
  useWillDock,
} from '@/components/layout/divine-will/dockStore'
import { type WillArtifact } from '../types'
import { willArtifact, willArtifactSummary, willPlan } from '../willFixtures'
import { useWill } from '../willStore'
import { LibraryScreen } from './LibraryScreen'

const TOTAL = 30
const PAGE = 24

function listing(request: MockRequest) {
  const offset = Number(request.query.get('offset') ?? 0)
  const count = Math.max(0, Math.min(PAGE, TOTAL - offset))
  return {
    items: Array.from({ length: count }, (_, index) =>
      willArtifactSummary({
        id: offset + index + 1,
        title: `Writing ${String(offset + index + 1)}`,
      })
    ),
    total: TOTAL,
    offset,
    limit: PAGE,
    languages: ['English', 'Latin'],
    tags: ['winter'],
  }
}

function routes(artifact: WillArtifact) {
  return {
    'GET /api/divine-will/artifacts': listing,
    'GET /api/divine-will/artifacts/{artifact_id}': artifact,
    'GET /api/divine-will/artifacts/{artifact_id}/diff': {
      artifact_id: artifact.artifact.id,
      a: 1,
      b: 2,
      text: '--- version 1\n+++ version 2\n@@ -1 +1,2 @@\n The snow came early.\n+The river froze.\n',
      added: 1,
      removed: 0,
    },
    'DELETE /api/divine-will/artifacts/{artifact_id}': { ok: true },
    'GET /api/names': [
      { id: 12, name: 'Old Keep', kind: 'entity', type: 'structure' },
    ],
    'GET /api/state': {},
  }
}

const STORY = willArtifact(
  willArtifactSummary(),
  '# The First Winter\n\nThe snow came early.\n\nThe river froze.'
)

function reset() {
  useWillDock.setState({ open: false, width: PANEL_DEFAULT_REM, view: 'chat' })
  useWill.setState({ mode: 'command', draft: '', seed: null })
}

beforeEach(async () => {
  reset()
  await page.viewport(1440, 900)
})
afterEach(reset)

describe('Library', () => {
  it('pages the shelves with show more', async () => {
    const { screen, server } = await renderScreen(
      <LibraryScreen />,
      routes(STORY)
    )
    await expect
      .element(screen.getByText('Showing 24 of 30 writings, 24 at a time'))
      .toBeInTheDocument()
    expect(
      screen
        .getByRole('list', { name: 'Writings' })
        .getByRole('listitem')
        .elements()
    ).toHaveLength(PAGE)
    await screen.getByRole('button', { name: 'Show more' }).click()
    await expect
      .element(screen.getByRole('button', { name: /^Writing 30,/ }))
      .toBeInTheDocument()
    expect(
      server
        .callsTo('GET /api/divine-will/artifacts')
        .map((call) => call.query.get('offset'))
    ).toContain('24')
    await expect
      .element(screen.getByRole('button', { name: 'Show more' }))
      .not.toBeInTheDocument()
  })

  it('filters by kind and search and clears the filters', async () => {
    const { screen, server } = await renderScreen(
      <LibraryScreen />,
      routes(STORY)
    )
    await screen.getByRole('button', { name: 'Filters', exact: true }).click()
    await screen.getByRole('combobox', { name: 'Kind' }).click()
    await screen.getByRole('option', { name: 'Screenplay' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Filters · 1 set' }))
      .toBeInTheDocument()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/divine-will/artifacts')
          .map((call) => call.query.get('kind'))
      )
      .toContain('screenplay')
    await screen.getByRole('searchbox', { name: 'Search the writings' }).click()
    await userEvent.keyboard('winter')
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/divine-will/artifacts')
          .map((call) => call.query.get('q'))
      )
      .toContain('winter')
    await screen.getByRole('button', { name: 'Clear 2 filters' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Clear filters' }))
      .toHaveAttribute('aria-description', 'No filter is set.')
  })

  it('reads a writing and asks the Divine Will to revise it', async () => {
    const { screen } = await renderScreen(
      <LibraryScreen />,
      routes(STORY),
      '/?artifact=3'
    )
    await expect
      .element(screen.getByRole('heading', { name: 'The First Winter' }))
      .toBeInTheDocument()
    await screen
      .getByRole('button', { name: 'Ask the Divine Will to revise' })
      .click()
    expect(useWillDock.getState().open).toBe(true)
    expect(useWill.getState().mode).toBe('creative_work')
    expect(useWill.getState().seed?.text).toBe(
      'Revise artifact#3 “The First Winter”: '
    )
  })

  it('compares two versions', async () => {
    const { screen } = await renderScreen(
      <LibraryScreen />,
      routes(STORY),
      '/?artifact=3'
    )
    await screen.getByRole('tab', { name: 'Versions' }).click()
    await expect.element(screen.getByText('Version 1 to 2')).toBeInTheDocument()
    await expect
      .poll(() => document.querySelector('[data-change="added"]')?.textContent)
      .toContain('The river froze.')
    await expect.element(screen.getByText('+1')).toBeInTheDocument()
  })

  it('shows a screenplay in screenplay layout and a page sealed', async () => {
    const script = willArtifact(
      willArtifactSummary({
        kind: 'screenplay',
        format: 'fountain',
        title: 'The Hall',
      }),
      'Title: The Hall\n\nINT. HALL - NIGHT\n\nMIRA\n(quietly)\nWe wait.\n\nCUT TO:'
    )
    const { screen } = await renderScreen(
      <LibraryScreen />,
      routes(script),
      '/?artifact=3'
    )
    await expect
      .element(screen.getByText('INT. HALL - NIGHT'))
      .toHaveAttribute('data-fountain', 'scene')
    await expect
      .element(screen.getByText('MIRA'))
      .toHaveAttribute('data-fountain', 'character')
    await expect
      .element(screen.getByText('(quietly)'))
      .toHaveAttribute('data-fountain', 'parenthetical')
    await expect
      .element(screen.getByText('We wait.'))
      .toHaveAttribute('data-fountain', 'dialogue')
    await expect
      .element(screen.getByText('CUT TO:'))
      .toHaveAttribute('data-fountain', 'transition')
  })

  it('deletes a writing only after a warning', async () => {
    const { screen, server } = await renderScreen(
      <LibraryScreen />,
      routes(STORY),
      '/?artifact=3'
    )
    await screen.getByRole('button', { name: 'Delete', exact: true }).click()
    await expect
      .element(
        screen.getByRole('alertdialog', { name: 'Delete this writing?' })
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Delete the writing' }).click()
    await expect
      .poll(() =>
        server.callsTo('DELETE /api/divine-will/artifacts/{artifact_id}')
      )
      .toHaveLength(1)
    await expect
      .element(screen.getByText('Choose a writing'))
      .toBeInTheDocument()
  })

  it('opens a plan on its plan card rather than its text', async () => {
    const plan = willArtifact(
      willArtifactSummary({ id: 4, kind: 'plan', plan_id: 7, title: 'A plan' }),
      '**Plan status:** Draft'
    )
    const { screen } = await renderScreen(
      <LibraryScreen />,
      {
        ...routes(plan),
        'GET /api/divine-will/plans/{plan_id}': willPlan({ id: 7 }),
      },
      '/?artifact=4'
    )
    await expect
      .element(screen.getByRole('tab', { name: 'Plan' }))
      .toHaveAttribute('aria-selected', 'true')
  })
})
