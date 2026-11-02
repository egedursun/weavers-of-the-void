import { expect, test } from '@playwright/test'
import { mockApi } from './mockApi'
import { type CheckOptions, collectViolations } from './pageChecks'

const CHECK_OPTIONS: CheckOptions = { tolerancePx: 1 }
const VIEW_KEY = 'aerona.cosmos.view'

test('the 2D cosmos selects a world, shows its card and stays consistent', async ({ page }) => {
  await mockApi(page)
  await page.addInitScript((key) => window.localStorage.setItem(key, '2d'), VIEW_KEY)
  await page.goto('/cosmos')
  const scene = page.getByRole('group', { name: 'Cosmos: stars, worlds and routes' })
  await expect(scene).toBeVisible()
  await scene.locator('[data-world-id="5"]').click()
  await expect(page.locator('article[data-world-id="5"]')).toBeVisible()
  await expect(page.getByText('Something is leaking in from outside.')).toBeVisible()
  const violations = await page.evaluate(collectViolations, CHECK_OPTIONS)
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([])
})

test('a star opens its card from the 2D view', async ({ page }) => {
  await mockApi(page)
  await page.addInitScript((key) => window.localStorage.setItem(key, '2d'), VIEW_KEY)
  await page.goto('/cosmos')
  await page.getByRole('button', { name: 'Keth Beacon, Pulsar' }).click()
  await expect(page.locator('article[data-star-id="11"]')).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Star' })).toHaveAttribute('data-state', 'active')
})

test('forgetting a world asks for confirmation and reports success', async ({ page }) => {
  await mockApi(page)
  await page.goto('/cosmos?world=5')
  await page.getByRole('button', { name: /Bury in oblivion/ }).click()
  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Bury in mist' }).click()
  await expect(page.getByText(/was buried in oblivion/)).toBeVisible()
})

test('the travel resource chip opens the command panel at the resource section', async ({ page }) => {
  await mockApi(page)
  await page.goto('/cosmos')
  await page.getByRole('button', { name: /Travel resource/ }).click()
  await expect(page).toHaveURL(/panel=command/)
  await expect(page.locator('[data-command-section="resource"]')).toHaveAttribute('data-state', 'open')
})
