import { jobRecord, ruleList, worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { TurnOrderPanel } from '@/features/epoch/TurnOrderPanel'
import { orderedSons } from '@/features/epoch/turnOrder'
import { BeliefSection } from '@/features/pantheon/BeliefSection'
import { SonBirthChild } from './SonBirthChild'
import { AddressSibling } from './SonSiblings'

const DONE = {
  action: 'done',
  message: 'It is done.',
  ledger_entry_id: null,
  job_id: null,
}

function son(
  id: number,
  name: string,
  overrides: Record<string, unknown> = {}
) {
  return { id, name, status: 'active', turn_rank: null, ...overrides } as never
}

const SIBLINGS = [
  {
    son: { id: 8, name: 'Morvane', kind: 'son' },
    value: 10,
    note: null,
    cover: null,
  },
  {
    son: { id: 9, name: 'Asheth', kind: 'son' },
    value: -20,
    note: null,
    cover: null,
  },
] as never

describe('a son speaks to a sibling', () => {
  it('needs a sibling and words, then orders the speech with its intent', async () => {
    const { screen, server } = await renderScreen(
      <AddressSibling sonId={7} alive options={[{ id: 8, name: 'Morvane' }]} />,
      {
        'GET /api/state': worldState(),
        'POST /api/actions/son:address_sibling': DONE,
      }
    )
    const speak = screen.getByRole('button', { name: 'Speak' })
    await expect
      .element(speak)
      .toHaveAttribute('aria-description', 'Pick a sibling.')
    await screen.getByRole('combobox', { name: 'Sibling to address' }).click()
    await screen.getByRole('option', { name: 'Morvane' }).click()
    await screen.getByRole('combobox', { name: 'Intent' }).click()
    await screen.getByRole('option', { name: 'Threat' }).click()
    await expect
      .element(speak)
      .toHaveAttribute('aria-description', 'Write the words they must say.')
    await screen
      .getByRole('textbox', { name: 'The words they must say' })
      .fill('  Leave the salt road to me.  ')
    await speak.click()
    await expect
      .poll(
        () => server.callsTo('POST /api/actions/son:address_sibling').length
      )
      .toBe(1)
    expect(
      server.callsTo('POST /api/actions/son:address_sibling')[0].body
    ).toEqual({
      son_id: 7,
      sibling_id: 8,
      intent: 'threat',
      text: 'Leave the salt road to me.',
    })
  })
})

describe('a son bears a child', () => {
  it('confirms, sends the co-parent and inspiration and follows the job', async () => {
    const { screen, server } = await renderScreen(
      <SonBirthChild son={son(7, 'Ithren')} siblings={SIBLINGS} />,
      {
        'GET /api/state': worldState(),
        'GET /api/rules': ruleList({
          'god_actions.inspiration_max_chars': 600,
        }),
        'GET /api/jobs': [],
        'GET /api/jobs/{job_id}': jobRecord({
          id: 'birth-1',
          kind: 'summon',
          stage: 'birth',
          progress: 0.25,
        }),
        'POST /api/actions/son:birth_child': { ...DONE, job_id: 'birth-1' },
      }
    )
    await screen.getByRole('combobox', { name: 'Other parent' }).click()
    await screen.getByRole('option', { name: 'Asheth' }).click()
    await screen
      .getByRole('textbox', { name: 'Inspiration' })
      .fill('A child of tides')
    await screen.getByRole('button', { name: 'Bear a child' }).click()
    expect(server.callsTo('POST /api/actions/son:birth_child')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Bear a child' })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/son:birth_child').length)
      .toBe(1)
    expect(server.callsTo('POST /api/actions/son:birth_child')[0].body).toEqual(
      {
        son_id: 7,
        inspiration: 'A child of tides',
        co_parent_id: 9,
      }
    )
    await expect.element(screen.getByText("Ithren's child")).toBeVisible()
  })

  it('waits for the language model', async () => {
    const { screen } = await renderScreen(
      <SonBirthChild son={son(7, 'Ithren')} siblings={SIBLINGS} />,
      {
        'GET /api/state': worldState({ llm_enabled: false }),
        'GET /api/jobs': [],
      }
    )
    await expect
      .element(screen.getByRole('button', { name: 'Bear a child' }))
      .toHaveAttribute(
        'aria-description',
        'The language model is not connected; this needs it.'
      )
  })
})

describe("the gods' turn order", () => {
  const state = worldState({
    sons: [
      { son: son(7, 'Ithren') },
      { son: son(8, 'Morvane', { turn_rank: 2 }) },
      { son: son(9, 'Asheth', { turn_rank: 1 }) },
      { son: son(10, 'Orveth', { status: 'dead' }) },
    ],
  }) as never

  it('lists pinned sons first and leaves the dead out', () => {
    expect(orderedSons(state).map((item) => item.name)).toEqual([
      'Asheth',
      'Morvane',
      'Ithren',
    ])
  })

  it('pins a son to a place and releases a pinned one', async () => {
    const { screen, server } = await renderScreen(
      <TurnOrderPanel state={state} />,
      {
        'GET /api/state': state,
        'POST /api/actions/son:turn_rank': DONE,
      }
    )
    await expect.element(screen.getByText('By initiative')).toBeVisible()
    const place = screen.getByRole('spinbutton', {
      name: 'Place in the turn for Ithren',
    })
    const pin = screen.getByRole('button', { name: 'Pin' })
    const release = screen.getByRole('button', { name: 'Release' })
    await expect.element(release.first()).toBeVisible()
    expect(release.elements()).toHaveLength(2)
    await place.fill('0')
    await expect
      .element(pin)
      .toHaveAttribute('aria-description', 'Give a place of 1 or more.')
    await place.fill('1')
    await pin.click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/son:turn_rank').length)
      .toBe(1)
    expect(server.callsTo('POST /api/actions/son:turn_rank')[0].body).toEqual({
      son_id: 7,
      rank: 1,
    })
    await release.first().click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/son:turn_rank').length)
      .toBe(2)
    expect(server.callsTo('POST /api/actions/son:turn_rank')[1].body).toEqual({
      son_id: 9,
      rank: null,
    })
  })
})

describe('folk belief names', () => {
  it("derives a people's name for the god anew", async () => {
    const views = [
      {
        people_id: 31,
        people_name: 'Marsh Folk',
        god_node_id: 7,
        local_name: 'Ith-the-wet',
        account: 'He rose from the reeds.',
        misconception: null,
        epoch: 2,
      },
    ] as never
    const { screen, server } = await renderScreen(
      <BeliefSection views={views} sonId={7} godName='Ithren' />,
      {
        'GET /api/state': worldState(),
        'POST /api/actions/belief:rename': {
          ...DONE,
          message: 'Marsh Folk now call him Ithrael.',
        },
      }
    )
    await screen.getByRole('button', { name: 'Derive the name anew' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/belief:rename').length)
      .toBe(1)
    expect(server.callsTo('POST /api/actions/belief:rename')[0].body).toEqual({
      people_id: 31,
      son_id: 7,
    })
    await expect
      .element(screen.getByText('Marsh Folk now call him Ithrael.'))
      .toBeVisible()
  })
})
