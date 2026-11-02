import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { EpochBreakdownPanel } from './EpochBreakdownPanel'
import { WorldSummary } from './WorldSummary'

const WORLD = {
  id: 1,
  name: 'Aerona',
  seed_idea: 'Corpses of gods.',
  epoch: 5,
  epoch_start_year: 500,
  doom_clock: 3,
  fate_debt_epoch: null,
  lore_language: 'english',
}

function summaryState(overrides: Record<string, unknown> = {}) {
  return worldState({
    world: WORLD,
    creator: { name: 'Ana', essence: 120 },
    last_epoch: { epoch: 4, name: 'The Long Dusk' },
    sons: [],
    ...overrides,
  }) as never
}

const SUMMARY_ROUTES = {
  'GET /api/epoch-star': { current: [], history: [] },
  'GET /api/epoch-stars': { current: [], history: [] },
}

describe('world summary', () => {
  it('shows waiting sons and the previous epoch name', async () => {
    const { screen } = await renderScreen(
      <WorldSummary state={summaryState({ pending_son_ids: [1, 2] })} />,
      SUMMARY_ROUTES
    )
    await expect.element(screen.getByText('2 still to act')).toBeInTheDocument()
    await expect
      .element(screen.getByText('After The Long Dusk'))
      .toBeInTheDocument()
  })

  it('says everyone acted when no son waits', async () => {
    const { screen } = await renderScreen(
      <WorldSummary state={summaryState()} />,
      SUMMARY_ROUTES
    )
    await expect
      .element(screen.getByText('Everyone has acted'))
      .toBeInTheDocument()
  })

  it('shows the Fate debt chip only when Fate could not weigh an epoch', async () => {
    const indebted = await renderScreen(
      <WorldSummary
        state={summaryState({ world: { ...WORLD, fate_debt_epoch: 3 } })}
      />,
      SUMMARY_ROUTES
    )
    await expect
      .element(indebted.screen.getByText('Fate in debt since epoch 3'))
      .toBeInTheDocument()
  })

  it('has no debt chip otherwise and names the lore language', async () => {
    const { screen } = await renderScreen(
      <WorldSummary state={summaryState()} />,
      SUMMARY_ROUTES
    )
    await expect
      .element(screen.getByText(/Fate in debt/))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByText('Lore in English'))
      .toBeInTheDocument()
  })
})

function chipFacts(chip: Element | null | undefined) {
  if (!(chip instanceof HTMLElement)) return null
  return {
    direction: chip.dataset.change,
    text: chip.textContent,
    good: chip.classList.contains('text-success'),
  }
}

function changeOf(field: string) {
  return chipFacts(
    document.querySelector(
      `[data-measure="${field}"] [data-domain="change-chip"]`
    )
  )
}

describe('epoch breakdown popover', () => {
  const current = {
    population: 120,
    followers: 10,
    entities: 50,
    words: 5,
    knowledge: 2,
    languages: 1,
    wars: 2,
    trade_routes: 1,
    alliances: 0,
    structures: 3,
    items: 4,
    dead: 6,
    godless: 1,
    doom: 8,
    doom_items: [
      { item: 'war_losses', delta: 5 },
      { item: 'prayers_answered', delta: -2 },
    ],
    essence_items: [{ item: 'base_refill', delta: 40 }],
    population_items: [],
  }

  it('compares an epoch with the one before, coloured by harm, and lists items with net totals', async () => {
    const { screen, server } = await renderScreen(
      <EpochBreakdownPanel state={summaryState()} />,
      {
        'GET /api/epochs/4/breakdown': {
          current,
          previous: { ...current, population: 100, wars: 3 },
          deltas: {},
          sons: [{ son_id: 7, changes: { faith: 4 } }],
        },
      }
    )
    await expect.element(screen.getByText('from 100')).toBeInTheDocument()
    expect(changeOf('population')).toEqual({
      direction: 'up',
      text: '20',
      good: true,
    })
    expect(changeOf('wars')).toEqual({
      direction: 'down',
      text: '1',
      good: true,
    })
    const warLosses = screen.getByText('War losses')
    await expect.element(warLosses).toBeInTheDocument()
    await expect
      .element(screen.getByRole('progressbar', { name: 'War losses +5' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Prayers answered −2' }))
      .toBeInTheDocument()
    expect(
      chipFacts(
        warLosses
          .element()
          .closest('ul')
          ?.parentElement?.querySelector('[data-domain="change-chip"]')
      )
    ).toEqual({ direction: 'up', text: '3', good: false })
    await expect.element(screen.getByText('Son #7')).toBeInTheDocument()
    expect(server.callsTo('GET /api/epochs/{epoch}/breakdown')[0].path).toBe(
      '/api/epochs/4/breakdown'
    )
  })

  it('loads another epoch from the selector', async () => {
    const { screen, server } = await renderScreen(
      <EpochBreakdownPanel state={summaryState()} />,
      {
        'GET /api/epochs/4/breakdown': {
          current,
          previous: null,
          deltas: {},
          sons: [],
        },
        'GET /api/epochs/2/breakdown': {
          current,
          previous: null,
          deltas: {},
          sons: [],
        },
      }
    )
    await screen.getByRole('combobox', { name: 'Epoch' }).click()
    await screen.getByRole('option', { name: 'Epoch 2' }).click()
    await expect
      .poll(() => server.callsTo('GET /api/epochs/2/breakdown').length)
      .toBe(1)
  })

  it('shows an empty state before any epoch closed', async () => {
    const { screen } = await renderScreen(
      <EpochBreakdownPanel state={summaryState({ last_epoch: null })} />
    )
    await expect
      .element(screen.getByText('No epoch has closed yet'))
      .toBeInTheDocument()
  })
})
