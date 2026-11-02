import { expect, test } from '@playwright/test'
import { mockApi } from './mockApi'

test('the map switches layers, shows its legend and pins a note', async ({ page }) => {
  await mockApi(page)
  await page.goto('/map')
  await expect(page.getByRole('img', { name: /Map of/ })).toBeVisible()
  const layers = page.getByRole('button', { name: 'Layers' })
  const sheet = await layers.isVisible()
  if (sheet) await layers.click()
  await page.getByRole('radio', { name: 'Political' }).click()
  if (sheet) await page.keyboard.press('Escape')
  const legend = page.getByRole('button', { name: 'Legend' })
  if ((await legend.getAttribute('aria-pressed')) !== 'true') await legend.click()
  await expect(page.getByText('Political control')).toBeVisible()
  await expect(page.locator('[data-map-legend]').getByText('Kethrani')).toBeVisible()
  await page.getByRole('button', { name: 'Note pin' }).click()
  const scene = page.getByRole('img', { name: /Map of/ })
  const box = await scene.boundingBox()
  if (!box) throw new Error('map scene has no box')
  await page.mouse.click(box.x + 30, box.y + 30)
  const dialog = page.getByRole('dialog', { name: 'New note' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('textbox').fill('Remember the salt.')
  await dialog.getByRole('button', { name: 'Pin' }).click()
  await expect(page.getByText('Note pinned')).toBeVisible()
})

test('the past epoch banner returns to today', async ({ page }) => {
  await mockApi(page)
  await page.goto('/map?epoch=8')
  await expect(page.getByText('The world in Epoch 8')).toBeVisible()
  await page.getByRole('button', { name: 'Back to today' }).click()
  await expect(page.getByText('The world in Epoch 8')).toBeHidden()
})

test('the network finds how two records are connected', async ({ page }) => {
  await mockApi(page)
  await page.goto('/network?from=4&to=1')
  await expect(page.locator('[data-path-result]')).toBeVisible()
  await expect(page.locator('[data-path-result]').getByText(/Connected in 1 step/)).toBeVisible()
  await page.getByRole('button', { name: 'Connectivity' }).click()
  await expect(page.getByText(/nodes · 37 links/)).toBeVisible()
  await page.getByRole('button', { name: 'Repair loose ends' }).click()
  await expect(page.getByText('No loose ends to repair.')).toBeVisible()
})

test('the network opens in 3D or falls back to 2D without errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await mockApi(page)
  await page.addInitScript(() => window.localStorage.setItem('aerona.graph.mode', '"3d"'))
  await page.goto('/network')
  await expect(page.locator('[data-graph-scene]')).toBeVisible()
  const threeD = page.locator('[data-graph-3d-controls]')
  if (await threeD.isVisible()) {
    await threeD.getByRole('button', { name: 'Fit' }).click()
    await threeD.getByRole('button', { name: 'Re-layout' }).click()
  }
  await expect(page.locator('[data-graph-scene] canvas').first()).toBeVisible()
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  expect(errors).toEqual([])
})
