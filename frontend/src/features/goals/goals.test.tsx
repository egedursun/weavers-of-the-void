import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { GoalsBlock } from './GoalsBlock'

const GOALS = {
  scenarios: [
    {
      key: 'many_worlds',
      name: 'Populate the worlds',
      description: 'Reach a thousand souls.',
      points: 10,
      history: [
        {
          id: 1,
          status: 'failed',
          start_epoch: 2,
          end_epoch: 4,
          result: null,
        },
      ],
    },
    {
      key: 'one_faith',
      name: 'Speak many tongues',
      description: 'Grow five languages.',
      points: 5,
      history: [],
    },
  ],
  running: [
    {
      id: 9,
      key: 'one_faith',
      name: 'Speak many tongues',
      start_epoch: 3,
      progress: {
        percent: 40,
        text: '2 of 5 languages',
        done: false,
        failed: false,
      },
    },
  ],
  achievements: [
    {
      key: 'first_prayer',
      name: 'First son',
      description: 'Summon a son.',
      points: 3,
      earned: true,
      epoch: 2,
    },
    {
      key: 'babel',
      name: 'Doomsayer',
      description: 'Reach doom.',
      points: 8,
      earned: false,
      epoch: null,
    },
  ],
  score: { parts: { population: 40, doomsday: -10 } },
  score_history: [
    [1, 10],
    [2, 20],
  ],
}

function routes(
  extra: Record<string, unknown> = {},
  state: Record<string, unknown> = {}
) {
  return {
    'GET /api/goals': GOALS,
    'GET /api/state': worldState(state),
    ...extra,
  }
}

describe('goals block', () => {
  it('sums the score with its breakdown and labels the negative apocalypse part', async () => {
    const { screen } = await renderScreen(<GoalsBlock />, routes())
    await expect
      .element(screen.getByText('30', { exact: true }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Population')).toBeInTheDocument()
    await expect.element(screen.getByText('+40')).toBeInTheDocument()
    await expect.element(screen.getByText('Apocalypse')).toBeInTheDocument()
    await expect.element(screen.getByText('-10')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('img', { name: 'Score over the epochs' }))
      .toBeInTheDocument()
  })

  it('shows a running scenario with progress and abandons it after confirmation', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({
        'POST /api/scenarios/9/abandon': { action: 'abandon', message: 'ok' },
      })
    )
    await expect
      .element(screen.getByText('2 of 5 languages'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('progressbar', { name: 'Speak many tongues progress' })
      )
      .toHaveAttribute('aria-valuenow', '40')
    await screen.getByRole('button', { name: 'Abandon' }).click()
    await expect
      .element(
        screen.getByRole('heading', { name: 'Abandon Speak many tongues?' })
      )
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/scenarios/9/abandon')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Abandon' })
      .click()
    await expect.element(screen.getByText('Goal abandoned')).toBeInTheDocument()
    expect(server.callsTo('POST /api/scenarios/9/abandon')).toHaveLength(1)
  })

  it('offers scenarios with history, blocks a running one and starts another', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({ 'POST /api/scenarios': { action: 'start', message: 'ok' } })
    )
    await expect.element(screen.getByText('Epoch 2 to 4')).toBeInTheDocument()
    const starts = screen.getByRole('button', { name: 'Start' })
    await expect
      .element(starts.nth(1))
      .toHaveAttribute('aria-description', 'Already running.')
    await starts.first().click()
    await expect
      .element(screen.getByText('You set yourself a new goal'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/scenarios')[0].body).toEqual({
      key: 'many_worlds',
    })
  })

  it('shows the empty state when no goal runs and the achievements count', async () => {
    const { screen } = await renderScreen(
      <GoalsBlock />,
      routes({ 'GET /api/goals': { ...GOALS, running: [] } })
    )
    await expect
      .element(screen.getByText('No running goal'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Achievements · 1/2' }).click()
    await expect.element(screen.getByText('First son')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Epoch 2', { exact: true }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('+8')).toBeInTheDocument()
  })

  it('measures the goals on demand and is read-only in a guest world', async () => {
    const { screen, server } = await renderScreen(
      <GoalsBlock />,
      routes({
        'POST /api/actions/goals:evaluate': {
          action: 'evaluate',
          message: 'ok',
        },
      })
    )
    await screen.getByRole('button', { name: 'Measure now' }).click()
    await expect.element(screen.getByText('Goals measured')).toBeInTheDocument()
    expect(server.callsTo('POST /api/actions/goals:evaluate')).toHaveLength(1)
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
