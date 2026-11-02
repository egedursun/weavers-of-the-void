import { ruleList, worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { PrayersScreen } from './PrayersScreen'

function prayer(
  id: number,
  kind: 'son' | 'entity',
  name: string,
  extra: Record<string, unknown> = {}
) {
  return {
    message: {
      id,
      epoch: 3,
      sender_node_id: id,
      recipient_node_id: 0,
      intent: 'friendship',
      text: `Prayer text ${id}`,
      request: null,
      wish: null,
      is_read: false,
      answered: false,
      answered_epoch: null,
      answer_essence: null,
      created_at: 'x',
      ...extra,
    },
    sender: { kind, id: id * 10, name },
  }
}

function routes(
  prayers: unknown[],
  extra: Record<string, unknown> = {},
  state: Record<string, unknown> = {}
) {
  return {
    'GET /api/prayers': prayers,
    'GET /api/state': worldState({ creator: { essence: 50 }, ...state }),
    'GET /api/sons': [],
    'GET /api/names': [],
    'GET /api/rules': ruleList({ 'god_actions.prayer_essence_cap': 20 }),
    ...extra,
  }
}

const MIXED = [
  prayer(1, 'son', 'Ithren'),
  prayer(2, 'entity', 'Old Mara', { request: 'blessing', wish: 'Rain' }),
  prayer(3, 'son', 'Valka', { answered: true, answer_essence: 5 }),
]

describe('prayers inbox', () => {
  it('shows counts per filter, the wish chip, the answered chip and the awaiting badge', async () => {
    const { screen } = await renderScreen(<PrayersScreen />, routes(MIXED))
    await expect
      .element(screen.getByText('2 prayers await an answer'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('radio', { name: 'All · 3' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('radio', { name: 'Awaiting answer · 2' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('radio', { name: 'Sons · 2' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('radio', { name: 'Mortals · 1' }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Wishes: Rain')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Answered · 5 essence'))
      .toBeInTheDocument()
  })

  it('filters by sender kind and awaiting state', async () => {
    const { screen } = await renderScreen(<PrayersScreen />, routes(MIXED))
    await screen.getByRole('radio', { name: 'Mortals · 1' }).click()
    await expect.element(screen.getByText('Prayer text 2')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Prayer text 1'))
      .not.toBeInTheDocument()
    await screen.getByRole('radio', { name: 'Awaiting answer · 2' }).click()
    await expect
      .element(screen.getByText('Prayer text 3'))
      .not.toBeInTheDocument()
  })

  it('filters by world when the cosmos has several', async () => {
    const { screen } = await renderScreen(
      <PrayersScreen />,
      routes(
        MIXED,
        {
          'GET /api/sons': [
            { son: { id: 10, name: 'Ithren', current_world_id: 1 } },
            { son: { id: 30, name: 'Valka', current_world_id: 2 } },
          ],
        },
        {
          worlds: [
            { id: 1, name: 'Aerona' },
            { id: 2, name: 'Nyx' },
          ],
        }
      )
    )
    await screen.getByRole('combobox', { name: 'World' }).click()
    await screen.getByRole('option', { name: 'Nyx' }).click()
    await expect.element(screen.getByText('Showing Nyx')).toBeInTheDocument()
    await expect.element(screen.getByText('Prayer text 3')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Prayer text 1'))
      .not.toBeInTheDocument()
  })

  it('shows empty and error states', async () => {
    const empty = await renderScreen(<PrayersScreen />, routes([]))
    await expect
      .element(empty.screen.getByText('No prayers yet'))
      .toBeInTheDocument()
    const broken = await renderScreen(
      <PrayersScreen />,
      routes([], { 'GET /api/prayers': failure(500, 'Prayers are lost.') })
    )
    await expect
      .element(broken.screen.getByText('Prayers are lost.'))
      .toBeInTheDocument()
  })
})

describe('answering a prayer', () => {
  const one = [prayer(1, 'son', 'Ithren')]

  it('needs words or essence and caps the gift by the rule and the essence in hand', async () => {
    const { screen } = await renderScreen(<PrayersScreen />, routes(one))
    const answer = screen.getByRole('button', { name: 'Answer' })
    await expect
      .element(answer)
      .toHaveAttribute('aria-description', 'Write an answer or give essence.')
    await expect
      .element(screen.getByLabelText('Give essence (at most 20)'))
      .toBeInTheDocument()
    await screen.getByLabelText('Give essence (at most 20)').fill('30')
    await expect
      .element(answer)
      .toHaveAttribute(
        'aria-description',
        'You can give at most 20 essence to one prayer.'
      )
  })

  it('sends the words and the essence gift', async () => {
    const { screen, server } = await renderScreen(
      <PrayersScreen />,
      routes(one, {
        'POST /api/prayers/1/answer': { action: 'answer', message: 'ok' },
      })
    )
    await screen.getByLabelText('Your answer').fill('Be patient')
    await screen.getByLabelText('Give essence (at most 20)').fill('8')
    await expect
      .element(screen.getByLabelText('costs 8 essence'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Answer' }).click()
    await expect
      .element(screen.getByText('Answer and 8 essence sent'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/prayers/1/answer')[0].body).toEqual({
      text: 'Be patient',
      essence: 8,
    })
  })

  it('lands as a dream for a mortal', async () => {
    const { screen } = await renderScreen(
      <PrayersScreen />,
      routes([prayer(2, 'entity', 'Old Mara')])
    )
    await expect
      .element(screen.getByRole('button', { name: 'Answer with a dream' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByLabelText('What should fall into their dream?'))
      .toBeInTheDocument()
  })

  it('explains a guest world', async () => {
    const { screen } = await renderScreen(
      <PrayersScreen />,
      routes(one, {}, { read_only: true })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Answer' }))
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })
})
