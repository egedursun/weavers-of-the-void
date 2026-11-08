import { godData, godRoutes } from '@/test-utils/godRoutes'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { CouncilRecord } from '@/features/council/CouncilRecord'
import { CompareSons } from './CompareSons'
import { GodPanel } from './GodPanel'
import { PantheonScreen } from './PantheonScreen'
import { SonCard } from './SonCard'
import { SonRevealOverlay } from './SonRevealOverlay'
import { ThisEpochBox } from './ThisEpochBox'
import { type SonPublic } from './api'

type Council = Parameters<typeof CouncilRecord>[0]['council']
type WorldState = Parameters<typeof ThisEpochBox>[0]['state']

const SONS = godData('/api/sons') as unknown as SonPublic[]
const STATE = godData('/api/state') as unknown as WorldState
const COUNCILS = godData('/api/councils') as unknown as Council[]
const [THALASSIR, LONG_NAMED, KHARUN, MIREL] = SONS

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

describe('son card', () => {
  it('shows rarity, stars, name, title, domains, level, vitals, nine stats, power slots and footer', async () => {
    const { screen } = await renderScreen(
      <SonCard view={THALASSIR} ready worldName='Thessaly Deep' />,
      godRoutes()
    )
    const card = screen.getByRole('link', { name: 'Thalassir' })
    await expect.element(card).toBeVisible()
    await expect.element(screen.getByText('Legendary').first()).toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: '3 stars' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Keeper of the Drowned Bells'))
      .toBeVisible()
    await expect.element(screen.getByText('Sea', { exact: true })).toBeVisible()
    await expect
      .element(screen.getByText('Oath', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Level 5')).toBeVisible()
    await expect.element(screen.getByText('Thessaly Deep')).toBeVisible()
    for (const stat of ['Life', 'Essence', 'Existence · Solid'])
      await expect
        .element(screen.getByText(stat, { exact: true }))
        .toBeVisible()
    for (const power of ['Tide Ledger', 'Bell of Return', 'Oathbinder'])
      await expect.element(screen.getByText(power)).toBeVisible()
    await expect.element(screen.getByText('/ 500 XP')).toBeVisible()
    expect(
      document.querySelector(
        '[data-son-card="7"] [data-domain="level-meter"] data[value="340"]'
      )
    ).not.toBeNull()
    const statBars = document.querySelectorAll(
      '[data-son-card="7"] [data-slot="progress"]'
    )
    expect(statBars.length).toBeGreaterThanOrEqual(12)
  })

  it('carries the reputation chip, last words, last action, closest sibling and nemesis', async () => {
    const { screen } = await renderScreen(
      <SonCard view={THALASSIR} ready={false} />,
      godRoutes()
    )
    await expect
      .element(screen.getByText('Sees the Creator: Loved'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('The sea keeps every promise it is made to keep.')
      )
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'Epoch 11: Raised a lighthouse temple above the drowned city of Oskar.'
        )
      )
      .toBeVisible()
    await expect.element(screen.getByText(/Vaelorithan.*\+64/)).toBeVisible()
    await expect.element(screen.getByText('Kharun the Ashen -48')).toBeVisible()
  })

  it('shows the plan and the first opportunity of the epoch', async () => {
    const { screen } = await renderScreen(
      <SonCard
        view={THALASSIR}
        ready
        hints={['Bind the Dune Mirrors with a dream.', 'Curse his creation.']}
      />,
      godRoutes()
    )
    await expect
      .element(screen.getByText(/Plan: Raise a lighthouse temple/))
      .toBeVisible()
    await expect.element(screen.getByText('Opportunities · 2')).toBeVisible()
    await expect
      .element(screen.getByText('Bind the Dune Mirrors with a dream.'))
      .toBeVisible()
  })

  it('shows the standing order in place of the plan', async () => {
    const { screen } = await renderScreen(
      <SonCard view={LONG_NAMED} ready={false} />,
      godRoutes()
    )
    await expect
      .element(
        screen.getByText(/Order: Send a dream of fire to the priests of Kharun/)
      )
      .toBeVisible()
  })

  it('opens the son drawer when the card is clicked and marks dead sons', async () => {
    const { screen, router } = await renderScreen(
      <>
        <SonCard view={KHARUN} ready={false} />
        <SonCard view={MIREL} ready={false} />
      </>,
      godRoutes()
    )
    await expect
      .element(screen.getByRole('link', { name: '† Mirel' }))
      .toBeVisible()
    await expect.element(screen.getByText('No power awakened')).toBeVisible()
    await screen.getByText('Lord of Cinders').click()
    await expect
      .poll(() => JSON.stringify(router.state.location.search))
      .toContain('son')
  })
})

describe('son reveal overlay', () => {
  it('reveals an arriving son with his full card and opens his card', async () => {
    const { screen, emit, router } = await renderScreen(
      <SonRevealOverlay />,
      godRoutes()
    )
    emit('son.new', { son_id: 7, rarity: 'legendary' })
    const dialog = screen.getByRole('dialog')
    await expect.element(dialog.getByText('A new son arrives')).toBeVisible()
    await expect
      .element(dialog.getByRole('heading', { name: 'Legendary' }))
      .toBeVisible()
    await expect
      .element(dialog.getByText('Thalassir, Keeper of the Drowned Bells'))
      .toBeVisible()
    await expect.element(dialog.getByText('Tide Ledger')).toBeVisible()
    const openCard = dialog
      .getByRole('button', { name: 'Open their page' })
      .element() as HTMLElement
    openCard.click()
    await expect.element(screen.getByRole('dialog')).not.toBeInTheDocument()
    await expect
      .poll(() => JSON.stringify(router.state.location.search))
      .toContain('son')
  })

  it('announces an ascension and closes with Escape', async () => {
    const { screen, emit } = await renderScreen(
      <SonRevealOverlay />,
      godRoutes()
    )
    emit('son.ascended', { son_id: 8, rarity: 'mythic' })
    await expect.element(screen.getByText('Ascension')).toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'Mythic' }))
      .toBeVisible()
    await userEvent.keyboard('{Escape}')
    await expect.element(screen.getByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('this epoch box', () => {
  it('lists prayers, waiting sons, affordable spends, notifications and server opportunities', async () => {
    const { screen } = await renderScreen(
      <ThisEpochBox state={STATE} />,
      godRoutes()
    )
    await expect.element(screen.getByText('Epoch 12')).toBeVisible()
    await expect
      .element(screen.getByText('2 prayers await an answer.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Answer' }))
      .toHaveAttribute('href', '/prayers')
    await expect
      .element(screen.getByText(/1 son has not acted this epoch yet/))
      .toBeVisible()
    await expect.element(screen.getByText('186 essence to spend')).toBeVisible()
    for (const spend of [
      'reveal · 25',
      'summon a son · 30',
      'convene the council · 20',
      'awaken peoples · 35',
    ])
      await expect.element(screen.getByText(spend)).toBeVisible()
    await expect
      .element(screen.getByText('3 unread notifications.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Read' }))
      .toHaveAttribute('href', '/notifications')
    await expect
      .element(screen.getByRole('link', { name: 'Action ledger' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Reveal' }).first())
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'You have 900 essence: enough for a new world, son or star.'
        )
      )
      .toBeVisible()
  })

  it('hides for this epoch and reopens', async () => {
    const { screen } = await renderScreen(
      <ThisEpochBox state={STATE} />,
      godRoutes()
    )
    await screen.getByRole('button', { name: 'Hide for this epoch' }).click()
    const reopen = screen.getByRole('button', {
      name: /This epoch: to-dos and opportunities/,
    })
    await expect.element(reopen).toBeVisible()
    await reopen.click()
    await expect
      .element(screen.getByRole('button', { name: 'Hide for this epoch' }))
      .toBeVisible()
  })

  it('names an interrupted epoch instead of waiting sons', async () => {
    const { screen } = await renderScreen(
      <ThisEpochBox
        state={
          {
            ...STATE,
            half_epoch: { epoch: 11, started: true, phase: 2 },
          } as unknown as WorldState
        }
      />,
      godRoutes()
    )
    await expect
      .element(
        screen.getByText(
          'Epoch 11 was interrupted; it can be completed from where it stopped.'
        )
      )
      .toBeVisible()
  })
})

describe('compare sons', () => {
  it('compares up to three remembered sons with level, vitals, stats, passions and reputation', async () => {
    const { screen } = await renderScreen(<CompareSons />, godRoutes())
    await expect
      .element(screen.getByText('Pick at least two sons to compare.'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Compare Thalassir' }).click()
    await screen
      .getByRole('button', { name: 'Compare Kharun the Ashen' })
      .click()
    const table = screen.getByRole('table')
    await expect.element(table).toBeVisible()
    for (const row of [
      'Level',
      'Life',
      'Essence',
      'Existence',
      'Faith',
      'Fame',
      'Reputation',
    ])
      await expect
        .element(table.getByRole('rowheader', { name: row, exact: true }))
        .toBeVisible()
    await expect.element(table.getByText('Stats')).toBeVisible()
    await expect.element(table.getByText('Passions')).toBeVisible()
    await expect
      .element(table.getByText('How they see the Creator'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Compare Mirel' }).click()
    await expect.element(screen.getByText('At most 3 sons.')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /^Compare Vaelorithan/ }))
      .toBeDisabled()
    expect(
      JSON.parse(
        localStorage.getItem('aerona.compare') ??
          localStorage.getItem(Object.keys(localStorage)[0]) ??
          '[]'
      )
    ).toEqual([7, 9, 10])
    await screen.getByRole('button', { name: 'Compare Mirel' }).click()
    await screen
      .getByRole('button', { name: 'Compare Kharun the Ashen' })
      .click()
    await screen.getByRole('button', { name: 'Compare Thalassir' }).click()
  })
})

describe('creator panel on the pantheon', () => {
  it('shows portrait, name, title, mood gauges, appearance and opens the creator drawer', async () => {
    const { screen, router } = await renderScreen(
      <GodPanel state={STATE} />,
      godRoutes()
    )
    await expect
      .element(screen.getByRole('heading', { name: 'Aeron' }))
      .toBeVisible()
    await expect.element(screen.getByText('The Unwritten Dawn')).toBeVisible()
    await expect
      .element(screen.getByText('Whole cosmos · 2 worlds'))
      .toBeVisible()
    await expect.element(screen.getByText('Sons see: Respected')).toBeVisible()
    await expect.element(screen.getByText('62/100')).toBeVisible()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Doom clock' }))
      .toBeVisible()
    const godless = screen.getByText('Godless communities')
    await expect.element(godless).toBeVisible()
    expect(
      godless
        .element()
        .closest('[data-domain="mini-stat"]')
        ?.querySelector('data')
        ?.getAttribute('value')
    ).toBe('3')
    await expect.element(screen.getByText('1 in rebellion')).toBeVisible()
    await expect
      .element(
        screen.getByText('Curious, slow to anger, terrible when roused.')
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Epic and depth' }).click()
    await expect
      .poll(() => JSON.stringify(router.state.location.search))
      .toContain('creator')
    await screen.getByRole('button', { name: 'Images', exact: true }).click()
    await expect
      .poll(() => JSON.stringify(router.state.location.search))
      .toContain('creator')
  })

  it('saves the portrait prompt and redraws the likeness as a job', async () => {
    const { screen, server } = await renderScreen(
      <GodPanel state={STATE} />,
      godRoutes()
    )
    await screen
      .getByRole('button', { name: 'Portrait prompt and likeness' })
      .click()
    const save = screen.getByRole('button', { name: 'Save prompt' })
    await expect
      .element(save)
      .toHaveAttribute('aria-description', 'Nothing changed.')
    await screen
      .getByLabelText('Portrait prompt')
      .fill('A dawn over drowned bells')
    await save.click()
    await expect.poll(() => server.callsTo('PATCH /api/creator').length).toBe(1)
    expect(server.callsTo('PATCH /api/creator')[0].body).toEqual({
      image_prompt: 'A dawn over drowned bells',
    })
    await screen.getByRole('button', { name: /Redraw the likeness/ }).click()
    await expect
      .poll(() => server.callsTo('POST /api/creator/portrait').length)
      .toBe(1)
  })
})

describe('council record', () => {
  it('shows topic, outcome, counts, caller, speeches, motion, votes, bar, notes and minutes', async () => {
    const { screen } = await renderScreen(
      <CouncilRecord council={COUNCILS[0]} />,
      godRoutes()
    )
    await expect
      .element(screen.getByText('How can the doom clock be stopped?'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Accepted', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('2 yes · 0 abstain · 1 no'))
      .toBeVisible()
    await expect.element(screen.getByText('Called by Fate')).toBeVisible()
    await screen.getByRole('button', { name: '2 speeches' }).click()
    await expect
      .element(screen.getByText('Let it burn. Ash is a kind of peace.'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'Every son claims one godless people before the next epoch.'
        )
      )
      .toBeVisible()
    await expect.element(screen.getByText('I will not bow.')).toBeVisible()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Yes votes' }))
      .toBeVisible()
    await expect.element(screen.getByText('Motion accepted')).toBeVisible()
    await expect
      .element(screen.getByText('The sons will claim the godless.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Kharun left the hall before the vote ended.'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'A seer dreamed of three brothers arguing under a pale star.'
        )
      )
      .toBeVisible()
  })
})

describe('pantheon screen', () => {
  it('composes the god panel, epoch box, sons, compare, goals, council, kinship and the world', async () => {
    const { screen, server } = await renderScreen(
      <PantheonScreen />,
      godRoutes()
    )
    await expect.element(screen.getByText('Pantheon · 4 sons')).toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'Aeron' }))
      .toBeVisible()
    await expect.element(screen.getByText('Epoch 12').first()).toBeVisible()
    await expect.element(screen.getByText('Compare cards')).toBeVisible()
    await expect
      .element(screen.getByText('Council of the Gods').first())
      .toBeVisible()
    await expect
      .element(
        screen
          .getByText(
            'The exiled heir of the drowned city will return to claim the throne beneath the bells.'
          )
          .first()
      )
      .toBeVisible()
    for (const [type, label, count] of [
      ['people', 'People', '6'],
      ['settlement', 'Settlement', '14'],
    ]) {
      const tile = screen.getByRole('link', {
        name: new RegExp(`^${count}\\s*${label}$`),
      })
      await expect.element(tile).toHaveAttribute('href', `/atlas?type=${type}`)
    }
    await expect
      .element(screen.getByText(/Three worlds turn around a pale star/))
      .toBeVisible()
    await expect
      .poll(() => server.callsTo('GET /api/councils').length)
      .toBeGreaterThan(0)
    await expect
      .poll(() => server.callsTo('GET /api/goals').length)
      .toBeGreaterThan(0)
    await expect
      .poll(() => server.callsTo('GET /api/opportunities').length)
      .toBeGreaterThan(0)
  })
})
