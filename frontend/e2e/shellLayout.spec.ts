import { type Page, expect, test } from '@playwright/test'
import { mockApi } from './mockApi'
import { SOFTWARE_WEBGL } from './softwareWebgl'

const FEED_KEY = 'aerona.feed'
const VIEW_KEY = 'aerona.cosmos.view'
const WORLD_FILTER_KEY = 'aerona.world-filter'
const MIN_CANVAS_PX = 600
const WIDTH_TOLERANCE_PX = 2

const CANVASES = [
  { route: '/cosmos', view: '3d', scene: '[aria-label="Cosmos: stars, worlds and routes"]' },
  { route: '/cosmos', view: '2d', scene: '[aria-label="Cosmos: stars, worlds and routes"]' },
  { route: '/map', view: null, scene: '[data-map-scene]' },
  { route: '/network', view: null, scene: '[data-graph-scene]' },
]

test.use(SOFTWARE_WEBGL)

test.beforeEach(({ browserName }, testInfo) => {
  test.skip(browserName !== 'chromium')
  const phone = testInfo.title.includes('phone')
  test.skip(phone !== (testInfo.project.name === 'mobile'), 'Each layout check runs on its own viewport')
})

async function openWithFeed(page: Page, url: string, view: string | null) {
  await mockApi(page)
  await page.addInitScript(
    ({ feed, viewKey, preset }) => {
      window.localStorage.setItem(feed, JSON.stringify({ state: { open: true, sounds: false, ambient: false, muted: [] }, version: 0 }))
      if (preset) window.localStorage.setItem(viewKey, preset)
    },
    { feed: FEED_KEY, viewKey: VIEW_KEY, preset: view }
  )
  await page.goto(url)
}

async function settledWidth(page: Page, selector: string): Promise<number> {
  const scene = page.locator(selector).first()
  await expect(scene).toBeVisible()
  let previous = -1
  await expect
    .poll(async () => {
      const width = (await scene.boundingBox())?.width ?? 0
      const settled = width === previous && width > 0
      previous = width
      return settled
    })
    .toBe(true)
  return previous
}

for (const canvas of CANVASES) {
  test(`the open live feed never squeezes ${canvas.route}${canvas.view ? ` in ${canvas.view}` : ''}`, async ({ page }) => {
    await openWithFeed(page, canvas.route, canvas.view)
    const closed = await settledWidth(page, canvas.scene)
    await expect(page.locator('[data-layout="feed-dock"]')).toHaveCount(0)
    await page.getByRole('button', { name: 'Live feed', exact: true }).click()
    await expect(page.getByRole('dialog', { name: 'Live feed' })).toBeVisible()
    const open = await settledWidth(page, canvas.scene)
    expect(open).toBeGreaterThan(MIN_CANVAS_PX)
    expect(Math.abs(open - closed)).toBeLessThanOrEqual(WIDTH_TOLERANCE_PX)
  })
}

test('the open live feed docks beside a page route', async ({ page }) => {
  await openWithFeed(page, '/chronicle', null)
  const dock = page.locator('[data-layout="feed-dock"]')
  await expect(dock).toBeVisible()
  const main = page.locator('#content')
  const [dockBox, mainBox] = await Promise.all([dock.boundingBox(), main.boundingBox()])
  if (!dockBox || !mainBox) throw new Error('missing layout boxes')
  expect(mainBox.x + mainBox.width).toBeLessThanOrEqual(dockBox.x + 1)
})

test('the global world filter carries into the map, chronicle, network and cosmos', async ({ page }) => {
  const maps: string[] = []
  await mockApi(page)
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    if (path.endsWith('/map')) maps.push(path)
  })
  await page.addInitScript((key) => window.localStorage.setItem(key, JSON.stringify({ state: { worldId: 5 }, version: 0 })), WORLD_FILTER_KEY)
  await page.goto('/map')
  const switcher = page.getByRole('combobox', { name: 'World filter' })
  await expect(switcher).not.toContainText('Whole cosmos')
  const name = (await switcher.textContent())?.trim() ?? ''
  expect(name).not.toBe('')
  await expect.poll(() => maps.some((path) => path.startsWith('/api/worlds/5/map'))).toBe(true)
  await page.goto('/chronicle')
  await expect(page.getByRole('combobox', { name: 'World', exact: true })).toContainText(name)
  await page.goto('/network')
  await expect(page.locator('[data-graph-scene]')).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'World', exact: true })).not.toContainText('Whole cosmos')
  await page.goto('/cosmos')
  const chooser = page.getByRole('radiogroup', { name: 'Choose a world' })
  await expect(chooser.getByRole('radio').nth(1)).toBeVisible()
  await expect(chooser.getByRole('radio', { checked: true })).toHaveCount(1)
  await expect(chooser.getByRole('radio').first()).not.toBeChecked()
})

test('the top bar slides away while scrolling down a long page on a phone and returns on the way up', async ({ page }) => {
  await mockApi(page)
  await page.goto('/chronicle')
  const bar = page.locator('[data-layout="top-bar"]')
  await expect(bar).toBeVisible()
  await page.mouse.wheel(0, 1200)
  await expect(bar).toHaveAttribute('data-collapsed', 'true')
  await page.mouse.wheel(0, -400)
  await expect(bar).not.toHaveAttribute('data-collapsed', 'true')
})

test('on a phone the top bar fits and the world filter and theme live in the navigation sheet', async ({ page }) => {
  await mockApi(page)
  await page.goto('/chronicle')
  const bar = page.locator('[data-layout="top-bar"]')
  await expect(bar.getByRole('link', { name: /notifications/ })).toBeVisible()
  const viewport = page.viewportSize()
  const box = await bar.getByRole('link', { name: /notifications/ }).boundingBox()
  if (!viewport || !box) throw new Error('missing layout boxes')
  expect(box.x + box.width).toBeLessThanOrEqual(viewport.width)
  await expect(bar.getByRole('combobox', { name: 'World filter' })).toBeHidden()
  await page.getByRole('button', { name: 'Toggle Sidebar' }).click()
  const tools = page.locator('[data-layout="sidebar-phone-tools"]')
  await expect(tools.getByRole('combobox', { name: 'World filter' })).toBeVisible()
  await expect(tools.getByRole('button', { name: 'Change theme' })).toBeVisible()
})
