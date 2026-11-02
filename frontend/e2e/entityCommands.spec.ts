import { type Page, expect, test } from '@playwright/test'
import { captureWrites, writesTo } from './capture'
import { mockApi } from './mockApi'

const COMMUNITY_COMMANDS = [
  'Convert to the Creator',
  'Curse or free a bloodline',
  'Manifest before mortals',
  'Wrath upon a record',
  'End a record\'s life in the world',
  'Move a record',
  'Decree war, peace, alliance or trade',
  'Single out a mortal agent',
  'Exile to another world',
  'Send to explore',
  'Show the road of the sky',
  'Send an expedition',
  'Set the star of the epoch',
  'Let a community read the Archive',
]

const MORTAL_COMMANDS = [
  'Drain or devour a mortal',
  'Choose a prophet',
  'Raise a mortal to godhood',
  'Take a mortal\'s life',
  'Shield a mortal from death',
  'Convert to the Creator',
  'Manifest before mortals',
  'Move a record',
  'Single out a mortal agent',
  'Exile to another world',
  'Send to explore',
  'Send an expedition',
  'Grant or take immortality',
  'Send a sign of the Creator',
]

async function openCommands(page: Page, url: string) {
  await mockApi(page)
  const writes = await captureWrites(page)
  await page.goto(url)
  const drawer = page.getByRole('dialog').last()
  await expect(drawer.locator('[data-record-actions]')).toBeVisible()
  return { drawer, writes }
}

test('a community offers its divine commands, each with the live cost in its label', async ({ page }) => {
  const { drawer } = await openCommands(page, '/chronicle?drawer=entity:43')
  for (const title of COMMUNITY_COMMANDS) {
    await expect(
      drawer.locator('[data-action-id]').getByRole('button', { name: new RegExp(`^${title}`) }).first()
    ).toBeVisible()
  }
  await expect(drawer.getByRole('button', { name: 'Convert to the Creator, costs 30 essence' })).toBeVisible()
  await expect(drawer.getByRole('button', { name: /^Manifest before mortals, costs 10 essence/ })).toBeVisible()
})

test('a mortal offers its own commands and hides the community ones', async ({ page }) => {
  const { drawer } = await openCommands(page, '/chronicle?drawer=entity:45')
  for (const title of MORTAL_COMMANDS) {
    await expect(
      drawer.locator('[data-action-id]').getByRole('button', { name: new RegExp(`^${title}`) }).first()
    ).toBeVisible()
  }
  await expect(drawer.getByRole('button', { name: /^Decree war, peace/ })).toHaveCount(0)
  await expect(drawer.getByRole('button', { name: /^Set class shares/ })).toHaveCount(0)
})

test('wrath needs a reason, asks for confirmation and sends the reason', async ({ page }) => {
  const { drawer, writes } = await openCommands(page, '/chronicle?drawer=entity:43')
  await drawer.getByRole('searchbox', { name: 'Find a command' }).fill('Wrath')
  const card = drawer.locator('[data-action-id="wrath"]')
  await card.getByRole('button', { name: /^Wrath upon a record/ }).click()
  await card.getByLabel('Why? Written in the chronicle').fill('It refused the tithe.')
  await card.getByRole('button', { name: 'Wrath upon a record', exact: true }).click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm.getByText(/will be destroyed/)).toBeVisible()
  expect(writesTo(writes, 'POST', /\/wrath$/)).toHaveLength(0)
  await confirm.getByRole('button', { name: 'Wrath upon a record' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /\/api\/entities\/43\/wrath$/).length).toBe(1)
  expect(writesTo(writes, 'POST', /\/wrath$/)[0]?.body).toMatchObject({ reason: 'It refused the tithe.' })
})

test('the archive state command is inert until another state is chosen', async ({ page }) => {
  const { drawer, writes } = await openCommands(page, '/chronicle?drawer=entity:45')
  await expect(drawer.getByText('Records whose importance falls sink into history by themselves.')).toBeVisible()
  await expect(drawer.getByText(/Importance 14 · last named in epoch 6/)).toBeVisible()
  const row = drawer.locator('[data-domain="form-row"]').filter({ hasText: 'Archive' }).first()
  const assign = row.getByRole('button', { name: 'Assign' })
  await expect(assign).toHaveAttribute('aria-disabled', 'true')
  await row.getByRole('combobox').click()
  await page.getByRole('option', { name: 'Keep in the Atlas' }).click()
  await assign.click()
  await expect(page.getByText('Archive state set')).toBeVisible()
  expect(writesTo(writes, 'PUT', /\/api\/entities\/45\/archive$/)[0]?.body).toEqual({ mode: 'atlas' })
})

test('the arrange block shows the current patron and can leave the record godless', async ({ page }) => {
  const { drawer, writes } = await openCommands(page, '/chronicle?drawer=entity:43')
  await expect(drawer.getByText('Now: Ithren the Unbowed')).toBeVisible()
  const row = drawer.locator('[data-domain="form-row"]').filter({ hasText: 'Patron' }).first()
  const assign = row.getByRole('button', { name: 'Assign' })
  await expect(assign).toHaveAttribute('aria-disabled', 'true')
  await row.getByRole('combobox').click()
  await page.getByRole('option', { name: 'Leave godless' }).click()
  await assign.click()
  await expect(page.getByText('Patron assigned')).toBeVisible()
  expect(writesTo(writes, 'PUT', /\/api\/entities\/43\/patron$/)).toHaveLength(1)
})

test('bonds can be proposed by Fate and marks changed from the arrange block', async ({ page }) => {
  const { drawer } = await openCommands(page, '/chronicle?drawer=entity:45')
  await expect(drawer.getByRole('button', { name: 'Let Fate suggest bonds' })).toBeVisible()
  await expect(drawer.getByRole('button', { name: 'Change marks' })).toBeVisible()
  await expect(drawer.getByText('Not travelling. Send it with the expedition command below.')).toBeVisible()
})
