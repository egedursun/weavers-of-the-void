import { type Page, expect, test } from '@playwright/test'
import { captureWrites, replyWith, writesTo } from './capture'
import { mockApi } from './mockApi'
import { SOFTWARE_WEBGL } from './softwareWebgl'

const FEED_KEY = 'aerona.feed'
const NOW = '2026-01-01T12:00:00+00:00'

test.use(SOFTWARE_WEBGL)

test.beforeEach(({ browserName }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile' || browserName !== 'chromium', 'The network canvas runs once on the desktop project')
})

async function openGraph(page: Page, url = '/network', mode: '2d' | '3d' = '2d') {
  await mockApi(page)
  await page.addInitScript(
    ({ feed, view }) => {
      window.localStorage.setItem(feed, JSON.stringify({ state: { open: false, sounds: false, ambient: false, muted: [] }, version: 0 }))
      window.localStorage.setItem('aerona.graph.mode', JSON.stringify(view))
    },
    { feed: FEED_KEY, view: mode }
  )
  await page.goto(url)
  await expect(page.locator('[data-graph-scene] canvas').first()).toBeVisible()
}

async function selectNode(page: Page, name: string) {
  const search = page.getByPlaceholder('Search a node and focus…')
  await search.fill(name)
  await search.press('Enter')
}

function stored(page: Page, key: string) {
  return page.evaluate((name) => window.localStorage.getItem(name), key)
}

test('the 2D network draws on its canvas and finding a node opens its info card', async ({ page }) => {
  await openGraph(page)
  const drawn = await page.locator('[data-graph-scene] canvas').first().evaluate((node) => {
    const canvas = node as HTMLCanvasElement
    const context = canvas.getContext('2d')
    if (!context) return 0
    const data = context.getImageData(0, 0, canvas.width, canvas.height).data
    const colours = new Set<number>()
    for (let index = 0; index < data.length; index += 4 * 97) colours.add((data[index] << 16) | (data[index + 1] << 8) | data[index + 2])
    return colours.size
  })
  expect(drawn).toBeGreaterThan(2)
  await selectNode(page, 'Harrowmere')
  await expect(page).toHaveURL(/focus=12/)
  const card = page.locator('[data-node-info]')
  await expect(card).toBeVisible()
  await expect(card.getByText('Harrowmere')).toBeVisible()
  await expect(card.getByText(/^\d+ links?$/)).toBeVisible()
  await expect(card.getByRole('button', { name: 'Open its page' })).toBeVisible()
  await expect(card.getByRole('link', { name: 'Show on map' })).toHaveAttribute('href', /\/map\?world=\d+&focus=12/)
  await card.getByRole('button', { name: 'Open its page' }).click()
  await expect(page).toHaveURL(/entry=entity/)
})

test('the info card finds the path to a second record and focuses the surroundings', async ({ page }) => {
  await openGraph(page)
  await selectNode(page, 'Ithren')
  const card = page.locator('[data-node-info]')
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Focus on its surroundings' }).click()
  await expect(page).toHaveURL(/focus=4/)
  await card.getByPlaceholder('Second record…').fill('Kethrani')
  await expect(page).toHaveURL(/from=4/)
  await expect(page).toHaveURL(/to=10/)
  await card.getByRole('button', { name: 'Close' }).click()
  await expect(card).toBeHidden()
})

test('clustering by world and the family legend filters are remembered', async ({ page }) => {
  await openGraph(page)
  const cluster = page.getByRole('button', { name: 'Cluster by world' })
  const before = await cluster.getAttribute('aria-pressed')
  await cluster.click()
  await expect(cluster).not.toHaveAttribute('aria-pressed', before ?? 'false')
  await expect.poll(() => stored(page, 'aerona.graph.cluster')).toBe(before === 'true' ? 'false' : 'true')
  const legend = page.locator('[data-graph-legend]')
  const family = legend.locator('button[aria-pressed]').first()
  await family.hover()
  await family.click()
  await expect.poll(() => stored(page, 'aerona.graph.hidden')).not.toBe(null)
  await expect.poll(async () => JSON.parse((await stored(page, 'aerona.graph.hidden')) ?? '[]').length).toBeGreaterThan(0)
  await legend.getByRole('button', { name: 'Types and links' }).click()
  await expect(legend.getByText('Link colours')).toBeVisible()
  const hiddenBefore = JSON.parse((await stored(page, 'aerona.graph.hidden')) ?? '[]').length
  await legend.locator('[data-slot="collapsible-content"] button[aria-pressed="true"]').first().click()
  await expect.poll(async () => JSON.parse((await stored(page, 'aerona.graph.hidden')) ?? '[]').length).toBeGreaterThan(hiddenBefore)
})

test('the network health panel lets Fate propose links, repairs everything after confirming and stops', async ({ page }) => {
  await openGraph(page)
  const writes = await captureWrites(page)
  await page.getByRole('button', { name: 'Connectivity' }).click()
  const health = page.locator('[data-network-health]')
  await expect(health).toBeVisible()
  await expect(health.getByText('Weakest')).toBeVisible()
  await health.getByRole('button', { name: 'Let Fate propose links' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /\/api\/graph\/fate-link$/).length).toBe(1)
  expect(writesTo(writes, 'POST', /\/api\/graph\/fate-link$/)[0].body).toEqual({ related: true, full: false, entity_ids: [] })
  await health.getByRole('button', { name: 'Full repair' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Repair the whole network' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /\/api\/graph\/fate-link$/).length).toBe(2)
  expect(writesTo(writes, 'POST', /\/api\/graph\/fate-link$/)[1].body).toEqual({ related: true, full: true, entity_ids: [] })
})

test('a running Fate repair can be stopped after its batch', async ({ page }) => {
  await openGraph(page)
  await replyWith(page, 'GET', /\/api\/jobs(\?.*)?$/, [
    { id: 'job-fate', kind: 'content', status: 'running', progress: 0.3, stage: 'Linking', params: { related: true, full: true }, result: null, error: null, created_at: NOW, started_at: NOW, finished_at: null },
  ])
  const writes = await captureWrites(page)
  await page.reload()
  await page.getByRole('button', { name: 'Connectivity' }).click()
  const health = page.locator('[data-network-health]')
  await health.getByRole('button', { name: 'Stop' }).click()
  await expect.poll(() => writesTo(writes, 'POST', /\/api\/graph\/fate-link\/stop$/).length).toBe(1)
  await expect(page.getByText('Fate will finish its current batch and stop.')).toBeVisible()
})

test('the 3D network renders on software WebGL with fit, rotate and re-layout controls', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await openGraph(page, '/network', '3d')
  const controls = page.locator('[data-graph-3d-controls]')
  await expect(controls).toBeVisible()
  const gl = await page.locator('[data-graph-scene] canvas').first().evaluate((node) => {
    const canvas = node as HTMLCanvasElement
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'))
  })
  expect(gl).toBe(true)
  await controls.getByRole('button', { name: 'Fit' }).click()
  const rotate = controls.getByRole('button', { name: 'Rotate' })
  const pressed = await rotate.getAttribute('aria-pressed')
  await rotate.click()
  await expect(rotate).not.toHaveAttribute('aria-pressed', pressed ?? 'false')
  await controls.getByRole('button', { name: 'Re-layout' }).click()
  await expect(controls.getByText(/double-click: page · Shift\+click: how connected · right-click: focus/)).toBeVisible()
  await selectNode(page, 'Harrowmere')
  await expect(page.locator('[data-node-info]')).toBeVisible()
  expect(errors).toEqual([])
})

test('switching from 3D back to 2D removes the 3D scene and its controls', async ({ page }) => {
  await openGraph(page, '/network', '3d')
  await expect(page.locator('[data-graph-3d-controls]')).toBeVisible()
  await page.getByRole('radiogroup', { name: 'View' }).getByRole('radio', { name: '2D' }).click()
  await expect(page.locator('[data-graph-3d-controls]')).toHaveCount(0)
  await expect(page.locator('[data-graph-scene] canvas').first()).toBeVisible()
  await expect.poll(() => stored(page, 'aerona.graph.mode')).toBe('"2d"')
})
