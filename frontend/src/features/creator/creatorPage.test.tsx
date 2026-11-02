import { ACCEPTED_ACTION } from '@/test-utils/fakeApi'
import { godData, godRoutes } from '@/test-utils/godRoutes'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { CreatorPage } from './CreatorPage'
import { RevelationDialog } from './RevelationDialog'

const PEOPLES = {
  items: [
    { id: 50, name: 'The Fisher Folk', entity_type: 'people' },
    { id: 60, name: 'The Dune Mirrors', entity_type: 'people' },
  ],
  total: 2,
}

const IMAGES = [
  {
    id: 801,
    node_id: 1,
    path: 'creator/dawn.png',
    url: '/api/media/creator/dawn.png',
    caption: 'The dawn over the sea',
    is_cover: true,
    kind: 'portrait',
    created_at: '2026-01-01T12:00:00+00:00',
  },
]

async function openCreator(overrides: Record<string, unknown> = {}) {
  return renderScreen(
    <CreatorPage />,
    godRoutes({ 'GET /api/entities': PEOPLES, ...overrides })
  )
}

afterEach(() => localStorage.clear())

describe('creator page', () => {
  it('shows the hero with mood, faith, cult, essence and appearance and redraws the likeness', async () => {
    const { screen, server } = await openCreator()
    await expect
      .element(screen.getByRole('heading', { name: 'Aeron' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('The Unwritten Dawn').first())
      .toBeVisible()
    await expect.element(screen.getByText('12.6 faith')).toBeVisible()
    await expect
      .element(screen.getByText('1 community worship', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('186 essence').first()).toBeVisible()
    await expect
      .element(
        screen
          .getByText(
            'A dawn that never finishes rising, with a voice like distant surf.'
          )
          .first()
      )
      .toBeVisible()
    await screen
      .getByRole('button', { name: /Redraw his likeness/ })
      .first()
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/creator/portrait').length)
      .toBe(1)
    await expect
      .element(screen.getByText('The likeness is being redrawn'))
      .toBeVisible()
  })

  it('falls back to the image galleries when the creator cannot be read', async () => {
    const { screen } = await openCreator({
      'GET /api/creator': failure(500, 'The archive is sealed.'),
    })
    await expect
      .element(screen.getByText('The Creator could not be read'))
      .toBeVisible()
    await expect
      .element(screen.getByText('The archive is sealed.'))
      .toBeVisible()
    await expect
      .element(screen.getByText(/map background, landscape and cover/))
      .toBeVisible()
  })

  it('edits the title, appearance, temperament and image prompt', async () => {
    const { screen, server } = await openCreator()
    await screen
      .getByRole('button', { name: 'Edit title, appearance and temperament' })
      .click()
    const title = screen.getByLabelText('Title', { exact: true })
    await title.clear()
    await title.fill('The Patient Dawn')
    await screen.getByLabelText('Temperament').clear()
    await screen.getByRole('button', { name: 'Save', exact: true }).click()
    await expect.poll(() => server.callsTo('PATCH /api/creator').length).toBe(1)
    expect(server.callsTo('PATCH /api/creator')[0].body).toEqual({
      title: 'The Patient Dawn',
      appearance:
        'A dawn that never finishes rising, with a voice like distant surf.',
      temperament: '',
      image_prompt: 'A radiant dawn figure over a dark ocean of stars',
    })
    await expect
      .element(screen.getByText("The Creator's likeness was updated"))
      .toBeVisible()
  })

  it('shows the mood gauges with thresholds, last-epoch inputs and sets the mood by hand', async () => {
    const { screen, server } = await openCreator()
    await expect
      .element(
        screen.getByText(
          'Changes at each epoch end by faith, prayers and silence in the world.'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText(/Last epoch: faith \+2\.5/))
      .toBeVisible()
    await expect
      .element(screen.getByText(/Last epoch: godless communities \+1\.2/))
      .toBeVisible()
    await expect.element(screen.getByText('Acts at 70').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Set the mood yourself' }).click()
    const anger = screen.getByRole('spinbutton', { name: /Anger|Wrath/ })
    await anger.clear()
    await anger.fill('80')
    await screen
      .getByRole('button', { name: 'Set the mood', exact: true })
      .click()
    await expect
      .poll(() => server.callsTo('PUT /api/creator/mood').length)
      .toBe(1)
    const body = server.callsTo('PUT /api/creator/mood')[0].body as Record<
      string,
      number
    >
    expect(body.anger).toBe(80)
    expect(body.contentment).toBe(64)
    expect(body.interest).toBe(71)
    expect(body.loneliness).toBe(38)
  })

  it('lists how each son sees him with unanswered prayers', async () => {
    const { screen } = await openCreator()
    await expect
      .element(screen.getByText('Reputation and passions'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Thalassir' }).first())
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Kharun the Ashen' }).first())
      .toBeVisible()
    await expect.element(screen.getByText('3 unanswered prayers')).toBeVisible()
    await expect
      .element(screen.getByText('1 unanswered prayer', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Read from your recent deeds'))
      .toBeVisible()
  })

  it('declares passions within the rule limit or returns to automatic reading', async () => {
    const { screen, server } = await openCreator()
    await screen
      .getByRole('button', { name: 'Choose your passions yourself' })
      .click()
    await expect.element(screen.getByText('Pick up to 3.')).toBeVisible()
    await screen.getByRole('checkbox', { name: 'Mercy' }).click()
    await screen.getByRole('checkbox', { name: 'Chaos' }).click()
    const declare = screen.getByRole('button', { name: 'Declare my passions' })
    await expect
      .element(declare)
      .toHaveAttribute('aria-description', 'You can pick at most 3 passions.')
    await screen.getByRole('checkbox', { name: 'Chaos' }).click()
    await declare.click()
    await expect
      .poll(() => server.callsTo('PUT /api/creator/passions').length)
      .toBe(1)
    expect(server.callsTo('PUT /api/creator/passions')[0].body).toEqual({
      passions: ['creation', 'order', 'mercy'],
      automatic: false,
    })
    await expect
      .element(screen.getByRole('button', { name: 'Read automatically' }))
      .toHaveAttribute('aria-description', 'Already automatic.')
  })

  it('writes the creator note into canon with a status line', async () => {
    const { screen, server } = await openCreator()
    await expect.element(screen.getByText('In canon')).toBeVisible()
    const note = screen.getByRole('textbox', { name: 'Your own word' })
    await note.fill('No son may unmake the eastern sea.')
    await expect.element(screen.getByText('Not saved')).toBeVisible()
    await screen.getByRole('button', { name: 'Write into canon' }).click()
    await expect
      .poll(() => server.callsTo('PUT /api/creator/note').length)
      .toBe(1)
    expect(server.callsTo('PUT /api/creator/note')[0].body).toEqual({
      text: 'No son may unmake the eastern sea.',
    })
  })

  it('writes his epic and deepens him as background jobs', async () => {
    const { screen, server } = await openCreator()
    await expect
      .element(screen.getByText("No bard has written the Creator's epic"))
      .toBeVisible()
    await screen.getByRole('button', { name: /Write his epic/ }).click()
    await expect
      .poll(() => server.callsTo('POST /api/creator/epic').length)
      .toBe(1)
    await expect
      .element(screen.getByText("The bard is writing the Creator's epic"))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'Before the first star, Aeron dreamed of a sea that remembered.'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('He cannot see the bottom of the oldest sea.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('The dawn owes nothing to the night.'))
      .toBeVisible()
    await screen.getByRole('button', { name: /Deepen again/ }).click()
    await expect
      .poll(() => server.callsTo('POST /api/creator/deepen').length)
      .toBe(1)
  })

  it('shows the cult, the traces and writes a people account about him', async () => {
    const { screen, server } = await openCreator()
    await expect
      .element(
        screen.getByText(/1 community worship him directly · total faith 12\.6/)
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'The Dawn Watchers' }))
      .toBeVisible()
    await expect.element(screen.getByText('Traces of the god')).toBeVisible()
    await expect
      .element(
        screen
          .getByText(
            'Thalassir raised a lighthouse temple over the drowned city.'
          )
          .first()
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('No people tells of Aeron yet'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: "Add or change a people's account" })
      .click()
    await screen.getByRole('combobox', { name: 'People' }).click()
    await screen.getByRole('option', { name: 'The Fisher Folk' }).click()
    await screen
      .getByLabelText('What they tell')
      .fill('He lit the western waters.')
    await screen
      .getByRole('button', { name: 'Write into canon' })
      .last()
      .click()
    await expect.poll(() => server.callsTo('PUT /api/beliefs').length).toBe(1)
    expect(server.callsTo('PUT /api/beliefs')[0].body).toMatchObject({
      people_id: 50,
      son_id: null,
      narrative: 'He lit the western waters.',
    })
  })

  it("shows the god's gallery and the selected world's images", async () => {
    const { screen, server } = await openCreator({
      'GET /api/creator': { ...godData('/api/creator'), images: IMAGES },
    })
    await expect.element(screen.getByText("The god's images")).toBeVisible()
    await expect
      .element(
        screen.getByText('Thessaly Deep: map background, landscape and cover')
      )
      .toBeVisible()
    await expect
      .poll(() => server.callsTo('GET /api/images').length)
      .toBeGreaterThan(0)
  })
})

describe('revelation dialog', () => {
  it('needs content, offers the mechanism only for a law and posts the revelation', async () => {
    const { screen, server } = await renderScreen(
      <RevelationDialog />,
      godRoutes({ 'POST /api/revelations': ACCEPTED_ACTION })
    )
    await screen.getByRole('button', { name: 'Reveal' }).click()
    const reveal = screen
      .getByRole('dialog')
      .getByRole('button', { name: /Reveal/ })
    await expect
      .element(reveal)
      .toHaveAttribute('aria-description', 'Your revelation must have content.')
    await expect.element(screen.getByText('25')).toBeVisible()
    await expect.element(screen.getByLabelText('Mechanism')).toBeVisible()
    await screen.getByRole('combobox', { name: 'Type' }).click()
    await screen.getByRole('option', { name: 'Legend' }).click()
    await expect
      .element(screen.getByLabelText('Mechanism'))
      .not.toBeInTheDocument()
    await screen.getByRole('combobox', { name: 'World' }).click()
    await screen.getByRole('option', { name: 'Thessaly Deep' }).click()
    await screen
      .getByLabelText('Your revelation')
      .fill('A pale star only the dying can see.')
    await reveal.click()
    await expect
      .poll(() => server.callsTo('POST /api/revelations').length)
      .toBe(1)
    expect(server.callsTo('POST /api/revelations')[0].body).toEqual({
      content: 'A pale star only the dying can see.',
      entity_type: 'legend',
      world_id: 1,
      mechanic: null,
    })
    await expect
      .element(screen.getByText('The revelation is descending'))
      .toBeVisible()
  })

  it('is blocked when the creator cannot afford it', async () => {
    const state = godData('/api/state')
    const { screen } = await renderScreen(
      <RevelationDialog />,
      godRoutes({
        'GET /api/state': {
          ...state,
          creator: { ...(state.creator as object), essence: 3 },
        },
      })
    )
    await screen.getByRole('button', { name: 'Reveal' }).click()
    await screen.getByLabelText('Your revelation').fill('Words.')
    await expect
      .element(
        screen.getByRole('dialog').getByRole('button', { name: /Reveal/ })
      )
      .toHaveAttribute('aria-description', '25 essence needed; you have 3.')
  })
})
