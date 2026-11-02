import { jobRecord, ruleList, worldState } from '@/test-utils/fixtures'
import { failure, type MockRequest } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { AwakenPeoplesControl } from './AwakenPeoplesControl'
import { NewThreadForm } from './NewThreadForm'
import { StoryThreads } from './StoryThreads'
import { SummonButton } from './SummonButton'
import { essenceReason } from './gate'

const RULES = ruleList({
  'costs.summon_son': 100,
  'costs.revelation': 30,
  'balance.awaken_peoples': 20,
  'balance.council': 40,
  'awakening.batch_cap': 3,
})

const WORLDS = [
  { id: 1, name: 'Aerona' },
  { id: 2, name: 'Nyx' },
]

function godRoutes(
  state: Record<string, unknown> = {},
  extra: Record<string, unknown> = {}
) {
  return {
    'GET /api/state': worldState({
      creator: { essence: 500, name: 'Ana' },
      worlds: WORLDS,
      ...state,
    }),
    'GET /api/rules': RULES,
    'GET /api/actions': [
      {
        id: 'awaken_peoples',
        title: 'Awaken peoples',
        group: 'creator',
        mode: 'job',
        cost: '20 essence per batch',
        confirmation: null,
        rows: [],
        path: '/api/peoples/awaken',
        method: 'POST',
        input_schema: {
          properties: { count: { default: 3, type: 'integer' } },
        },
      },
    ],
    'GET /api/jobs': [],
    'GET /api/names': [
      {
        id: 10,
        name: 'Stonehold',
        kind: 'entity',
        type: 'settlement',
        world_id: 1,
      },
      { id: 11, name: 'Ithren', kind: 'son', type: 'son', world_id: 1 },
    ],
    'GET /api/threads': [],
    'GET /api/expeditions': [],
    ...extra,
  }
}

afterEach(() => localStorage.clear())

describe('gate reasons', () => {
  it('words the missing essence', () => {
    expect(essenceReason(1200, 4)).toBe('1,200 essence needed; you have 4.')
  })
})

describe('summon a son', () => {
  it('shows the rule cost and summons with Fate choosing the world', async () => {
    const { screen, server } = await renderScreen(
      <SummonButton />,
      godRoutes(
        {},
        { 'POST /api/sons/summon': { action: 'summon', message: 'ok' } }
      )
    )
    const button = screen.getByRole('button', { name: /Summon a son/ })
    await expect.element(button).toBeEnabled()
    await expect
      .element(screen.getByLabelText('costs 100 essence'))
      .toBeInTheDocument()
    await button.click()
    expect(server.callsTo('POST /api/sons/summon')[0].body).toEqual({
      world_id: null,
    })
    await expect
      .element(screen.getByText('A son is answering your call'))
      .toBeInTheDocument()
  })

  it('targets the selected world when the cosmos has several', async () => {
    const { screen, server } = await renderScreen(
      <SummonButton />,
      godRoutes(
        {},
        { 'POST /api/sons/summon': { action: 'summon', message: 'ok' } }
      )
    )
    await screen
      .getByRole('combobox', { name: 'World for the new son' })
      .click()
    await screen.getByRole('option', { name: 'Nyx' }).click()
    await screen.getByRole('button', { name: /Summon a son/ }).click()
    expect(server.callsTo('POST /api/sons/summon')[0].body).toEqual({
      world_id: 2,
    })
  })

  it('hides the world choice in a single-world cosmos', async () => {
    const { screen } = await renderScreen(
      <SummonButton />,
      godRoutes({ worlds: [WORLDS[0]] })
    )
    await expect
      .element(screen.getByRole('button', { name: /Summon a son/ }))
      .toBeEnabled()
    await expect.element(screen.getByRole('combobox')).not.toBeInTheDocument()
  })

  const blocked: [string, Record<string, unknown>, string][] = [
    [
      'not enough essence',
      { creator: { essence: 4 } },
      '100 essence needed; you have 4.',
    ],
    [
      'an epoch running',
      { epoch_running: true },
      'An epoch is running; this opens when it ends.',
    ],
    [
      'no language model',
      { llm_enabled: false },
      'The language model is not connected; this needs it.',
    ],
    ['a guest world', { read_only: true }, 'A guest world is open read-only.'],
  ]
  for (const [name, state, reason] of blocked)
    it(`explains the block for ${name}`, async () => {
      const { screen } = await renderScreen(<SummonButton />, godRoutes(state))
      await expect
        .element(screen.getByRole('button', { name: /Summon a son/ }))
        .toHaveAttribute('aria-description', reason)
    })

  it('is blocked while a son is already being summoned', async () => {
    const { screen } = await renderScreen(
      <SummonButton />,
      godRoutes(
        {},
        { 'GET /api/jobs': [jobRecord({ kind: 'summon', status: 'running' })] }
      )
    )
    await expect
      .element(screen.getByRole('button', { name: /Summon a son/ }))
      .toHaveAttribute('aria-description', 'A son is already being summoned.')
  })

  it('shows the server error as a toast', async () => {
    const { screen } = await renderScreen(
      <SummonButton />,
      godRoutes(
        {},
        { 'POST /api/sons/summon': failure(409, 'The world is full of sons.') }
      )
    )
    await screen.getByRole('button', { name: /Summon a son/ }).click()
    await expect
      .element(screen.getByText('The world is full of sons.'))
      .toBeInTheDocument()
  })
})

describe('awaken peoples', () => {
  it('prices per batch of the rule cap and sends the count', async () => {
    const { screen, server } = await renderScreen(
      <AwakenPeoplesControl />,
      godRoutes(
        {},
        { 'POST /api/peoples/awaken': { action: 'awaken', message: 'ok' } }
      )
    )
    const count = screen.getByLabelText('Peoples to awaken')
    await expect.element(count).toHaveValue(3)
    await expect
      .element(screen.getByLabelText('costs 20 essence'))
      .toBeInTheDocument()
    await count.fill('7')
    await expect
      .element(screen.getByLabelText('costs 60 essence'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByText(/Every 3 peoples are one batch, paid per batch/)
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: /Awaken peoples/ }).click()
    expect(server.callsTo('POST /api/peoples/awaken')[0].body).toEqual({
      count: 7,
      world_id: null,
    })
  })

  it('refuses an invalid count and a cost beyond the essence', async () => {
    const { screen } = await renderScreen(
      <AwakenPeoplesControl />,
      godRoutes({ creator: { essence: 30 } })
    )
    const count = screen.getByLabelText('Peoples to awaken')
    await count.fill('0')
    await expect
      .element(screen.getByRole('button', { name: /Awaken peoples/ }))
      .toHaveAttribute('aria-description', 'Choose how many.')
    await count.fill('10')
    await expect
      .element(screen.getByRole('button', { name: /Awaken peoples/ }))
      .toHaveAttribute('aria-description', '80 essence needed; you have 30.')
  })

  it('lets Fate choose the world or sends the picked one', async () => {
    const { screen, server } = await renderScreen(
      <AwakenPeoplesControl />,
      godRoutes(
        {},
        { 'POST /api/peoples/awaken': { action: 'awaken', message: 'ok' } }
      )
    )
    await screen
      .getByRole('combobox', { name: 'World for the new peoples' })
      .click()
    await expect
      .element(screen.getByRole('option', { name: 'Let Fate choose' }))
      .toBeInTheDocument()
    await screen.getByRole('option', { name: 'Aerona' }).click()
    await screen.getByRole('button', { name: /Awaken peoples/ }).click()
    expect(server.callsTo('POST /api/peoples/awaken')[0].body).toMatchObject({
      world_id: 1,
    })
  })
})

describe('open a new story', () => {
  it('needs the story text and sends it with the related records', async () => {
    const { screen, server } = await renderScreen(
      <NewThreadForm />,
      godRoutes(
        {},
        { 'POST /api/threads': { action: 'thread', message: 'ok' } }
      )
    )
    await screen.getByRole('button', { name: 'Open a new story' }).click()
    const submit = screen.getByRole('button', { name: 'Open the story' })
    await expect
      .element(submit)
      .toHaveAttribute('aria-description', 'Write the story first.')
    await screen.getByLabelText('The story').fill('The exiled heir returns.')
    await screen.getByRole('combobox').click()
    await screen.getByRole('option', { name: /Stonehold/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Remove Stonehold' }))
      .toBeInTheDocument()
    await submit.click()
    await expect
      .element(screen.getByText('A new story is open; Fate will follow it'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/threads')[0].body).toEqual({
      text: 'The exiled heir returns.',
      related_ids: [10],
    })
    await expect.element(screen.getByLabelText('The story')).toHaveValue('')
  })
})

describe('story threads', () => {
  const thread = (
    id: number,
    status: 'open' | 'closed',
    extra: Record<string, unknown> = {}
  ) => ({
    id,
    epoch: 2,
    text: `Story text ${id}`,
    status,
    closing_text: null,
    closed_epoch: null,
    progress: 0,
    related: [],
    ...extra,
  })

  it('shows number, epoch, progress and closing text across open and closed stories', async () => {
    const { screen } = await renderScreen(
      <StoryThreads />,
      godRoutes(
        {},
        {
          'GET /api/threads': [
            thread(1, 'open', { progress: 3 }),
            thread(2, 'closed', {
              closed_epoch: 5,
              closing_text: 'It ended well.',
            }),
          ],
        }
      )
    )
    await expect
      .element(screen.getByText('Story #1 · Epoch 2 · advanced 3 times'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Story text 2'))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: 'Show closed stories' }).click()
    await expect
      .element(screen.getByText('Story #2 · Epoch 2 · closed in Epoch 5'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('It ended well.')).toBeInTheDocument()
  })

  it('shows empty states for open and closed stories', async () => {
    const { screen } = await renderScreen(<StoryThreads />, godRoutes())
    await expect.element(screen.getByText('No open story')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Show closed stories' }).click()
    await expect
      .element(screen.getByText('No closed story yet'))
      .toBeInTheDocument()
  })

  it('limits the list and expands it on request', async () => {
    const threads = Array.from({ length: 8 }, (_, index) =>
      thread(index + 1, 'open')
    )
    const { screen } = await renderScreen(
      <StoryThreads />,
      godRoutes({}, { 'GET /api/threads': threads })
    )
    await expect.element(screen.getByText('Story text 6')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Story text 7'))
      .not.toBeInTheDocument()
    await screen
      .getByRole('button', { name: 'Show all stories (2 more)' })
      .click()
    await expect.element(screen.getByText('Story text 8')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Show less' }).click()
    await expect
      .element(screen.getByText('Story text 8'))
      .not.toBeInTheDocument()
  })

  it('closes a story with the optional closing note', async () => {
    const { screen, server } = await renderScreen(
      <StoryThreads />,
      godRoutes(
        {},
        {
          'GET /api/threads': [thread(4, 'open')],
          'POST /api/threads/4/close': (request: MockRequest) => ({
            action: 'close',
            message: String((request.body as { how: string }).how),
          }),
        }
      )
    )
    await screen.getByRole('button', { name: 'Close the story' }).click()
    await userEvent.type(
      screen.getByLabelText('How did it close? (optional)'),
      'Peace was made'
    )
    await screen.getByRole('button', { name: 'Close', exact: true }).click()
    await expect.element(screen.getByText('Story closed')).toBeInTheDocument()
    expect(server.callsTo('POST /api/threads/4/close')[0].body).toEqual({
      how: 'Peace was made',
    })
  })
})
