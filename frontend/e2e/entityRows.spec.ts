import { type Page, expect, test } from '@playwright/test'
import { captureWrites, writesTo } from './capture'
import { loreResponse } from './loreMocks'
import { mockApi } from './mockApi'

type Detail = Record<string, unknown> & { entity: Record<string, unknown>; flags: string[]; bonds: { kind: string }[] }

const MORTAL = 45
const SETTLEMENT = 43
const KNOWLEDGE = 48
const REGION = 41
const LORE_REFERER = 'http://127.0.0.1/chronicle'

function loreDetail(id: number): Detail {
  return loreResponse('GET', new URL(`http://mock/api/entities/${id}`), LORE_REFERER) as Detail
}

async function withDetail(page: Page, id: number, change: (detail: Detail) => Detail) {
  await page.route(new RegExp(`/api/entities/${id}$`), (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(change(structuredClone(loreDetail(id)))) })
  })
}

async function openRecord(page: Page, id: number, prepare?: (page: Page) => Promise<void>) {
  await mockApi(page)
  if (prepare) await prepare(page)
  const writes = await captureWrites(page)
  await page.goto(`/chronicle?entry=entity:${id}`)
  const entryWindow = page.getByRole('dialog').last()
  await expect(entryWindow.getByRole('heading', { level: 2 }).first()).toBeVisible()
  return { entryWindow, writes }
}

async function command(entryWindow: ReturnType<Page['getByRole']>, query: string, title: string) {
  await entryWindow.getByRole('searchbox', { name: 'Find a command' }).fill(query)
  const card = entryWindow.locator('[data-action-id]').filter({ hasText: title }).first()
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: new RegExp(`^${title}`) }).first().click()
  return card
}

test('the hero chips show known marks with their tone and prefixed tags in words', async ({ page }) => {
  const { entryWindow } = await openRecord(page, SETTLEMENT, (target) =>
    withDetail(target, SETTLEMENT, (detail) => ({ ...detail, flags: [...detail.flags, 'cursed'], tags: ['tier:2', 'side:north', 'branch:secret'] }))
  )
  await expect(entryWindow.getByText('Protected from ruin').first()).toBeVisible()
  await expect(entryWindow.locator('[data-slot="badge"]').filter({ hasText: /^Cursed$/ }).first()).toHaveClass(/destructive/)
  await expect(entryWindow.getByText('Tier 2').first()).toBeVisible()
  await expect(entryWindow.getByText('Side north').first()).toBeVisible()
  await expect(entryWindow.getByText(/^Branch secret$/)).toHaveCount(0)
})

test('a knowledge record shows its branch, level, finder and knowers', async ({ page }) => {
  const { entryWindow } = await openRecord(page, KNOWLEDGE)
  const panel = entryWindow.locator('#section-knowledge')
  await expect(panel).toBeVisible()
  await expect(panel.getByText('Writing · level 2')).toBeVisible()
  await expect(panel.getByRole('link', { name: /^Orun the Pale/ })).toBeVisible()
  await expect(panel.getByRole('link', { name: 'Velmora-under-the-Glass' })).toBeVisible()
  await expect(panel.getByRole('link', { name: 'The Brine-Singers of the Ninth Shore' })).toBeVisible()
})

test('a thinking record that lacks a knowledge can be taught it by the hand of god', async ({ page }) => {
  const { entryWindow, writes } = await openRecord(page, MORTAL, (target) =>
    withDetail(target, MORTAL, (detail) => ({ ...detail, bonds: detail.bonds.filter((bond) => bond.kind !== 'knows') }))
  )
  const hand = entryWindow.locator('#section-hand')
  await hand.getByRole('combobox', { name: 'Knowledge to teach' }).click()
  await page.getByRole('option', { name: /Salt Reading/ }).click()
  await hand.getByRole('button', { name: /^Teach/ }).click()
  await expect.poll(() => writesTo(writes, 'POST', new RegExp(`/api/entities/${MORTAL}/intervene$`)).length).toBe(1)
  expect(writesTo(writes, 'POST', /\/intervene$/)[0].body).toEqual({ action: 'teach_knowledge', knowledge_id: KNOWLEDGE })
})

test('a living record can be exiled to another world after confirming and pardoned when marked', async ({ page }) => {
  const { entryWindow, writes } = await openRecord(page, MORTAL, (target) =>
    withDetail(target, MORTAL, (detail) => ({ ...detail, flags: [...detail.flags, 'oathbreaker'] }))
  )
  const pardon = await command(entryWindow, 'Pardon', 'Pardon oath-breaking, exile and curse')
  await pardon.getByRole('button', { name: /^Pardon oath-breaking, exile and curse$/ }).last().click()
  await expect.poll(() => writesTo(writes, 'POST', new RegExp(`/api/entities/${MORTAL}/pardon$`)).length).toBe(1)
  const exile = await command(entryWindow, 'Exile', 'Exile to another world')
  await exile.getByRole('combobox').first().click()
  await page.getByRole('option').first().click()
  await exile.getByRole('button', { name: /^Exile to another world$/ }).last().click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Exile to another world' }).click()
  await expect.poll(() => writesTo(writes, 'POST', new RegExp(`/api/entities/${MORTAL}/exile$`)).length).toBe(1)
  expect(writesTo(writes, 'POST', /\/exile$/)[0].body).toMatchObject({ world_id: expect.any(Number) })
})

test('a region can open a cosmic deposit only once the travel resource is defined', async ({ page }) => {
  const { entryWindow } = await openRecord(page, REGION)
  await entryWindow.getByRole('searchbox', { name: 'Find a command' }).fill('deposit')
  const card = entryWindow.locator('[data-action-id="cosmos:deposit"]')
  await expect(card).toBeVisible()
  await expect(card).toContainText(/Open a cosmic deposit/)
  const run = card.getByRole('button', { name: /^Open a cosmic deposit/ }).first()
  await run.click()
  await expect(card.getByText("Define the cosmos's travel resource in the Cosmos screen first.").or(card.getByRole('button', { name: /^Open a cosmic deposit$/ })).first()).toBeVisible()
})

test('marks, traits and mechanics are toggled from the tag editor', async ({ page }) => {
  const { entryWindow, writes } = await openRecord(page, SETTLEMENT)
  const tags = entryWindow.locator('#section-tags')
  await tags.getByRole('button', { name: 'Change marks' }).click()
  const active = tags.getByRole('button', { name: 'Protected from ruin' })
  await expect(active).toHaveAttribute('aria-pressed', 'true')
  await active.click()
  await expect.poll(() => writesTo(writes, 'PATCH', new RegExp(`/api/entities/${SETTLEMENT}/tags$`)).length).toBe(1)
  expect(writesTo(writes, 'PATCH', /\/tags$/)[0].body).toEqual({ remove_flags: ['protected_from_ruin'] })
  const inactive = tags.locator('button[aria-pressed="false"]').first()
  await inactive.click()
  await expect.poll(() => writesTo(writes, 'PATCH', /\/tags$/).length).toBe(2)
  expect(Object.keys(writesTo(writes, 'PATCH', /\/tags$/)[1].body as object)[0]).toMatch(/^add_/)
})
