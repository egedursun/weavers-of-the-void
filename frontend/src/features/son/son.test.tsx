import { ruleList, worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { HandOfGodPanel } from './HandOfGodPanel'
import { SonRecords } from './SonRecords'

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

describe('son records', () => {
  it('keeps the old words spoken with the son among its words', async () => {
    const creator = { id: 1, kind: 'creator', name: 'Aeron' }
    const ithren = { id: 7, kind: 'son', name: 'Ithren' }
    const detail = {
      worshippers: [],
      creations: [],
      messages: [
        {
          id: 1,
          epoch: 3,
          sender: creator,
          recipient: ithren,
          intent: 'chat',
          text: 'Where were you when the river rose?',
          tone: null,
          answered: true,
        },
        {
          id: 2,
          epoch: 3,
          sender: ithren,
          recipient: creator,
          intent: 'prayer',
          text: 'Grant the harvest.',
          tone: null,
          answered: false,
        },
      ],
    } as never
    const { screen } = await renderScreen(
      <SonRecords detail={detail} />,
      routes()
    )
    await expect
      .element(screen.getByText('"Where were you when the river rose?"'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('"Grant the harvest."'))
      .toBeInTheDocument()
  })
})
