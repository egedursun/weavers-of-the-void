import { expect, test } from '@playwright/test'
import { captureWrites, replyWith, writesTo } from './capture'
import { mockApi } from './mockApi'

const SETTLEMENT = '/chronicle?drawer=entity:43'
const STRUCTURE = '/chronicle?drawer=entity:42'
const MORTAL = '/chronicle?drawer=entity:45'
const PEOPLE = '/chronicle?drawer=entity:44'

async function openDrawer(page: import('@playwright/test').Page, url: string) {
  await mockApi(page)
  const writes = await captureWrites(page)
  await page.goto(url)
  const drawer = page.getByRole('dialog').last()
  await expect(drawer.getByRole('heading', { level: 2 }).first()).toBeVisible()
  return { drawer, writes }
}

test('the hero shows the record identity and toggles the favourite', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, STRUCTURE)
  await expect(drawer.getByText('Structure').first()).toBeVisible()
  await expect(drawer.getByText('by Ithren the Unbowed')).toBeVisible()
  await expect(drawer.getByRole('link', { name: 'Show on map' })).toBeVisible()
  await expect(drawer.getByRole('link', { name: 'Show in network' })).toBeVisible()
  await drawer.getByRole('button', { name: 'Favourite' }).click()
  await expect(page.getByText('Removed from favourites')).toBeVisible()
  expect(writesTo(writes, 'PUT', /\/api\/entities\/42\/favorite$/)[0]?.body).toEqual({ favorite: false })
})

test('the hero breadcrumb and Fate note show where the record stands', async ({ page }) => {
  const { drawer } = await openDrawer(page, STRUCTURE)
  const location = drawer.getByRole('navigation', { name: 'Location' })
  await expect(location.getByText('Velmora-under-the-Glass')).toBeVisible()
  await expect(drawer.getByText('Accepted: the ossuary binds the town to its dead')).toBeVisible()
})

test('the section navigator lists the sections of the record', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  for (const name of ['Facts', 'Stats', 'Society', 'Depth', 'Hand of God', 'Commands', 'Bonds', 'Connections', 'Images', 'Chronicle', 'Edit']) {
    await expect(drawer.getByRole('button', { name, exact: true }).first()).toBeVisible()
  }
  await drawer.getByRole('button', { name: 'Bonds', exact: true }).click()
  await expect(drawer.locator('#section-bonds')).toBeInViewport()
})

test('the timeline strip shows one column per epoch since birth', async ({ page }) => {
  const { drawer } = await openDrawer(page, STRUCTURE)
  await expect(drawer.getByRole('link', { name: 'Epoch 2: 1 records' })).toBeVisible()
  await expect(drawer.getByRole('link', { name: 'Epoch 5: 1 records' })).toBeVisible()
  await expect(drawer.getByRole('link', { name: 'Epoch 3: 0 records' })).toBeVisible()
})

test('canon facts can be added with a reason and retired after confirming', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, STRUCTURE)
  await drawer.getByRole('button', { name: 'Add fact' }).click()
  const fix = drawer.getByRole('button', { name: 'Fix it in canon' })
  await expect(fix).toBeDisabled()
  await drawer.getByLabel('Predicate').fill('forbids')
  await expect(fix).toBeDisabled()
  await drawer.getByLabel('Or plain text').fill('the singing after dusk')
  await fix.click()
  await expect(page.getByText('Fact written into canon')).toBeVisible()
  expect(writesTo(writes, 'POST', /\/api\/facts$/)[0]?.body).toEqual({
    subject_id: 42,
    relation: 'forbids',
    object_id: null,
    object_text: 'the singing after dusk',
  })
  await drawer.getByRole('button', { name: 'Retire this fact' }).first().click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm.getByText('Retire this fact?')).toBeVisible()
  await confirm.getByRole('button', { name: 'Retire' }).click()
  await expect(page.getByText('Fact removed from canon')).toBeVisible()
  expect(writesTo(writes, 'DELETE', /\/api\/facts\/1$/)).toHaveLength(1)
})

test('settlement stats show the carrying capacity warning and exploration pressure', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  await expect(drawer.getByText('Last turn: epoch 6')).toBeVisible()
  await expect(drawer.getByText(/Acts this epoch/)).toBeVisible()
  await expect(drawer.getByText('Civilization tier 2')).toBeVisible()
  await expect(drawer.getByText(/Full 108%: growth stops/)).toBeVisible()
  await expect(drawer.getByText(/Spontaneous exploration pressure 2/)).toBeVisible()
  await drawer.getByRole('button', { name: 'Adjust stats' }).click()
  await expect(drawer.getByRole('spinbutton').first()).toBeVisible()
})

test('mortal stats show the life line, lifespan breakdown and the cost of death', async ({ page }) => {
  const { drawer } = await openDrawer(page, MORTAL)
  await expect(drawer.getByText('61 years old · 13 years left')).toBeVisible()
  await expect(drawer.getByText('60 base + 6 medicine + 8 renown = 74')).toBeVisible()
  await expect(drawer.getByText('A son pays 18 essence for a 35% chance; you pay 15.')).toBeVisible()
  await expect(drawer.getByRole('progressbar', { name: 'Sanity' })).toBeVisible()
})

test('society shows class shares, contentment, the uprising band and the stores', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  const society = drawer.locator('#section-society')
  await expect(society.getByText('An uprising is near')).toBeVisible()
  await expect(society.getByText('Least content: Warrior')).toBeVisible()
  await expect(society.getByText('Farmer')).toBeVisible()
  await expect(society.getByText('40%')).toBeVisible()
  await expect(society.getByText(/Food 140/)).toBeVisible()
})

test('wars and relations list the ongoing war and the bands of every bond', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  await expect(drawer.getByText('The War of the Glass Wells').first()).toBeVisible()
  await expect(drawer.getByLabel('Wars and relations').getByText('Ongoing')).toBeVisible()
  await expect(drawer.getByText('Ally', { exact: true })).toBeVisible()
  await expect(drawer.getByText('Once enemy')).toBeVisible()
  await expect(drawer.getByText('Holds captive').first()).toBeVisible()
})

test('depth shows history, sayings, rumours and the hidden truth', async ({ page }) => {
  const { drawer } = await openDrawer(page, STRUCTURE)
  await expect(drawer.getByText('Built in the second tide by salt-masons who never spoke again.')).toBeVisible()
  await expect(drawer.getByText('What the glass keeps, the glass sings.')).toBeVisible()
  await expect(drawer.getByText('A tenth king sleeps in a wall nobody has found.')).toBeVisible()
  await expect(drawer.getByRole('button', { name: 'Deepen again' })).toBeVisible()
  await drawer.getByRole('button', { name: 'The hidden truth' }).click()
  await expect(drawer.getByText('The kings are not dead; they are listening.')).toBeVisible()
})

test('a settlement lists what it knows and grants knowledge for free', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  await expect(drawer.getByText('What it knows')).toBeVisible()
  await expect(drawer.getByText('Salt Reading').first()).toBeVisible()
  await expect(drawer.getByText('It knows everything there is')).toBeVisible()
})

test('the bonds are grouped, debts are shown and a bond breaks after confirming', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, SETTLEMENT)
  const bonds = drawer.locator('#section-bonds')
  await expect(bonds.getByText(/12 .*barrels of brine-glass/)).toBeVisible()
  await bonds.getByRole('button', { name: 'Break this bond' }).first().click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm.getByText('Break this bond?')).toBeVisible()
  await confirm.getByRole('button', { name: 'Break' }).click()
  await expect(page.getByText('Bond broken')).toBeVisible()
  expect(writesTo(writes, 'DELETE', /\/api\/links\/\d+$/)).toHaveLength(1)
})

test('creating a bond needs a type and another record', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, SETTLEMENT)
  const bonds = drawer.locator('#section-bonds')
  await bonds.getByRole('button', { name: 'Create a bond' }).click()
  const create = bonds.getByRole('button', { name: /^Create/ }).last()
  await expect(create).toBeDisabled()
  await bonds.getByRole('combobox', { name: 'Bond' }).click()
  await page.getByRole('option').first().click()
  await bonds.getByRole('combobox', { name: 'The other side' }).click()
  await page.getByRole('option', { name: /Old Brine Tongue/ }).click()
  await bonds.getByLabel('Description').fill('sworn at dusk')
  await expect(create).toBeEnabled()
  await create.click()
  await expect(page.getByText('Bond created')).toBeVisible()
  const body = writesTo(writes, 'POST', /\/api\/links$/)[0]?.body as Record<string, unknown>
  expect(body).toMatchObject({ description: 'sworn at dusk' })
})

test('similar records are suggested with their reasons', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  await expect(drawer.getByText('May be related')).toBeVisible()
  await expect(drawer.getByText(/shared bonds/)).toBeVisible()
})

test('the connection finder shows the bond chain to another record', async ({ page }) => {
  const { drawer } = await openDrawer(page, STRUCTURE)
  await drawer.getByRole('combobox', { name: 'Connected to' }).click()
  await page.getByRole('option', { name: /Aeron/ }).click()
  const chain = drawer.getByRole('list', { name: 'Bond chain' })
  await expect(chain).toBeVisible()
  await expect(chain.getByText('Ithren the Unbowed')).toBeVisible()
})

test('the personal note autosaves and can be deleted after confirming', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, STRUCTURE)
  const note = drawer.getByRole('textbox', { name: 'My notes' })
  await expect(note).toHaveValue('Ask Ithren about the tenth king.')
  await note.fill('Ask Ithren about the tenth king and the door.')
  await note.blur()
  await expect.poll(() => writesTo(writes, 'PUT', /\/api\/entities\/42\/note$/).length).toBeGreaterThan(0)
  expect(writesTo(writes, 'PUT', /\/api\/entities\/42\/note$/).at(-1)?.body).toMatchObject({
    text: 'Ask Ithren about the tenth king and the door.',
  })
  await drawer.getByRole('button', { name: 'Delete note' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Delete note' }).click()
  await expect(page.getByText('Note deleted')).toBeVisible()
  expect(writesTo(writes, 'DELETE', /\/api\/entities\/42\/note$/)).toHaveLength(1)
})

test('mentions list the chronicle entries of the record', async ({ page }) => {
  const { drawer } = await openDrawer(page, STRUCTURE)
  const section = drawer.locator('#section-chronicle')
  await expect(section.getByText(/was raised under Velmora-under-the-Glass/)).toBeVisible()
  await expect(section.getByText(/Three hundred drowned/)).toBeVisible()
})

test('a people records how it tells of a god', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, PEOPLE)
  await drawer.getByLabel('What they tell').fill('They say Ithren walked out of the tide.')
  await drawer.getByRole('button', { name: /Write the account|Save the account|Write it/ }).first().click()
  await expect(page.getByText('The account was written')).toBeVisible()
  expect(writesTo(writes, 'PUT', /\/api\/beliefs$/)).toHaveLength(1)
})

test('renaming a record sends the changed fields', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, STRUCTURE)
  const edit = drawer.locator('#section-edit')
  await edit.getByLabel('Name').fill('The Singing Ossuary')
  await edit.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByText('The Singing Ossuary updated')).toBeVisible()
  expect(writesTo(writes, 'PATCH', /\/api\/entities\/42$/)[0]?.body).toMatchObject({ name: 'The Singing Ossuary' })
})

test('striking a record from canon asks first, and merging needs the typed word', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, STRUCTURE)
  await drawer.getByRole('button', { name: 'Dangerous operations' }).click()
  await drawer.getByRole('button', { name: 'Delete from canon' }).click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm.getByText(/from canon\?/)).toBeVisible()
  await confirm.getByRole('button', { name: 'Delete from canon' }).click()
  await expect(page.getByText('Canon updated')).toBeVisible()
  expect(writesTo(writes, 'PUT', /\/api\/entities\/42\/canon$/)[0]?.body).toEqual({ status: 'rejected' })
  const merge = drawer.getByRole('button', { name: 'Merge', exact: true })
  await expect(merge).toBeDisabled()
})

test('a rejected record offers to break Fate and return to canon', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, '/chronicle?drawer=entity:52')
  await drawer.getByRole('button', { name: 'Dangerous operations' }).click()
  await drawer.getByRole('button', { name: 'Break Fate, take into canon' }).click()
  await expect(page.getByText('Canon updated')).toBeVisible()
  expect(writesTo(writes, 'PUT', /\/api\/entities\/52\/canon$/)[0]?.body).toEqual({ status: 'canon' })
})

test('hand of god gates miracles with reasons and sends a confirmed curse', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, SETTLEMENT)
  const hand = drawer.locator('#section-hand')
  await expect(hand.getByRole('button', { name: 'Peace' })).toBeEnabled()
  await expect(hand.getByRole('button', { name: 'Healing' })).toBeEnabled()
  await expect(hand.getByText('It already knows all knowledge in the world.')).toBeVisible()
  await hand.getByRole('button', { name: 'Curse', exact: true }).click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm.getByText(/Curse Velmora/)).toBeVisible()
  await confirm.getByRole('button', { name: 'Curse', exact: true }).click()
  await expect(page.getByText('Intervention done')).toBeVisible()
  expect(writesTo(writes, 'POST', /\/api\/entities\/43\/intervene$/)[0]?.body).toEqual({ action: 'curse' })
})

test('disasters strike only after confirming and healing runs directly', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, SETTLEMENT)
  const hand = drawer.locator('#section-hand')
  await hand.getByRole('button', { name: 'Healing' }).click()
  await expect(page.getByText('Intervention done')).toBeVisible()
  await hand.getByRole('button', { name: 'Flood' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Send', exact: true }).click()
  const intervene = writesTo(writes, 'POST', /\/intervene$/).map((write) => write.body)
  expect(intervene).toEqual([
    { action: 'miracle', miracle: 'healing' },
    { action: 'disaster', disaster: 'flood' },
  ])
})

test('a dream needs content before it can be sent', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, MORTAL)
  const hand = drawer.locator('#section-hand')
  const send = hand.getByRole('button', { name: 'Send the dream' })
  await expect(send).toBeDisabled()
  await hand.getByRole('textbox', { name: 'The dream' }).fill('A salt door opens in the north.')
  await expect(send).toBeEnabled()
  await send.click()
  await expect(page.getByText('Dream sent; it sees it on its next turn')).toBeVisible()
  expect(writesTo(writes, 'POST', /\/api\/entities\/45\/dream$/)[0]?.body).toEqual({
    text: 'A salt door opens in the north.',
  })
})

test('commands are searchable, show their cost and offer undo after running', async ({ page }) => {
  await mockApi(page)
  await replyWith(page, 'POST', /\/api\/entities\/43\/convert/, {
    action: 'convert',
    message: 'Velmora turned to the Creator.',
    essence_spent: 30,
    essence_gained: 0,
    created_ids: [],
    values: {},
    ledger_entry_id: 91,
  })
  await replyWith(page, 'POST', /\/api\/ledger\/91\/undo/, {
    action: 'undo',
    message: 'Undone',
    essence_spent: 0,
    essence_gained: 0,
    created_ids: [],
    values: {},
  })
  const writes = await captureWrites(page)
  await page.goto(SETTLEMENT)
  const drawer = page.getByRole('dialog').last()
  await drawer.getByRole('searchbox', { name: 'Find a command' }).fill('Convert')
  const card = drawer.locator('[data-action-id]').first()
  await expect(card).toBeVisible()
  await expect(drawer.getByRole('button', { name: /Convert to the Creator, costs 30 essence/ })).toBeVisible()
  await drawer.getByRole('button', { name: /Convert to the Creator, costs 30 essence/ }).click()
  await card.getByRole('button', { name: /^Convert to the Creator$/ }).last().click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm.getByText('Convert to the Creator?')).toBeVisible()
  expect(writesTo(writes, 'POST', /\/convert$/)).toHaveLength(0)
  await confirm.getByRole('button', { name: 'Convert to the Creator' }).click()
  await expect(page.getByText('Velmora turned to the Creator.')).toBeVisible()
  await page.getByRole('button', { name: 'Undo' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /\/api\/ledger\/91\/undo$/).length).toBe(1)
})

test('searching the commands with no match says so', async ({ page }) => {
  const { drawer } = await openDrawer(page, SETTLEMENT)
  await drawer.getByRole('searchbox', { name: 'Find a command' }).fill('zzzz')
  await expect(drawer.getByText('No command matches')).toBeVisible()
})

test('the Mechanics tab lists the mechanics acting on a record and runs one on it', async ({ page }) => {
  const { drawer, writes } = await openDrawer(page, MORTAL)
  const mechanics = drawer.locator('#section-mechanics')
  await mechanics.scrollIntoViewIfNeeded()
  await expect(mechanics.getByText('Typed injuries on body parts')).toBeVisible()
  await expect(mechanics.getByText('× 0.85 because a lingering illness saps their strength')).toBeVisible()
  await expect(drawer.locator('#section-biography').getByText('Varn and Osk met at the ford.')).toBeVisible()
  await mechanics.getByRole('button', { name: 'Run on this record now' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /\/api\/actions\/lever:run$/).length).toBe(1)
  expect(writesTo(writes, 'POST', /\/api\/actions\/lever:run$/)[0]?.body).toEqual({ mechanic: 'injuries', target_node_id: 45 })
})
