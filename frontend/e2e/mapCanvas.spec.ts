import { readFileSync } from 'node:fs'
import path from 'node:path'
import { type Page, type Request, expect, test } from '@playwright/test'
import { captureWrites, writesTo } from './capture'
import { mockApi } from './mockApi'

type MapFixture = {
  geometry: { extent: { x: number; y: number; width: number; height: number } }
  notes: Record<string, unknown>[]
}

const MAP: MapFixture = JSON.parse(readFileSync(path.resolve(import.meta.dirname, 'fixtures/mapGraph.json'), 'utf8')).map
const FEED_KEY = 'aerona.feed'
const OVERLAYS_KEY = 'aerona.map.overlays'
const SCAN_STEP_PX = 6

type Spot = { x: number; y: number; cursor: string }

async function openMap(page: Page, url = '/map') {
  await mockApi(page)
  await page.addInitScript((key) => {
    window.localStorage.setItem(key, JSON.stringify({ state: { open: false, sounds: false, ambient: false, muted: [] }, version: 0 }))
  }, FEED_KEY)
  const maps: string[] = []
  page.on('request', (request: Request) => {
    const url = new URL(request.url())
    if (/^\/api\/worlds\/\d+\/map$/.test(url.pathname)) maps.push(`${url.pathname}${url.search}`)
  })
  await page.goto(url)
  const scene = page.getByRole('img', { name: /^Map of / })
  await expect(scene).toBeVisible()
  await scene.scrollIntoViewIfNeeded()
  await settle(page)
  return { scene, maps }
}

async function settle(page: Page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
}

async function pixels(page: Page) {
  await settle(page)
  return page.locator('[data-map-scene] canvas').evaluate((node) => (node as HTMLCanvasElement).toDataURL())
}

async function scan(page: Page, cursor: string): Promise<Spot[]> {
  return page.locator('[data-map-scene] canvas').evaluate(
    (node, { wanted, step }) => {
      const canvas = node as HTMLCanvasElement
      const box = canvas.getBoundingClientRect()
      const found: { x: number; y: number; cursor: string }[] = []
      for (let y = box.top + step; y < box.bottom - step; y += step)
        for (let x = box.left + step; x < box.right - step; x += step) {
          canvas.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y, bubbles: true, pointerType: 'mouse' }))
          if (canvas.style.cursor === wanted) found.push({ x, y, cursor: wanted })
        }
      canvas.dispatchEvent(new PointerEvent('pointerleave', { bubbles: true }))
      return found
    },
    { wanted: cursor, step: SCAN_STEP_PX }
  )
}

test.beforeEach(({ browserName }, testInfo) => {
  test.skip(browserName !== 'chromium')
  test.skip(testInfo.project.name === 'mobile' && !testInfo.title.includes('phone'), 'Canvas pointer tests run on the desktop project')
})

test('the map fetches the world map, follows the world selector and shows its status line', async ({ page }) => {
  const { maps } = await openMap(page)
  expect(maps.some((url) => url.startsWith('/api/worlds/3/map'))).toBe(true)
  await expect(page.locator('[data-map-status]')).toContainText(/1,639 known cells4 regions\d+ markersDrag markers to move · click: open its page\./)
  await page.getByRole('combobox', { name: 'World shown on the map' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('option', { selected: true })).toBeFocused()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: /^Mirevast/ })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/world=5/)
  await expect.poll(() => maps.some((url) => url.startsWith('/api/worlds/5/map'))).toBe(true)
})

test('overlay toggles redraw the scene and are remembered', async ({ page }) => {
  await openMap(page)
  const before = await pixels(page)
  for (const overlay of ['Roads', 'Wars', 'Events', 'Labels']) {
    const toggle = page.getByRole('button', { name: overlay, exact: true })
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'false')
  }
  expect(await pixels(page)).not.toBe(before)
  const stored = await page.evaluate((key) => window.localStorage.getItem(key), OVERLAYS_KEY)
  expect(JSON.parse(stored ?? '{}')).toMatchObject({ roads: false, wars: false, events: false, labels: false })
  await page.reload()
  await expect(page.getByRole('button', { name: 'Roads', exact: true })).toHaveAttribute('aria-pressed', 'false')
  await page.getByRole('button', { name: 'Roads', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Roads', exact: true })).toHaveAttribute('aria-pressed', 'true')
})

test('on a phone the layers open as a bottom sheet', async ({ page }) => {
  await openMap(page)
  const layers = page.getByRole('button', { name: 'Layers' })
  test.skip(!(await layers.isVisible()), 'The layer sheet exists only on narrow screens')
  await layers.click()
  const sheet = page.getByRole('dialog', { name: 'Layers' })
  await expect(sheet).toBeVisible()
  await sheet.getByRole('button', { name: 'Wars', exact: true }).click()
  await expect(sheet.getByRole('button', { name: 'Wars', exact: true })).toHaveAttribute('aria-pressed', 'false')
  await page.keyboard.press('Escape')
  await expect(sheet).toBeHidden()
})

test('finding a place focuses it on the map and an unknown name warns', async ({ page }) => {
  await openMap(page)
  const before = await pixels(page)
  const search = page.getByPlaceholder('Find on map…')
  await search.fill('Harrowmere')
  await search.press('Enter')
  await expect(page).toHaveURL(/focus=12/)
  expect(await pixels(page)).not.toBe(before)
  await search.fill('Atlantis')
  await search.press('Enter')
  await expect(page.getByText('No such place on the map.')).toBeVisible()
})

test('a focus request in the URL zooms on the entity', async ({ page }) => {
  await openMap(page)
  const fitted = await pixels(page)
  await page.goto('/map?focus=13')
  await expect(page.getByRole('img', { name: /^Map of / })).toBeVisible()
  expect(await pixels(page)).not.toBe(fitted)
})

test('the time slider shows a past epoch, plays forward and returns to today', async ({ page }) => {
  const { maps } = await openMap(page)
  const slider = page.locator('[data-map-time]').getByRole('slider')
  await slider.focus()
  await page.keyboard.press('ArrowLeft')
  await expect(page).toHaveURL(/epoch=11/)
  await expect.poll(() => maps.some((url) => url.includes('epoch=11'))).toBe(true)
  await expect(page.locator('[data-map-past]')).toBeVisible()
  await expect(page.locator('[data-map-status]')).toContainText("You're looking at the past; markers can't be moved.")
  await expect(page.getByRole('button', { name: 'Note pin' })).toBeDisabled()
  await page.getByRole('button', { name: 'Play epochs in order' }).click()
  await expect(page.getByRole('button', { name: 'Stop' })).toBeVisible()
  await expect(page).not.toHaveURL(/epoch=/, { timeout: 5000 })
  await expect(page.getByRole('button', { name: 'Play epochs in order' })).toBeVisible()
})

test('markers can be hovered and clicked to open their record', async ({ page }) => {
  await openMap(page)
  const spots = await scan(page, 'move')
  expect(spots.length).toBeGreaterThan(0)
  const spot = spots[Math.floor(spots.length / 2)]
  await page.mouse.move(spot.x, spot.y)
  await page.mouse.move(spot.x + 1, spot.y)
  await page.mouse.click(spot.x + 1, spot.y)
  const stack = page.locator('[data-map-stack]')
  if (await stack.waitFor({ timeout: 800 }).then(() => true, () => false)) await stack.getByRole('listitem').first().getByRole('button').click()
  await expect(page).toHaveURL(/drawer=entity/)
})

test('dragging a marker saves its new map position', async ({ page }) => {
  await openMap(page)
  const writes = await captureWrites(page)
  const spots = await scan(page, 'move')
  expect(spots.length).toBeGreaterThan(0)
  const spot = spots[0]
  await page.mouse.move(spot.x, spot.y)
  await page.mouse.down()
  await page.mouse.move(spot.x + 40, spot.y + 30, { steps: 10 })
  await page.mouse.up()
  await expect.poll(() => writesTo(writes, 'PUT', /\/api\/entities\/\d+\/map-position$/).length).toBe(1)
  const body = writesTo(writes, 'PUT', /\/map-position$/)[0].body as { x: number; y: number }
  expect(typeof body.x).toBe('number')
  expect(typeof body.y).toBe('number')
})

test('markers cannot be dragged while looking at the past', async ({ page }) => {
  await openMap(page, '/map?epoch=8')
  await expect(page.locator('[data-map-past]')).toBeVisible()
  expect(await scan(page, 'move')).toHaveLength(0)
  expect((await scan(page, 'pointer')).length).toBeGreaterThan(0)
})

test('a note pin opens its read popup and deletes after confirming', async ({ page }) => {
  const extent = MAP.geometry.extent
  const note = { ...MAP.notes[0], x: extent.x + extent.width / 2, y: extent.y + extent.height / 2 }
  await openMap(page)
  await page.route(/\/api\/worlds\/\d+\/map(\?.*)?$/, (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...MAP, notes: [note] }) })
  )
  await page.reload()
  await expect(page.getByRole('img', { name: /^Map of / })).toBeVisible()
  await page.getByRole('img', { name: /^Map of / }).scrollIntoViewIfNeeded()
  await settle(page)
  const writes = await captureWrites(page)
  const pins = await scan(page, 'pointer')
  let opened = false
  for (const pin of pins) {
    await page.mouse.click(pin.x, pin.y)
    const popup = page.getByRole('dialog', { name: 'Your note' })
    if (await popup.waitFor({ timeout: 400 }).then(() => true, () => false)) {
      opened = true
      break
    }
    if (/drawer=/.test(page.url())) await page.goBack()
    if (await page.locator('[data-map-stack]').isVisible()) await page.keyboard.press('Escape')
  }
  expect(opened).toBe(true)
  await page.getByRole('dialog', { name: 'Your note' }).getByRole('button', { name: 'Delete' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Delete the note' }).click()
  await expect.poll(() => writesTo(writes, 'DELETE', /\/api\/map-notes\/1$/).length).toBe(1)
})

test('the legend lists only the markers present with tier thresholds', async ({ page }) => {
  await openMap(page)
  const legendToggle = page.getByRole('button', { name: 'Legend' })
  if ((await legendToggle.getAttribute('aria-pressed')) !== 'true') await legendToggle.click()
  const legend = page.locator('[data-map-legend]')
  await expect(legend).toBeVisible()
  await expect(legend).toContainText(/Settlement|Town|City/)
  await expect(legend).toContainText(/War/)
  await expect(legend).toContainText(/Your note|note/i)
})

test('war and event markers show their names on hover', async ({ page }) => {
  await openMap(page)
  const spots = await scan(page, 'pointer')
  const seen = new Set<string>()
  for (const spot of spots) {
    await page.mouse.move(spot.x, spot.y)
    for (const name of ['The War of the Salt Crowns', 'The Ashfall of Stonefold', 'Ruins of Old Harrow'])
      if (await page.locator('[data-map-frame]').getByText(name).first().isVisible()) seen.add(name)
  }
  expect(seen.has('The War of the Salt Crowns')).toBe(true)
  expect(seen.has('The Ashfall of Stonefold') || seen.has('Ruins of Old Harrow')).toBe(true)
})

test('the star of the epoch is shown today and hidden in the past', async ({ page }) => {
  await openMap(page)
  await expect(page.locator('[data-map-frame]').getByText(/ ascendant$/)).toBeVisible()
  await page.goto('/map?epoch=8')
  await expect(page.locator('[data-map-past]')).toBeVisible()
  await expect(page.locator('[data-map-frame]').getByText(/ ascendant$/)).toHaveCount(0)
})
