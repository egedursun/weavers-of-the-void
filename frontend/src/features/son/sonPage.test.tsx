import { godRoutes } from '@/test-utils/godRoutes'
import { type MockRoutes } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { toast } from 'sonner'
import { afterEach, describe, expect, it } from 'vitest'
import { SonPage } from './SonPage'

const NAMES = [
  { id: 42, name: 'Oskar', kind: 'entity', type: 'settlement', world_id: 1 },
  {
    id: 50,
    name: 'The Fisher Folk',
    kind: 'entity',
    type: 'people',
    world_id: 1,
  },
]
const PEOPLES = {
  items: [{ id: 50, name: 'The Fisher Folk', entity_type: 'people' }],
  total: 1,
}
const ACCEPTED = {
  action: 'done',
  message: 'Done.',
  essence_spent: 0,
  essence_gained: 0,
  job_id: null,
}

function routes(extra: MockRoutes = {}) {
  return godRoutes({
    'GET /api/names': NAMES,
    'GET /api/entities': PEOPLES,
    'PUT /api/beliefs': ACCEPTED,
    'POST /api/links': ACCEPTED,
    'DELETE /api/links/{id}': ACCEPTED,
    'POST /api/actions/{key}': ACCEPTED,
    ...extra,
  })
}

async function openSon(id: number, extra: MockRoutes = {}) {
  return renderScreen(<SonPage id={String(id)} />, routes(extra))
}

async function confirm(
  screen: Awaited<ReturnType<typeof openSon>>['screen'],
  label: string
) {
  await screen
    .getByRole('alertdialog')
    .getByRole('button', { name: label })
    .click()
}

function heroStats() {
  return Object.fromEntries(
    Array.from(
      document.querySelectorAll('header [data-domain="mini-stat"] data'),
      (stat) => [
        stat.nextElementSibling?.textContent ?? '',
        stat.getAttribute('value'),
      ]
    )
  )
}

afterEach(() => localStorage.clear())

describe('son hero', () => {
  it('shows class, name, title, domains, vitals, existence, actions, world, anchor and plan', async () => {
    const { screen } = await openSon(7)
    await expect
      .element(screen.getByRole('heading', { name: 'Thalassir', exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('★★★')).toBeVisible()
    await expect
      .element(screen.getByText('Level 5', { exact: true }))
      .toBeVisible()
    await expect.poll(heroStats).toEqual({
      Life: '120/140',
      Essence: '64/150',
      Faith: '18.4',
      Fame: '46',
      Solid: '72',
      Actions: '3',
      'Power cap': '7',
    })
    await expect
      .element(screen.getByText('Anchor', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Oskar' }).first())
      .toBeVisible()
    await expect
      .element(
        screen
          .getByText(/Raise a lighthouse temple on the western cliffs/)
          .first()
      )
      .toBeVisible()
  })

  it('marks fading for a forgotten son', async () => {
    const { screen } = await openSon(9)
    await expect
      .element(screen.getByText(/Being forgotten · fades in \d+ epochs/))
      .toBeVisible()
  })

  it('links the print page and toggles the bookmark', async () => {
    const { screen } = await openSon(7)
    await expect
      .element(screen.getByRole('link', { name: 'Print page' }))
      .toHaveAttribute('href', '/api/book?son_id=7')
    const bookmark = screen.getByRole('button', { name: 'Bookmark' })
    await expect.element(bookmark).toHaveAttribute('aria-pressed', 'false')
    await bookmark.click()
    await expect
      .element(screen.getByRole('button', { name: 'Bookmarked' }))
      .toHaveAttribute('aria-pressed', 'true')
  })
})

describe('dead son', () => {
  it('shows bones, cults, devotion, earliest return and loyal communities and resurrects by hand', async () => {
    const { screen, server } = await openSon(10, {
      'POST /api/sons/10/resurrect': ACCEPTED,
    })
    await expect.element(screen.getByText('Mirel died · Epoch 9')).toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: /^The remains of/ }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Resurrection devotion'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Earliest return in Epoch 12'))
      .toBeVisible()
    await expect.element(screen.getByText('3 epochs remaining')).toBeVisible()
    await expect
      .element(screen.getByText('18 followers · devotion 40'))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('link', {
          name: 'The Brine-Singers of the Ninth Shore',
        })
      )
      .toBeVisible()
    await expect
      .element(screen.getByText(/resurrection cult that gathers devotion/))
      .toBeVisible()
    await screen
      .getByRole('button', { name: /Resurrect by your own hand/ })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/sons/10/resurrect').length)
      .toBe(1)
  })
})

describe('hand of god on the son page', () => {
  it('strikes with lightning and exiles after confirming', async () => {
    const { screen, server } = await openSon(7)
    await screen.getByRole('button', { name: /^Lightning/ }).click()
    await confirm(screen, 'Lightning')
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/punish').length)
      .toBe(1)
    expect(server.callsTo('POST /api/sons/7/punish')[0].body).toEqual({
      kind: 'lightning',
    })
    await screen.getByRole('button', { name: /^Exile/ }).click()
    await confirm(screen, 'Exile')
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/punish').length)
      .toBe(2)
    expect(server.callsTo('POST /api/sons/7/punish')[1].body).toEqual({
      kind: 'exile',
    })
  })

  it('chains a son who has not acted this epoch', async () => {
    const { screen, server } = await openSon(7)
    await screen.getByRole('button', { name: /^Chain this epoch/ }).click()
    await confirm(screen, 'Chain this epoch')
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/punish').length)
      .toBe(1)
    expect(server.callsTo('POST /api/sons/7/punish')[0].body).toEqual({
      kind: 'chain',
    })
  })

  it('suppresses a rebellion after confirming or forgives it, and pardons the chained', async () => {
    const { screen, server } = await openSon(9)
    await expect
      .element(screen.getByText('In rebellion against his father'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: /^Suppress the rebellion/ })
      .click()
    await confirm(screen, 'Suppress the rebellion')
    await expect
      .poll(() => server.callsTo('POST /api/sons/9/punish').length)
      .toBe(1)
    expect(server.callsTo('POST /api/sons/9/punish')[0].body).toEqual({
      kind: 'suppress',
    })
    await screen.getByRole('button', { name: 'Forgive' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/sons/9/punish').length)
      .toBe(2)
    expect(server.callsTo('POST /api/sons/9/punish')[1].body).toEqual({
      kind: 'pardon',
    })
    await expect
      .element(screen.getByRole('button', { name: 'Pardon' }))
      .toBeVisible()
  })

  it('demotes one class and rips out a chosen power', async () => {
    const { screen, server } = await openSon(7)
    await screen.getByRole('button', { name: /^Lower to Epic/ }).click()
    await confirm(screen, 'Lower to Epic')
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/demote').length)
      .toBe(1)
    await screen.getByRole('combobox', { name: 'Power to rip out' }).click()
    await screen.getByRole('option', { name: 'Bell of Return' }).click()
    await screen.getByRole('button', { name: /^Rip out the power/ }).click()
    await confirm(screen, 'Rip out the power')
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/strip-power').length)
      .toBe(1)
    expect(server.callsTo('POST /api/sons/7/strip-power')[0].body).toEqual({
      slot: 1,
    })
  })

  it('sends him to another world under the distribution protection note', async () => {
    const { screen, server } = await openSon(7)
    await expect
      .element(screen.getByText(/protected from it for 3 epochs/))
      .toBeVisible()
    const send = screen.getByRole('button', { name: 'Send to world' })
    await expect
      .element(send)
      .toHaveAttribute('aria-description', 'Pick another world.')
    await screen.getByRole('combobox', { name: 'World to send him to' }).click()
    await screen.getByRole('option', { name: /^The Glass Wastes/ }).click()
    await send.click()
    await expect
      .poll(() => server.callsTo('PUT /api/sons/7/world').length)
      .toBe(1)
    expect(server.callsTo('PUT /api/sons/7/world')[0].body).toEqual({
      world_id: 2,
    })
  })
})

describe('son sections', () => {
  it("lists this epoch's opportunities as the server phrases them", async () => {
    const { screen } = await openSon(7)
    await expect
      .element(screen.getByRole('heading', { name: 'Opportunities' }))
      .toBeVisible()
    await expect.element(screen.getByText(/RIVAL SIBLINGS: /)).toBeVisible()
    await expect
      .element(screen.getByText(/Communities that worship no one/))
      .toBeVisible()
  })

  it('shows how he sees his father and nudges love within the manual cap', async () => {
    const { screen, server } = await openSon(7)
    await expect
      .element(screen.getByRole('heading', { name: 'How he sees his father' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Last contact: Epoch 11'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          /Your nudges: love 10, fear 0, forgottenness 0; 60% of each remains/
        )
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Win his heart' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/reputation-nudge').length)
      .toBe(1)
    expect(server.callsTo('POST /api/sons/7/reputation-nudge')[0].body).toEqual(
      { love: 10, fear: 0, forgotten: 0 }
    )
    await screen.getByRole('button', { name: 'Remind him of you' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/reputation-nudge').length)
      .toBe(2)
    expect(server.callsTo('POST /api/sons/7/reputation-nudge')[1].body).toEqual(
      { love: 0, fear: 0, forgotten: -15 }
    )
  })

  it('shows his epic and rewrites it', async () => {
    const { screen, server } = await openSon(7)
    await expect
      .element(screen.getByText('The Song of the Drowned Bells'))
      .toBeVisible()
    await expect.element(screen.getByText('The First Oath')).toBeVisible()
    await screen.getByRole('button', { name: /Rewrite epic/ }).click()
    await expect
      .poll(() => server.callsTo('POST /api/sons/7/epic').length)
      .toBe(1)
  })

  it('shows three power slots with effect, parameter and locked styling', async () => {
    const { screen } = await openSon(7)
    const powers = screen.getByRole('heading', { name: 'Powers', exact: true })
    await expect.element(powers).toBeVisible()
    await expect
      .element(screen.getByText('Locked', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Duels on his chosen stat favour him.').first())
      .toBeVisible()
  })

  it('shows his existence and identity', async () => {
    const { screen } = await openSon(7)
    await expect.element(screen.getByText('Tide and memory')).toBeVisible()
    await expect
      .element(screen.getByText('A voice in the bell towers of drowned cities'))
      .toBeVisible()
    await expect.element(screen.getByText('Ul-Varesh')).toBeVisible()
    await expect
      .element(
        screen.getByText('Binding the restless sea to an oath it cannot break.')
      )
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'He once let a city drown to win a wager with his brother.'
        )
      )
      .toBeVisible()
  })

  it('edits name and plan with a PATCH', async () => {
    const { screen, server } = await openSon(7)
    await screen
      .getByRole('button', {
        name: 'Edit name, plan, personality, stats and resources',
      })
      .click()
    const name = screen.getByRole('textbox', { name: 'Name', exact: true })
    await name.clear()
    await name.fill('Thalassir the Bellwarden')
    await screen.getByRole('button', { name: 'Save', exact: true }).click()
    await expect.poll(() => server.callsTo('PATCH /api/sons/7').length).toBe(1)
    expect(server.callsTo('PATCH /api/sons/7')[0].body).toMatchObject({
      name: 'Thalassir the Bellwarden',
    })
  })

  it('adjusts one stat, passion or resource at a time from the stats section', async () => {
    const { screen, server } = await openSon(7)
    await screen.getByRole('button', { name: 'Adjust stats' }).click()
    const might = screen.getByRole('spinbutton', { name: 'Might (1–100)' })
    await might.clear()
    await might.fill('101')
    await expect
      .element(screen.getByRole('button', { name: 'Set Might' }))
      .toBeDisabled()
    await might.clear()
    await might.fill('97')
    await screen.getByRole('button', { name: 'Set Might' }).click()
    await expect.poll(() => server.callsTo('PATCH /api/sons/7').length).toBe(1)
    expect(server.callsTo('PATCH /api/sons/7')[0].body).toEqual({
      stats: { might: 97 },
    })
    const wrath = screen.getByRole('spinbutton', { name: 'Wrath (0–100)' })
    await wrath.clear()
    await wrath.fill('3')
    await screen.getByRole('button', { name: 'Set Wrath' }).click()
    await expect.poll(() => server.callsTo('PATCH /api/sons/7').length).toBe(2)
    expect(server.callsTo('PATCH /api/sons/7')[1].body).toEqual({
      passions: { wrath: 3 },
    })
    const xp = screen.getByRole('spinbutton', { name: 'Experience (0+)' })
    await xp.clear()
    await xp.fill('1234')
    await screen.getByRole('button', { name: 'Set Experience' }).click()
    await expect.poll(() => server.callsTo('PATCH /api/sons/7').length).toBe(3)
    expect(server.callsTo('PATCH /api/sons/7')[2].body).toEqual({
      resources: { xp: 1234 },
    })
  })

  it('shows peoples accounts of him and writes one with the son fixed', async () => {
    const { screen, server } = await openSon(7)
    await expect.element(screen.getByText('"Bellfather"')).toBeVisible()
    await expect
      .element(
        screen.getByText('He rings the drowned bells to warn us of storms.')
      )
      .toBeVisible()
    await screen
      .getByRole('button', { name: "Add or change a people's account" })
      .click()
    await screen.getByRole('combobox', { name: 'People' }).click()
    await screen.getByRole('option', { name: 'The Fisher Folk' }).click()
    await screen.getByLabelText('What they tell').fill('He counts the drowned.')
    await screen.getByRole('button', { name: 'Write into canon' }).click()
    await expect.poll(() => server.callsTo('PUT /api/beliefs').length).toBe(1)
    expect(server.callsTo('PUT /api/beliefs')[0].body).toMatchObject({
      people_id: 50,
      son_id: 7,
      narrative: 'He counts the drowned.',
    })
  })

  it('shows stats, passions and resources with experience to the next level', async () => {
    const { screen } = await openSon(7)
    await expect
      .element(screen.getByRole('heading', { name: 'Stats', exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'Passions', exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'Resources', exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Experience')).toBeVisible()
    await expect
      .element(screen.getByText('Sanity', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText(/anchor living feed existence/))
      .toBeVisible()
  })

  it('saves his portrait prompt from the images section', async () => {
    const { screen, server } = await openSon(7, {
      'PUT /api/sons/7/image-prompt': { ok: true },
    })
    const prompt = screen.getByRole('textbox', { name: 'Portrait prompt' })
    await expect
      .element(prompt)
      .toHaveValue('A storm-lit figure among drowned bell towers, oil painting')
    await prompt.fill('A bell warden of salt')
    await screen.getByRole('button', { name: 'Save prompt' }).click()
    await expect
      .poll(() => server.callsTo('PUT /api/sons/7/image-prompt').length)
      .toBe(1)
    expect(server.callsTo('PUT /api/sons/7/image-prompt')[0].body).toEqual({
      image_prompt: 'A bell warden of salt',
    })
  })

  it('breaks a bond after confirming and creates a new one', async () => {
    const { screen, server } = await openSon(7)
    await expect
      .element(screen.getByRole('heading', { name: 'His hand in the world' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('He shelters the drowned city.'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Break' }).first().click()
    await confirm(screen, 'Break')
    await expect
      .poll(() => server.callsTo('DELETE /api/links/{id}').length)
      .toBe(1)
    expect(server.callsTo('DELETE /api/links/{id}')[0].path).toBe(
      '/api/links/501'
    )
    const broken = screen.getByText('The bond was broken')
    await expect.element(broken).toBeVisible()
    toast.dismiss()
    await expect.element(broken).not.toBeInTheDocument()
    await screen.getByRole('button', { name: 'Create a bond' }).click()
    await screen.getByRole('combobox', { name: 'Kind' }).click()
    await screen.getByRole('option', { name: 'Protects' }).click()
    await screen.getByRole('combobox', { name: 'Target' }).click()
    await screen.getByRole('option', { name: /Fisher Folk/ }).click()
    await screen.getByRole('button', { name: 'Create bond' }).click()
    await expect.poll(() => server.callsTo('POST /api/links').length).toBe(1)
    expect(server.callsTo('POST /api/links')[0].body).toMatchObject({
      source_id: 7,
      target_id: 50,
      kind: 'protects',
    })
  })

  it('lists worshippers, creations with status and words exchanged', async () => {
    const { screen } = await openSon(7)
    await expect
      .element(screen.getByRole('heading', { name: 'Worshippers' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'Creations' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'The Bell Choir' }))
      .toBeVisible()
    await expect.element(screen.getByText('Rejected').first()).toBeVisible()
    await expect
      .element(
        screen.getByText('"Grant me the strength to hold the western storm."')
      )
      .toBeVisible()
  })

  it('groups his turns by epoch from the ledger and shows his chronicle trace', async () => {
    const { screen, server } = await openSon(7)
    await expect
      .element(screen.getByText('Epoch 11 · 1 actions · 3 changes'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('heading', { name: 'Trace in the chronicle' }))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('The fisher folk prayed for calm seas.').first()
      )
      .toBeVisible()
    const ledger = server.callsTo('GET /api/ledger')[0]
    expect(ledger.query.get('actor_kind')).toBe('son')
    expect(ledger.query.get('actor_id')).toBe('7')
  })
})
