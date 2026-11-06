import { ruleList, worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { beforeEach, describe, expect, it } from 'vitest'
import { HandOfGodPanel } from './HandOfGodPanel'
import { SonChat } from './SonChat'

const STATS = {
  strength: 20,
  endurance: 20,
  agility: 20,
  wisdom: 20,
  cunning: 20,
  will: 20,
  creativity: 20,
  charisma: 20,
  might: 4,
}

function son(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    name: 'Ithren',
    status: 'active',
    rarity: 'rare',
    essence: 30,
    hp: 50,
    existence: 60,
    level: 3,
    chained: false,
    order_absolute: false,
    turn_rank: null,
    standing_order: null,
    current_world_id: 1,
    sanity: 50,
    ...STATS,
    ...overrides,
  }
}

function view(sonOverrides: Record<string, unknown> = {}) {
  return {
    son: son(sonOverrides),
    powers: [],
    max_essence: 100,
    max_hp: 100,
    next_star: null,
    ascension: null,
  } as never
}

const RULES = ruleList({
  'costs.bless_essence': 20,
  'costs.bless_hp': 10,
  'god_power.absolute_command_cost': 50,
})

function routes(
  state: Record<string, unknown> = {},
  extra: Record<string, unknown> = {}
) {
  return {
    'GET /api/state': worldState({
      creator: { essence: 100 },
      worlds: [{ id: 1, name: 'Aerona' }],
      ...state,
    }),
    'GET /api/rules': RULES,
    'GET /api/sons': [],
    'GET /api/foreign-gods': [],
    'GET /api/jobs': [],
    ...extra,
  }
}

describe('hand of god panel', () => {
  it('announces a standing order from the order box', async () => {
    const { screen, server } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={200} />,
      routes(
        {},
        { 'PUT /api/sons/7/order': { action: 'order', message: 'ok' } }
      )
    )
    await expect
      .element(screen.getByRole('button', { name: 'Clear standing order' }))
      .toBeInTheDocument()
    await screen
      .getByLabelText('Order for their next action')
      .fill('Guard the salt road')
    await screen.getByRole('button', { name: 'Announce order' }).click()
    await expect
      .element(screen.getByText('Order announced'))
      .toBeInTheDocument()
    expect(server.callsTo('PUT /api/sons/7/order')[0].body).toEqual({
      text: 'Guard the salt road',
    })
  })

  it('needs words and a confirmation for an absolute command', async () => {
    const { screen, server } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={200} />,
      routes(
        {},
        {
          'POST /api/sons/7/absolute-command': { action: 'cmd', message: 'ok' },
        }
      )
    )
    const button = screen.getByRole('button', { name: /Absolute command/ })
    await expect
      .element(button)
      .toHaveAttribute(
        'aria-description',
        'Write the command in the order box first.'
      )
    await screen.getByLabelText('Order for their next action').fill('March')
    await expect
      .element(screen.getByLabelText('costs 50 essence'))
      .toBeInTheDocument()
    await button.click()
    await expect
      .element(
        screen.getByRole('heading', { name: 'Give an irrefusable command?' })
      )
      .toBeInTheDocument()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: /Absolute command/ })
      .click()
    await expect
      .element(screen.getByText('Irrefusable command given'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/7/absolute-command')[0].body).toEqual(
      { text: 'March' }
    )
  })

  it('blesses with essence at the rule cost and sends the kind', async () => {
    const { screen, server } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={200} />,
      routes(
        {},
        { 'POST /api/sons/7/bless': { action: 'bless', message: 'ok' } }
      )
    )
    await screen.getByRole('button', { name: /^Essence/ }).click()
    await expect.element(screen.getByText('Blessed')).toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/7/bless')[0].body).toEqual({
      kind: 'essence',
    })
  })

  it('blocks blessings that would change nothing', async () => {
    const { screen } = await renderScreen(
      <HandOfGodPanel
        view={view({ essence: 100, hp: 100, existence: 100 })}
        ready
        killCost={200}
      />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: /^Essence/ }))
      .toHaveAttribute('aria-description', 'Essence already full (100/100).')
    await expect
      .element(screen.getByRole('button', { name: /^Fill life/ }))
      .toHaveAttribute('aria-description', 'Life is already full.')
    await expect
      .element(screen.getByRole('button', { name: /^Remember them/ }))
      .toHaveAttribute('aria-description', 'Their existence is already whole.')
  })

  it('refuses a blessing the creator cannot afford', async () => {
    const { screen } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={200} />,
      routes({ creator: { essence: 5 } })
    )
    await expect
      .element(screen.getByRole('button', { name: /^Essence/ }))
      .toHaveAttribute('aria-description', '20 essence needed; you have 5.')
  })

  it('kills only after confirmation, charging the priced cost', async () => {
    const { screen, server } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={80} />,
      routes({}, { 'POST /api/sons/7/kill': { action: 'kill', message: 'ok' } })
    )
    await screen.getByRole('button', { name: /^Kill/ }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Kill Ithren?' }))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/7/kill')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: /^Kill/ })
      .click()
    await expect.element(screen.getByText('Ithren died')).toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/7/kill')).toHaveLength(1)
  })

  it('cannot act when he already acted and is blocked while an epoch runs', async () => {
    const idle = await renderScreen(
      <HandOfGodPanel view={view()} ready={false} killCost={80} />,
      routes()
    )
    await expect
      .element(idle.screen.getByRole('button', { name: 'Act now' }))
      .toHaveAttribute(
        'aria-description',
        'Acted this epoch, asleep, chained, exiled or fading.'
      )
  })

  it('is blocked while an epoch runs', async () => {
    const { screen } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={80} />,
      routes({ epoch_running: true })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Act now' }))
      .toHaveAttribute(
        'aria-description',
        'An epoch is running; this opens when it ends.'
      )
  })

  it('is read-only in a guest world', async () => {
    const { screen } = await renderScreen(
      <HandOfGodPanel view={view()} ready killCost={80} />,
      routes({ read_only: true })
    )
    await expect
      .element(screen.getByRole('button', { name: /^Essence/ }))
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })
})

describe('son chat', () => {
  beforeEach(() => localStorage.clear())
  const record = (overrides: Record<string, unknown> = {}) =>
    son(overrides) as never

  it('shows the transcript with the son and the creator on opposite sides', async () => {
    const { screen } = await renderScreen(
      <SonChat son={record()} cover={null} />,
      routes(
        {},
        {
          'GET /api/sons/7/chat': [
            { id: 1, epoch: 2, sender_node_id: 99, text: 'Speak, Ithren.' },
            { id: 2, epoch: 2, sender_node_id: 7, text: 'I listen, father.' },
          ],
          'GET /api/rules': [
            ...RULES,
            ...ruleList({ 'council.chat_max_chars': 400 }),
          ],
        }
      )
    )
    await expect.element(screen.getByText('Speak, Ithren.')).toBeInTheDocument()
    await expect
      .element(screen.getByText('I listen, father.'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('You · Epoch 2')).toBeInTheDocument()
  })

  it('shows empty and dead states', async () => {
    const alive = await renderScreen(
      <SonChat son={record({ id: 8 })} cover={null} />,
      routes({}, { 'GET /api/sons/8/chat': [] })
    )
    await expect
      .element(alive.screen.getByText('No words yet'))
      .toBeInTheDocument()
  })

  it('does not reach a dead son', async () => {
    const { screen } = await renderScreen(
      <SonChat son={record({ id: 9, status: 'dead' })} cover={null} />,
      routes({}, { 'GET /api/sons/9/chat': [] })
    )
    await expect
      .element(screen.getByText('Too late', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByLabelText('What do you say to Ithren?'))
      .toBeDisabled()
  })

  it('sends words, shows the reply attitude and loyalty change', async () => {
    const { screen, server } = await renderScreen(
      <SonChat son={record({ id: 10 })} cover={null} />,
      routes(
        {},
        {
          'GET /api/sons/10/chat': [],
          'POST /api/sons/10/chat': {
            attitude: 'loyal',
            change: 3,
            loyalty: 70,
            reply: 'ok',
          },
        }
      )
    )
    const say = screen.getByRole('button', { name: 'Say' })
    await expect
      .element(say)
      .toHaveAttribute('aria-description', 'Write something first.')
    await screen.getByLabelText('What do you say to Ithren?').fill('Be brave')
    await say.click()
    await expect
      .element(screen.getByText('Loyalty +3 → 70'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/sons/10/chat')[0].body).toEqual({
      text: 'Be brave',
    })
  })

  it('returns failed text to the box and shows the error', async () => {
    const { screen } = await renderScreen(
      <SonChat son={record({ id: 11 })} cover={null} />,
      routes(
        {},
        {
          'GET /api/sons/11/chat': [],
          'POST /api/sons/11/chat': failure(503, 'The model did not answer.'),
        }
      )
    )
    await screen.getByLabelText('What do you say to Ithren?').fill('Hear me')
    await screen.getByRole('button', { name: 'Say' }).click()
    await expect
      .element(screen.getByText('The model did not answer.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByLabelText('What do you say to Ithren?'))
      .toHaveValue('Hear me')
  })
})
