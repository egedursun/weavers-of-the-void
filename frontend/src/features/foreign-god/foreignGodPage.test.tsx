import { godData, godRoutes } from '@/test-utils/godRoutes'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { ForeignGodPage } from './ForeignGodPage'
import { PlaceForeignGodForm } from './PlaceForeignGodForm'

const DETAIL = godData('/api/foreign-gods/3')
const GOD = DETAIL.god as Record<string, unknown>
const CHRONICLE_LINE = {
  id: 95,
  epoch: 11,
  year: 340,
  kind: 'omen',
  son_id: null,
  world_id: 2,
  text: 'Ysmera turned in her sleep and the glass dunes sang.',
  template_key: null,
  created_at: '2026-01-01T12:00:00+00:00',
}
const DEPTH = {
  history: 'She was the moon before the moon.',
  names: [],
  secrets: ['She remembers the first eclipse.'],
  fears: ['Being reflected wrongly.'],
  taboos: [],
  gifts: [],
  desire: 'To see her face in still water again.',
  sayings: [],
  rumours: [],
  hidden_truth: 'She is two gods sharing one name.',
  view_of_pantheon: 'Wary.',
  worship: 'Mirrors buried in sand.',
  epoch: 10,
}

function detail(
  god: Record<string, unknown> = {},
  extra: Record<string, unknown> = {}
) {
  return {
    ...DETAIL,
    world: { id: 2, name: 'The Glass Wastes' },
    chronicle: [CHRONICLE_LINE],
    ...extra,
    god: { ...GOD, ...god },
  }
}

async function openGod(
  god: Record<string, unknown> = {},
  extra: Record<string, unknown> = {}
) {
  return renderScreen(
    <ForeignGodPage id='3' />,
    godRoutes({
      'GET /api/foreign-gods/3': detail(god, extra),
      'POST /api/foreign-gods/3/deepen': {
        action: 'deepen',
        message: 'Deepening',
        job_id: null,
      },
    })
  )
}

afterEach(() => localStorage.clear())

describe('foreign god page', () => {
  it('shows the hero with world, status, domains, power, faith, contact, epochs and awakening', async () => {
    const { screen } = await openGod({ defeated_epoch: 7 })
    await expect
      .element(screen.getByText('Foreign god › The Glass Wastes'))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('heading', { name: 'Ysmera of the Hollow Moon' })
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('She Who Waits Beneath the Glass'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Moon', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText('Glass', { exact: true }).first())
      .toBeVisible()
    await expect.element(screen.getByText('Power 54')).toBeVisible()
    await expect.element(screen.getByText('6.5 faith')).toBeVisible()
    await expect.element(screen.getByText('No contact yet')).toBeVisible()
    await expect.element(screen.getByText('Since Epoch 2')).toBeVisible()
    await expect.element(screen.getByText('Defeated in Epoch 7')).toBeVisible()
    await expect.element(screen.getByText('Awakening')).toBeVisible()
    await expect.element(screen.getByText(/stir the sleeper/)).toBeVisible()
  })

  it('marks a dead god and the epoch of his death', async () => {
    const { screen } = await openGod({
      status: 'dead',
      death_epoch: 9,
      contacted: true,
    })
    await expect
      .element(
        screen.getByRole('heading', { name: '† Ysmera of the Hollow Moon' })
      )
      .toBeVisible()
    await expect.element(screen.getByText('Died in Epoch 9')).toBeVisible()
    await expect
      .element(screen.getByText('Made contact with the pantheon'))
      .toBeVisible()
  })

  it('links his world in Cosmos, the world guide and the book entry', async () => {
    const { screen, router } = await openGod()
    await expect
      .element(screen.getByRole('link', { name: 'Show the world in Cosmos' }))
      .toHaveAttribute('href', '/cosmos?world=2')
    await expect
      .element(screen.getByRole('link', { name: 'Open in the book' }))
      .toHaveAttribute('href', '/api/book#foreign-god-3')
    await screen.getByRole('button', { name: 'World guide' }).click()
    await expect
      .poll(() => JSON.stringify(router.state.location.search))
      .toContain('world-guide')
  })

  it('deepens him and shows the depth, keeping hand-written fields', async () => {
    const { screen, server } = await openGod({ depth: DEPTH })
    await expect
      .element(screen.getByText('She was the moon before the moon.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('She remembers the first eclipse.'))
      .toBeVisible()
    await expect
      .element(screen.getByText(/you wrote by hand are kept/))
      .toBeVisible()
    await screen.getByRole('button', { name: /Deepen again/ }).click()
    await expect
      .poll(() => server.callsTo('POST /api/foreign-gods/3/deepen').length)
      .toBe(1)
  })

  it('offers deepening when he has no depth yet', async () => {
    const { screen } = await openGod()
    await expect.element(screen.getByText('Not deepened yet')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /^Deepen/ }))
      .toBeVisible()
  })

  it('lists worshippers and the sons he encountered', async () => {
    const { screen } = await openGod()
    await expect
      .element(screen.getByRole('link', { name: 'The Dune Mirrors' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('People · since Epoch 3'))
      .toBeVisible()
    await expect.element(screen.getByText('Sons encountered')).toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: /^Vaelorithan/ }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Currently on this world'))
      .toBeVisible()
  })

  it('shows an empty worshipper state', async () => {
    const { screen } = await openGod({}, { worshippers: [], sons_here: [] })
    await expect
      .element(screen.getByText('No community worships this god now'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Sons encountered'))
      .not.toBeInTheDocument()
  })

  it('shows his images with the image prompt and his chronicle mentions', async () => {
    const { screen, server } = await openGod({
      image_prompt: 'A moon goddess in glass',
    })
    await expect
      .element(screen.getByRole('heading', { name: 'Images' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('A moon goddess in glass').first())
      .toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'In the chronicle' }))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Ysmera turned in her sleep and the glass dunes sang.')
      )
      .toBeVisible()
    expect(server.callsTo('PATCH /api/foreign-gods/3').length).toBe(0)
  })

  it('edits name, title, domains, attitude, power, status, contact, description and prompt', async () => {
    const { screen, server } = await openGod()
    await screen
      .getByRole('button', {
        name: 'Edit name, title, attitude, power and status',
      })
      .click()
    const name = screen.getByRole('textbox', { name: 'Name', exact: true })
    await name.clear()
    await name.fill('Ysmera the Waking')
    const power = screen.getByRole('spinbutton', { name: 'Power' })
    await power.clear()
    await power.fill('60')
    await screen.getByLabelText('Contact made with the pantheon').click()
    await screen
      .getByRole('button', { name: 'Save', exact: true })
      .first()
      .click()
    await expect
      .poll(() => server.callsTo('PATCH /api/foreign-gods/3').length)
      .toBe(1)
    expect(server.callsTo('PATCH /api/foreign-gods/3')[0].body).toEqual({
      name: 'Ysmera the Waking',
      title: 'She Who Waits Beneath the Glass',
      domain_primary: 'moon',
      domain_secondary: 'glass',
      stance: -22,
      power: 60,
      status: 'asleep',
      contacted: true,
      description:
        'An old goddess of the glass wastes who sleeps beneath the dunes and dreams in reflections.',
      image_prompt: '',
    })
  })

  it('refuses to save without a name', async () => {
    const { screen } = await openGod()
    await screen
      .getByRole('button', {
        name: 'Edit name, title, attitude, power and status',
      })
      .click()
    await screen.getByRole('textbox', { name: 'Name', exact: true }).clear()
    await expect
      .element(
        screen.getByRole('button', { name: 'Save', exact: true }).first()
      )
      .toHaveAttribute('aria-description', 'A name is needed.')
  })

  it('edits stats, powers (blank name removes, trailing row adds), personality, existence and depth', async () => {
    const { screen, server } = await openGod({ depth: DEPTH })
    await screen
      .getByRole('button', {
        name: 'Edit stats, powers, personality, existence and depth',
      })
      .click()
    const wisdom = screen.getByRole('spinbutton', { name: 'Wisdom' })
    await wisdom.clear()
    await wisdom.fill('75')
    await screen.getByRole('textbox', { name: 'Power 1 name' }).clear()
    await screen
      .getByRole('textbox', { name: 'Power 2 name' })
      .fill('Glass Echo')
    await screen.getByRole('combobox', { name: 'Power 2 effect' }).click()
    await screen.getByRole('option').first().click()
    await screen
      .getByRole('textbox', { name: 'Power 2 description' })
      .fill('Repeats a spell.')
    await expect
      .element(screen.getByRole('textbox', { name: 'Power 3 name' }))
      .toBeVisible()
    await screen
      .getByRole('textbox', { name: 'Appearance' })
      .fill('A woman of moonlit glass.')
    await screen.getByRole('textbox', { name: 'True name' }).fill('Ys')
    await screen.getByRole('textbox', { name: 'Secrets' }).fill('One\nTwo')
    await screen
      .getByRole('button', { name: 'Save', exact: true })
      .last()
      .click()
    await expect
      .poll(() => server.callsTo('PATCH /api/foreign-gods/3').length)
      .toBe(1)
    const body = server.callsTo('PATCH /api/foreign-gods/3')[0].body as Record<
      string,
      Record<string, unknown> & unknown[]
    >
    expect(body.stats.wisdom).toBe(75)
    expect(body.powers).toHaveLength(1)
    expect(body.powers[0]).toMatchObject({
      name: 'Glass Echo',
      description: 'Repeats a spell.',
    })
    expect(body.personality.appearance).toBe('A woman of moonlit glass.')
    expect(body.existence.true_name).toBe('Ys')
    expect(body.depth.secrets).toEqual(['One', 'Two'])
    expect(body.depth.history).toBe('She was the moon before the moon.')
  })
})

describe('place an old god', () => {
  it('places a god on a chosen world with domains, attitude and dice power', async () => {
    const { screen, server } = await renderScreen(
      <PlaceForeignGodForm />,
      godRoutes({
        'POST /api/foreign-gods': {
          action: 'foreign:place',
          message: 'Placed',
          job_id: null,
        },
      })
    )
    await screen.getByRole('button', { name: 'Place an old god' }).click()
    const place = screen.getByRole('button', { name: /Place the god/ })
    await expect
      .element(place)
      .toHaveAttribute('aria-description', 'A name is needed.')
    await screen
      .getByRole('textbox', { name: 'Name', exact: true })
      .fill('Orrun')
    await screen
      .getByRole('textbox', { name: 'Title' })
      .fill('The Drowned Bell')
    await screen.getByRole('combobox', { name: 'World' }).click()
    await screen.getByRole('option', { name: /The Glass Wastes/ }).click()
    await screen.getByRole('combobox', { name: 'First domain' }).click()
    await screen.getByRole('option', { name: 'Sea', exact: true }).click()
    await screen.getByRole('combobox', { name: 'Second domain' }).click()
    await screen.getByRole('option', { name: 'Oath', exact: true }).click()
    const stance = screen.getByRole('spinbutton', { name: 'Attitude' })
    await stance.clear()
    await stance.fill('-10')
    await screen
      .getByRole('textbox', { name: 'Image prompt' })
      .fill('  A drowned bell under green water  ')
    await place.click()
    await expect
      .poll(() => server.callsTo('POST /api/foreign-gods').length)
      .toBe(1)
    expect(server.callsTo('POST /api/foreign-gods')[0].body).toEqual({
      world_id: 2,
      name: 'Orrun',
      title: 'The Drowned Bell',
      description: null,
      domain_primary: 'sea',
      domain_secondary: 'oath',
      stance: -10,
      power: null,
      image_prompt: 'A drowned bell under green water',
    })
    await expect
      .element(
        screen.getByText(
          'An old god takes a place in the world and is being deepened'
        )
      )
      .toBeVisible()
  })
})
