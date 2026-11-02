import { expect, test } from '@playwright/test'
import { captureWrites, writesTo } from './capture'
import { mockApi } from './mockApi'

test('the map fog can be lifted and laid again', async ({ page }) => {
  await mockApi(page)
  await page.goto('/map')
  await expect(page.getByRole('img', { name: /Map of/ })).toBeVisible()
  const layers = page.getByRole('button', { name: 'Layers' })
  const fog = page.getByRole('button', { name: 'Fog' })
  await expect(layers.or(fog)).toBeVisible()
  if (await layers.isVisible()) await layers.click()
  await expect(fog).toHaveAttribute('aria-pressed', 'true')
  await fog.click()
  await expect(fog).toHaveAttribute('aria-pressed', 'false')
  await expect
    .poll(async () => JSON.parse((await page.evaluate(() => window.localStorage.getItem('aerona.map.overlays'))) ?? '{}'))
    .toMatchObject({ fog: false })
})

test('a war opens on its own and leads back to all wars', async ({ page }) => {
  await mockApi(page)
  await page.goto('/wars')
  await page.getByRole('link', { name: 'Open the war' }).first().click()
  await expect(page).toHaveURL(/war=1/)
  const focus = page.locator('#war-focus')
  await expect(focus.getByRole('heading', { name: 'The Salt War' })).toBeVisible()
  await focus.getByRole('link', { name: 'All wars' }).click()
  await expect(page.locator('#war-focus')).toHaveCount(0)
})

test('a language is reshaped and its signature redrawn', async ({ page }) => {
  await mockApi(page)
  const writes = await captureWrites(page)
  await page.goto('/languages?view=tree&language=47')
  const shaper = page.locator('#languages-shape')
  await shaper.getByRole('textbox', { name: 'Taught names' }).fill('Ashkar\nOrrin')
  await shaper.getByRole('button', { name: 'Save the tongue' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /language:edit$/).length).toBe(1)
  expect(writesTo(writes, 'POST', /language:edit$/)[0].body).toMatchObject({ language_id: 47, sample_names: ['Ashkar', 'Orrin'] })
  await shaper.getByRole('button', { name: 'Redraw the signature' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /language:signature$/).length).toBe(1)
})

test('the economy runs by hand from the cosmos command panel', async ({ page }) => {
  await mockApi(page)
  const writes = await captureWrites(page)
  await page.goto('/cosmos?panel=command&section=economy')
  await page.getByRole('button', { name: /Run the cosmic economy/ }).click()
  await expect.poll(() => writesTo(writes, 'POST', /economy:cosmic$/).length).toBe(1)
  await page.getByRole('button', { name: /^Cure/ }).first().click()
  await expect.poll(() => writesTo(writes, 'POST', /addiction:cure$/).length).toBe(1)
  expect(writesTo(writes, 'POST', /addiction:cure$/)[0].body).toEqual({ entity_id: 43, resource_id: 90 })
})
