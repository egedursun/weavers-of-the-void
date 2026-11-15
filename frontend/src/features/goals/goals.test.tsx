import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { GoalsBlock } from './GoalsBlock'

const tiers = (name: string, thresholds: number[], earned: (number | null)[]) =>
  thresholds.map((threshold, index) => ({
    tier: index + 1,
    name: index === 0 ? name : `${name} ${'I'.repeat(index + 1)}`,
    description: `${threshold} counted.`,
    threshold,
    points: (index + 1) * 10,
    epoch: earned[index] ?? null,
  }))

const MANY_WORLDS = {
  key: 'many_worlds',
  category: 'cosmos',
  name: 'A five-world cosmos',
  description: 'At least 5 worlds in the cosmos, each with a living people.',
  points: 250,
  next_tier: 2,
  default_target: 8,
  target_max: 1000,
  history: [
    {
      id: 1,
      status: 'completed',
      name: 'A five-world cosmos',
      tier: 1,
      target: 5,
      start_epoch: 2,
      end_epoch: 4,
      deadline_epoch: null,
      points: 250,
      awarded_points: 250,
      result: 'Worlds with a living people: 5/5',
    },
  ],
}

const LONG_PEACE = {
  key: 'long_peace',
  category: 'order',
  name: '5 epochs of peace',
  description: 'No war stays open for 5 epochs in a row.',
  points: 200,
  next_tier: 1,
  default_target: 5,
  target_max: 1000,
  history: [],
}

const GOALS = {
  epoch: 6,
  categories: [
    { category: 'cosmos', label: 'Cosmos' },
    { category: 'order', label: 'Order' },
    { category: 'peoples', label: 'Peoples' },
  ],
  metrics: [
    {
      metric: 'worlds',
      category: 'cosmos',
      label: 'Worlds in the cosmos',
      value: 3,
      lower_is_better: false,
    },
    {
      metric: 'languages',
      category: 'peoples',
      label: 'Languages',
      value: 12,
      lower_is_better: false,
    },
    {
      metric: 'ongoing_wars',
      category: 'order',
      label: 'Ongoing wars',
      value: 2,
      lower_is_better: true,
    },
  ],
  scenarios: [
    MANY_WORLDS,
    LONG_PEACE,
    {
      key: 'custom',
      category: 'creator',
      name: 'A goal of your own',
      description: 'Choose any measure of the cosmos.',
      points: 150,
      next_tier: 1,
      default_target: 1,
      target_max: 2000000000,
      history: [],
    },
  ],
  running: [
    {
      id: 9,
      key: 'long_peace',
      name: '5 epochs of peace',
      description: 'No war stays open for 5 epochs in a row.',
      tier: 1,
      target: 5,
      start_epoch: 3,
      deadline_epoch: 8,
      held: false,
      hold_epochs: 0,
      points: 250,
      metric: null,
      comparator: null,
      basis: null,
      title: null,
      progress: {
        percent: 40,
        text: '2/5 peace epochs',
        value: 2,
        done: false,
        failed: false,
      },
    },
  ],
  achievements: [
    {
      key: 'babel',
      category: 'peoples',
      metric: 'languages',
      title: 'Babel',
      value: 12,
      tier: 1,
      percent: 13,
      tiers: tiers('Babel', [10, 25, 60], [4]),
    },
    {
      key: 'second_sky',
      category: 'cosmos',
      metric: 'worlds',
      title: 'Many skies',
      value: 3,
      tier: 0,
      percent: 60,
      tiers: tiers('Many skies', [5, 12, 20], []),
    },
  ],
  score: {
    parts: { population: 40, life: 6, doomsday: -10, achievements: 10 },
  },
  score_history: [
    [4, 20],
    [5, 30],
    [6, 46],
  ],
}

const QUOTE = {
  name: 'A eight-world cosmos II',
  description: 'At least 8 worlds.',
  target: 8,
  start_value: 3,
  points: 500,
}

const DONE = { action: 'done', message: 'ok' }

function routes(
  extra: Record<string, unknown> = {},
  state: Record<string, unknown> = {}
) {
  return {
    'GET /api/goals': GOALS,
    'GET /api/goals/quote': QUOTE,
    'GET /api/state': worldState(state),
    ...extra,
  }
}

describe('goals block', () => {
  it('sums the score with every labelled part', async () => {
    const { screen } = await renderScreen(<GoalsBlock />, routes())
    await expect
      .element(screen.getByText('46', { exact: true }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Life')).toBeInTheDocument()
    await expect.element(screen.getByText('+6')).toBeInTheDocument()
    await expect.element(screen.getByText('Apocalypse')).toBeInTheDocument()
    await expect.element(screen.getByText('-10')).toBeInTheDocument()
    await expect
      .element(screen.getByText('1/6', { exact: true }).first())
      .toBeInTheDocument()
  })

  it('shows a running goal with its deadline, holds it and abandons it after confirmation', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({
        'POST /api/scenarios/9/hold': DONE,
        'POST /api/scenarios/9/abandon': DONE,
      })
    )
    await expect
      .element(screen.getByText('2/5 peace epochs'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Epoch 8 · 2 epochs left'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('progressbar', { name: '5 epochs of peace progress' })
      )
      .toHaveAttribute('aria-valuenow', '40')
    await screen.getByRole('button', { name: 'Hold' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/scenarios/9/hold')[0]?.body)
      .toEqual({ held: true })
    await screen.getByRole('button', { name: 'Abandon' }).click()
    expect(server.callsTo('POST /api/scenarios/9/abandon')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Abandon' })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/scenarios/9/abandon').length)
      .toBe(1)
  })

  it('reshapes a running goal with a new target and deadline', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({ 'POST /api/scenarios/9/edit': DONE })
    )
    await screen.getByRole('button', { name: 'Edit' }).click()
    const dialog = screen.getByRole('dialog')
    await dialog.getByLabelText('Target').fill('9')
    await dialog.getByLabelText('Epochs until the deadline').fill('4')
    await dialog.getByRole('button', { name: 'Reshape the goal' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/scenarios/9/edit')[0]?.body)
      .toEqual({
        target: 9,
        deadline_epochs: 4,
        hold_epochs: 0,
        title: null,
      })
  })

  it('sets a board goal with a chosen target, a deadline and a live quote', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({ 'POST /api/scenarios': DONE })
    )
    await expect.element(screen.getByText('Tier II')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Set this goal' }).click()
    const dialog = screen.getByRole('dialog')
    await dialog.getByLabelText('Target').fill('8')
    await dialog.getByRole('switch', { name: 'Set a deadline' }).click()
    await dialog.getByLabelText('Epochs until the deadline').fill('5')
    await expect.element(dialog.getByText('+500')).toBeInTheDocument()
    await expect
      .element(dialog.getByText('Within 5 epochs'))
      .toBeInTheDocument()
    await dialog.getByRole('button', { name: 'Begin the goal' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/scenarios')[0]?.body)
      .toEqual({ key: 'many_worlds', target: 8, deadline_epochs: 5 })
  })

  it('keeps a running board goal from starting twice and says why', async () => {
    const { screen } = await renderScreen(<GoalsBlock />, routes())
    await screen.getByRole('button', { name: 'Running' }).click()
    await expect
      .element(
        screen
          .getByRole('dialog')
          .getByRole('button', { name: 'Begin the goal' })
      )
      .toHaveAttribute('aria-description', 'This goal is already running.')
  })

  it('shapes a goal of ones own from any measure', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({ 'POST /api/scenarios/custom': DONE })
    )
    await expect.element(screen.getByText('Now 3.')).toBeInTheDocument()
    await screen.getByLabelText('Target').fill('6')
    await screen.getByLabelText('Hold').fill('2')
    await screen.getByLabelText('Name of the goal').fill('Six worlds')
    await screen.getByRole('button', { name: 'Set the goal' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/scenarios/custom')[0]?.body)
      .toEqual({
        metric: 'worlds',
        comparator: 'at_least',
        basis: 'total',
        target: 6,
        hold_epochs: 2,
        deadline_epochs: null,
        title: 'Six worlds',
      })
  })

  it('keeps the record of ended goals and strikes one after confirmation', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({ 'POST /api/scenarios/1/delete': DONE })
    )
    await expect.element(screen.getByText('+250 of 250')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Strike' }).click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Strike' })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/scenarios/1/delete').length)
      .toBe(1)
  })

  it('shows achievements tier by tier with progress and filters them by field', async () => {
    const { screen } = await renderScreen(
      <GoalsBlock />,
      routes({ 'GET /api/goals': { ...GOALS, running: [] } })
    )
    await expect
      .element(screen.getByText('No running goal'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Achievements · 1/6' }).click()
    await expect.element(screen.getByText('Babel I')).toBeInTheDocument()
    await expect.element(screen.getByText('I · Epoch 4')).toBeInTheDocument()
    await expect.element(screen.getByText('12 / 25')).toBeInTheDocument()
    await expect.element(screen.getByText('3 / 5')).toBeInTheDocument()
    await screen
      .getByRole('button', { name: /Peoples/ })
      .last()
      .click()
    await expect.element(screen.getByText('3 / 5')).not.toBeInTheDocument()
  })

  it('measures the goals on demand and is read-only in a guest world', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({ 'POST /api/actions/goals:evaluate': DONE })
    )
    await screen.getByRole('button', { name: 'Measure now' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/goals:evaluate').length)
      .toBe(1)
  })

  it('blocks measuring in a guest world', async () => {
    const { screen } = await renderScreen(
      <GoalsBlock />,
      routes({}, { read_only: true })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Measure now' }))
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })
})
