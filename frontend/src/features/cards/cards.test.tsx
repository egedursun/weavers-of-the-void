import { worldState } from '@/test-utils/fixtures'
import { type MockRequest, failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { CardsScreen } from './CardsScreen'
import { type CharacterCard } from './api'
import {
  cardFileName,
  deckOf,
  deckTotal,
  drawerOf,
  filtersOf,
  materialOf,
  rankOf,
  statFill,
  statMeta,
  typeLine,
} from './cardModel'
import {
  CARD_RATIO,
  CARD_SPAN,
  CARD_TOP,
  PACK_RATIO,
  PACK_TOP,
  REVEAL_Y,
  beamsOf,
  landingOf,
} from './packModel'
import { everyOpen, everySealed, sealedIn, useCardSeals } from './sealStore'

function card(overrides: Partial<CharacterCard> = {}): CharacterCard {
  return {
    node_id: 7,
    node_kind: 'son',
    entity_type: null,
    name: 'Ilvane',
    title: 'Keeper of the Ford',
    subtype: null,
    rarity: 'epic',
    stars: 3,
    power_level: null,
    level: 4,
    xp: 30,
    domains: ['death'],
    world_id: 1,
    cover: null,
    flavor: 'Patient and slow.',
    headline: [
      { key: 'might', label: 'Might', value: 70, maximum: 100 },
      { key: 'hp', label: 'Life', value: 90, maximum: 120 },
    ],
    stats: [
      { key: 'strength', label: 'Strength', value: 61, maximum: 100 },
      { key: 'faith', label: 'Faith', value: 12, maximum: null },
      {
        key: 'mood_temperament',
        label: 'Temperament',
        value: -1,
        maximum: 100,
      },
    ],
    abilities: [{ name: 'Stillwater', text: 'Calms every river it touches.' }],
    notes: [{ label: 'Fear', text: 'Being forgotten.' }],
    fallen: false,
    born_epoch: 2,
    ended_epoch: null,
    ...overrides,
  }
}

const MORTAL = card({
  node_id: 41,
  node_kind: 'entity',
  entity_type: 'mortal',
  name: 'Corran Vey',
  title: null,
  subtype: 'smith',
  rarity: 'mythic',
  stars: null,
  power_level: 14,
  level: null,
  xp: null,
  domains: [],
  abilities: [],
  notes: [],
  fallen: true,
  ended_epoch: 6,
})

function page(items: CharacterCard[], total = items.length, offset = 0) {
  return {
    items,
    total,
    offset,
    limit: 48,
    decks: [
      { node_kind: 'son', entity_type: null, total: 1 },
      { node_kind: 'entity', entity_type: 'mortal', total: 1 },
    ],
    rarities: [
      { rarity: 'common', total: 0 },
      { rarity: 'uncommon', total: 0 },
      { rarity: 'rare', total: 0 },
      { rarity: 'epic', total: 1 },
      { rarity: 'legendary', total: 0 },
      { rarity: 'mythic', total: 1 },
    ],
    latest_node_id: 41,
  }
}

function openEveryCard() {
  useCardSeals.setState({ openedThrough: 41, turned: [] })
}

beforeEach(() => {
  useCardSeals.setState({ openedThrough: 0, turned: [] })
})

afterEach(() => {
  document.documentElement.classList.remove('reduce-motion')
})

function routes(reply: (request: MockRequest) => unknown) {
  return {
    'GET /api/state': worldState(),
    'GET /api/catalogue': {
      domains: [{ key: 'death', label: 'Death' }],
      entity_types: [{ key: 'mortal', label: 'Mortal' }],
    },
    'GET /api/cards': reply,
  }
}

describe('card model', () => {
  it('turns the chosen deck and state into the query', () => {
    expect(filtersOf(' vey ', 'mortal', 'rare', 3, 'fallen', 'name')).toEqual({
      q: 'vey',
      nodeKind: 'entity',
      entityType: 'mortal',
      rarity: 'rare',
      worldId: 3,
      fallen: true,
      order: 'name',
    })
    expect(filtersOf('', 'all', null, null, 'all', 'power').fallen).toBeNull()
    expect(filtersOf('', 'son', null, null, 'living', 'power')).toMatchObject({
      nodeKind: 'son',
      entityType: null,
      fallen: false,
    })
  })

  it('counts a deck from the served totals', () => {
    const counts = page([]).decks as never
    expect(deckTotal(counts, deckOf('all'))).toBe(2)
    expect(deckTotal(counts, deckOf('mortal'))).toBe(1)
    expect(deckTotal(counts, deckOf('beast'))).toBe(0)
  })

  it('writes the type line, stars, fills and file names', () => {
    expect(typeLine(MORTAL, () => 'Mortal', String)).toBe('Mortal · smith')
    expect(typeLine(card(), String, () => 'Death')).toBe(
      'Child of the Creator · Death'
    )
    expect(materialOf(MORTAL)).toBe('mythic')
    expect(materialOf(card({ node_kind: 'creator', rarity: null }))).toBe(
      'sovereign'
    )
    expect(materialOf(card({ node_kind: 'foreign_god', rarity: null }))).toBe(
      'obsidian'
    )
    expect(rankOf(MORTAL)).toEqual({ value: 14, label: 'Power level' })
    expect(
      statMeta({ key: 'might', label: 'Might', value: 1, maximum: 100 }, true)
        .group
    ).toBe('Soul')
    expect(
      statMeta(
        { key: 'strength', label: 'Strength', value: 1, maximum: 100 },
        false
      )
    ).toMatchObject({ group: 'Traits', effect: null, abbr: 'STR' })
    expect(statFill({ key: 'x', label: 'X', value: -40, maximum: 100 })).toBe(
      0.4
    )
    expect(statFill({ key: 'x', label: 'X', value: 3, maximum: null })).toBe(
      null
    )
    expect(cardFileName(card({ name: 'Élodie Brûlé the Old' }), 'back')).toBe(
      'elodie-brule-the-old-back.png'
    )
    expect(drawerOf(MORTAL)).toEqual({ kind: 'entity', id: '41' })
    expect(drawerOf(card({ node_kind: 'creator' }))).toEqual({
      kind: 'creator',
    })
  })
})

describe('card seals', () => {
  it('keeps unopened cards sealed and opens through the newest card', () => {
    const fresh = { openedThrough: 0, turned: [] }
    expect(sealedIn(fresh, 7)).toBe(true)
    expect(everySealed(fresh)).toBe(true)
    expect(everyOpen(fresh, 41)).toBe(false)
    expect(everyOpen(fresh, null)).toBe(true)
    useCardSeals.getState().open(7)
    expect(sealedIn(useCardSeals.getState(), 7)).toBe(false)
    expect(sealedIn(useCardSeals.getState(), 41)).toBe(true)
    useCardSeals.getState().openAll(41)
    const opened = useCardSeals.getState()
    expect(opened.turned).toEqual([])
    expect(sealedIn(opened, 41)).toBe(false)
    expect(sealedIn(opened, 42)).toBe(true)
    expect(everyOpen(opened, 41)).toBe(true)
    expect(everyOpen(opened, 50)).toBe(false)
    useCardSeals.getState().seal(7)
    expect(sealedIn(useCardSeals.getState(), 7)).toBe(true)
    expect(everyOpen(useCardSeals.getState(), 41)).toBe(false)
    useCardSeals.getState().open(7)
    expect(useCardSeals.getState().turned).toEqual([])
    useCardSeals.getState().sealAll()
    expect(everySealed(useCardSeals.getState())).toBe(true)
  })
})

describe('pack staging', () => {
  it('lands the opened card on the centre of the light at every stage size', () => {
    for (const [width, height, pack] of [
      [1000, 600, 220],
      [390, 640, 230],
      [1400, 760, 280],
    ]) {
      const landing = landingOf(width, height, pack)
      const packHeight = pack * PACK_RATIO
      const cardHeight = pack * CARD_SPAN * CARD_RATIO
      const laidOut =
        height * PACK_TOP -
        packHeight / 2 +
        packHeight * CARD_TOP +
        cardHeight / 2
      expect(laidOut + landing.dy).toBeCloseTo(height * REVEAL_Y, 6)
      expect(landing.height * landing.scale).toBeLessThanOrEqual(
        height * 0.7 + 1e-6
      )
      expect(landing.width * landing.scale).toBeLessThanOrEqual(
        width * 0.84 + 1e-6
      )
    }
  })

  it('draws soft beams in order around the whole circle', () => {
    let seed = 7
    const random = () => {
      seed = (seed * 16807) % 2147483647
      return seed / 2147483647
    }
    const beams = beamsOf(random, 26, [0.5, 2.6], ['--beam-strong'])
    const angles = [...beams.matchAll(/(-?[\d.]+)deg/g)].map((match) =>
      Number(match[1])
    )
    expect(beams.startsWith('conic-gradient(from 0deg, transparent 0deg')).toBe(
      true
    )
    expect(angles.slice(1)).toEqual([...angles.slice(1)].sort((a, b) => a - b))
    expect(Math.min(...angles.slice(1))).toBeGreaterThanOrEqual(0)
    expect(Math.max(...angles)).toBe(360)
    expect(beams.match(/var\(--beam-strong\)/g)).toHaveLength(26)
  })
})

describe('CardsScreen', () => {
  it('shows unopened cards as sealed packs and opens or seals them all', async () => {
    const { screen } = await renderScreen(
      <CardsScreen />,
      routes(() => page([card(), MORTAL]))
    )
    await expect
      .element(
        screen.getByRole('button', { name: 'Open a sealed pack' }).first()
      )
      .toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Open a sealed pack' }).all()
    ).toHaveLength(2)
    await expect.element(screen.getByText(/2 sealed packs/)).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Seal every pack' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Open every pack' }).click()
    await expect
      .element(
        screen.getByRole('button', { name: 'Inspect the card of Ilvane' })
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Open every pack' }))
      .toBeDisabled()
    await screen
      .getByRole('button', { name: 'Seal the card of Ilvane back in its pack' })
      .click()
    await expect
      .element(screen.getByRole('button', { name: 'Open a sealed pack' }))
      .toBeVisible()
    await expect.element(screen.getByText(/1 sealed pack$/)).toBeVisible()
    await screen.getByRole('button', { name: 'Seal every pack' }).click()
    await expect
      .poll(
        () =>
          screen.getByRole('button', { name: 'Open a sealed pack' }).all()
            .length
      )
      .toBe(2)
  })

  it('tears a sealed pack open in the inspector and keeps it open', async () => {
    document.documentElement.classList.add('reduce-motion')
    const { screen } = await renderScreen(
      <CardsScreen />,
      routes(() => page([card(), MORTAL]))
    )
    await screen
      .getByRole('button', { name: 'Open a sealed pack' })
      .first()
      .click()
    const dialog = screen.getByRole('dialog')
    await expect
      .element(dialog.getByRole('heading', { name: 'A sealed pack' }))
      .toBeVisible()
    await dialog.getByRole('button', { name: 'Open the pack' }).click()
    await expect
      .element(dialog.getByRole('button', { name: 'Read the whole card' }))
      .toBeVisible()
    await expect
      .element(dialog.getByRole('heading', { name: 'Ilvane' }))
      .toBeVisible()
    expect(sealedIn(useCardSeals.getState(), 7)).toBe(false)
    await expect
      .element(dialog.getByRole('button', { name: 'Open the next pack' }))
      .toBeEnabled()
    await dialog.getByRole('button', { name: 'Read the whole card' }).click()
    await expect
      .element(
        dialog.getByText('Calms every river it touches.', { exact: true })
      )
      .toBeVisible()
    await dialog
      .getByRole('button', { name: 'Seal it back in its pack' })
      .click()
    await expect
      .element(dialog.getByRole('heading', { name: 'A sealed pack' }))
      .toBeVisible()
    expect(sealedIn(useCardSeals.getState(), 7)).toBe(true)
  })

  it('lays out the cards, filters the deck and searches by name', async () => {
    openEveryCard()
    const { screen, server } = await renderScreen(
      <CardsScreen />,
      routes((request) =>
        request.query.get('entity_type') === 'mortal'
          ? page([MORTAL])
          : page([card(), MORTAL])
      )
    )
    await expect.element(screen.getByText('Ilvane').first()).toBeVisible()
    await expect.element(screen.getByText('† Corran Vey').first()).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Mortals · 1' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Mythic · 1' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('region', { name: 'The divine' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('region', { name: 'Souls of the worlds' }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Mythic · 1' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/cards')
          .some((call) => call.query.get('rarity') === 'mythic')
      )
      .toBe(true)
    await screen.getByRole('button', { name: 'Mortals · 1' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/cards')
          .some((call) => call.query.get('entity_type') === 'mortal')
      )
      .toBe(true)
    await userEvent.fill(
      screen.getByRole('searchbox', { name: 'Find a card' }),
      'vey'
    )
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/cards')
          .some((call) => call.query.get('q') === 'vey')
      )
      .toBe(true)
  })

  it('opens a card to read every value and walks the deck', async () => {
    openEveryCard()
    const { screen } = await renderScreen(
      <CardsScreen />,
      routes(() => page([card(), MORTAL]))
    )
    await screen
      .getByRole('button', { name: 'Inspect the card of Ilvane' })
      .click()
    const dialog = screen.getByRole('dialog')
    await expect
      .element(
        dialog.getByText('Calms every river it touches.', { exact: true })
      )
      .toBeVisible()
    await expect
      .element(dialog.getByText('Being forgotten.', { exact: true }))
      .toBeVisible()
    await expect
      .element(dialog.getByText('Faith', { exact: true }).last())
      .toBeVisible()
    const values = dialog.getByRole('region', { name: 'Every value' })
    for (const label of ['Strength', 'Temperament'])
      expect(
        values
          .getByText(label, { exact: true })
          .last()
          .element()
          .closest('.surface-sheen')
      ).not.toBeNull()
    await dialog.getByRole('button', { name: 'Next card' }).click()
    await expect
      .element(dialog.getByRole('heading', { name: 'Corran Vey' }))
      .toBeVisible()
    await userEvent.keyboard('{Escape}')
    await screen.getByRole('radio', { name: 'Swipe through a deck' }).click()
    await expect.element(screen.getByText('Card 1 of 2')).toBeVisible()
    await screen.getByRole('button', { name: 'Next card' }).click()
    await expect.element(screen.getByText('Card 2 of 2')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Next card' }))
      .toBeDisabled()
  })

  it('says when nothing matches and when the cards cannot be drawn', async () => {
    const { screen } = await renderScreen(
      <CardsScreen />,
      routes((request) =>
        request.query.get('q') ? page([]) : failure(500, 'The deck is lost.')
      )
    )
    await expect.element(screen.getByText('The deck is lost.')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Try again' }))
      .toBeVisible()
    await userEvent.fill(
      screen.getByRole('searchbox', { name: 'Find a card' }),
      'zz'
    )
    await expect.element(screen.getByText('No card matches')).toBeVisible()
  })
})
