import { type Page, expect, test } from '@playwright/test'
import { replyWith } from './capture'
import { mockApi } from './mockApi'
import { SOFTWARE_WEBGL } from './softwareWebgl'

const VIEW_KEY = 'aerona.cosmos.view'
const QUALITY_KEY = 'aerona.cosmos.quality'
const FEED_KEY = 'aerona.feed'
const SCENE = 'Cosmos: stars, worlds and routes'
const LABEL_REACH_PX = 8
const PAUSED_FRAMES = 20

type Point = { x: number; y: number }

test.use({ ...SOFTWARE_WEBGL, viewport: { width: 1440, height: 1400 } })

test.beforeEach(({ browserName }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile' || browserName !== 'chromium', 'The 3D scene runs once on the desktop project')
})

async function open3d(page: Page, url = '/cosmos', quality?: string) {
  await mockApi(page)
  await page.addInitScript(
    ({ view, feed, qualityKey, preset }) => {
      window.localStorage.setItem(view, '3d')
      window.localStorage.setItem(feed, JSON.stringify({ state: { open: false, sounds: false, ambient: false, muted: [] }, version: 0 }))
      if (preset) window.localStorage.setItem(qualityKey, preset)
    },
    { view: VIEW_KEY, feed: FEED_KEY, qualityKey: QUALITY_KEY, preset: quality }
  )
  await page.goto(url)
  await expect(page.locator(`[aria-label="${SCENE}"] canvas`)).toBeVisible()
  await expect(page.getByRole('radio', { name: '3D view' })).toHaveAttribute('aria-checked', 'true')
}

function labelOf(page: Page, name: string) {
  return page.locator('[aria-hidden="true"] > div').filter({ has: page.getByText(name, { exact: true }) }).first()
}

async function labelBox(page: Page, name: string) {
  const label = labelOf(page, name)
  await expect.poll(async () => label.evaluate((node) => (node as HTMLElement).style.transform), { timeout: 15000 }).toContain('translate3d')
  const box = await label.boundingBox()
  if (!box) throw new Error(`no label for ${name}`)
  return box
}

async function pointOf(page: Page, name: string): Promise<Point> {
  const box = await labelBox(page, name)
  return { x: box.x + box.width / 2, y: box.y - LABEL_REACH_PX }
}

async function hover(page: Page, point: Point) {
  await page.mouse.move(point.x, point.y)
  await page.mouse.move(point.x + 1, point.y)
}

async function transformOf(page: Page, name: string) {
  return labelOf(page, name).evaluate((node) => (node as HTMLElement).style.transform)
}

function waitFrames(page: Page, count: number) {
  return page.evaluate(
    (total) =>
      new Promise<void>((resolve) => {
        let seen = 0
        const tick = () => {
          seen += 1
          if (seen < total) requestAnimationFrame(tick)
          else resolve()
        }
        requestAnimationFrame(tick)
      }),
    count
  )
}

test('the 3D scene starts on software WebGL with its help line, legend and quality presets', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await open3d(page)
  const canvas = page.locator(`[aria-label="${SCENE}"] canvas`)
  const size = await canvas.evaluate((node) => {
    const element = node as HTMLCanvasElement
    return { context: Boolean(element.getContext('webgl2')), width: element.width, css: element.clientWidth }
  })
  expect(size.context).toBe(true)
  expect(size.width).toBeGreaterThan(0)
  await expect(page.getByText(/Drag: rotate · right-drag: pan · wheel: zoom/)).toBeVisible()
  await expect(page.getByText(/This browser cannot draw the 3D sky/)).toHaveCount(0)
  await expect(page.getByLabel('Route legend')).toBeVisible()
  await expect(page.getByRole('combobox', { name: '3D quality' })).toHaveText('Low quality')
  await expect(page.getByRole('combobox', { name: '3D quality' })).toHaveAttribute('title', /draws without a graphics card/)
  await page.getByRole('combobox', { name: '3D quality' }).click()
  await page.getByRole('option', { name: 'High' }).click()
  await expect.poll(() => page.evaluate((key) => window.localStorage.getItem(key), QUALITY_KEY)).toBe('high')
  await expect(canvas).toBeVisible()
  const highWidth = await canvas.evaluate((node) => (node as HTMLCanvasElement).width)
  await page.getByRole('combobox', { name: '3D quality' }).click()
  await page.getByRole('option', { name: 'Low' }).click()
  await expect.poll(() => canvas.evaluate((node) => (node as HTMLCanvasElement).width)).toBeLessThanOrEqual(highWidth)
  expect(errors).toEqual([])
})

test('the scene falls back to 2D when WebGL 2 is missing and remembers the view', async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string, ...rest: unknown[]) {
      if (kind === 'webgl2') return null
      return (original as (...args: unknown[]) => unknown).call(this, kind, ...rest)
    } as typeof HTMLCanvasElement.prototype.getContext
    window.localStorage.setItem('aerona.cosmos.view', '3d')
  })
  await page.goto('/cosmos')
  await expect(page.getByRole('group', { name: SCENE })).toBeVisible()
  await expect(page.getByRole('radio', { name: '3D view' })).toBeDisabled()
  await expect(page.getByText(/This browser cannot draw the 3D sky \(WebGL 2 is not available in this browser\)/)).toBeVisible()
})

test('an empty cosmos shows the silent void overlay in 3D', async ({ page }) => {
  await open3d(page)
  await replyWith(page, 'GET', /\/api\/cosmos$/, { stars: [], worlds: [], foreign_gods: [], routes: [], journeys: [], sky_events: [], world_types: [], places: [], communities: [] })
  await page.reload()
  await expect(page.getByText('The void is still silent.')).toBeVisible()
  await expect(page.getByText('It will shine here when the first star ignites.')).toBeVisible()
})

test('world and star labels carry their kind, discovery and planet count', async ({ page }) => {
  await open3d(page)
  await expect(labelOf(page, 'Velar Sun')).toContainText('Yellow dwarf · 3 worlds')
  await expect(labelOf(page, 'Pell')).toContainText('Ice world · legend')
  await expect(labelOf(page, 'Ashen Reach')).toContainText('Unknown world')
  await expect(labelOf(page, 'Hollow Choir')).toContainText('Forgotten')
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Ark of Thessaly' }).click()
  await expect.poll(() => labelOf(page, 'Ark of Thessaly').evaluate((node) => (node as HTMLElement).style.visibility), { timeout: 15000 }).toBe('visible')
})

test('hovering a world shows its card tip and clicking selects it in the side panel', async ({ page }) => {
  await open3d(page, '/cosmos?world=6')
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Velar' }).click()
  const velar = await pointOf(page, 'Velar')
  await hover(page, velar)
  const tip = page.getByRole('tooltip').filter({ hasText: 'Click: card · double-click: descend to its map' })
  await expect(tip).toBeVisible()
  await expect(tip).toContainText('Velar')
  await expect(tip).toContainText(/souls · \d+ regions · atmosphere/)
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Oru' }).click()
  await expect(page.locator('article[data-world-id="6"]')).toBeVisible()
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Velar' }).click()
  await expect(page.locator('article[data-world-id="3"]')).toBeVisible()
  await page.goto('/cosmos?world=6')
  await expect(page.locator('article[data-world-id="6"]')).toBeVisible()
  const target = await reachableWorld(page, ['Brightmoor', 'Ark of Thessaly', 'Velar', 'Shattered Ring', 'Ashen Reach'])
  await page.mouse.click(target.point.x, target.point.y)
  await expect(page.locator(`article[data-world-id="${target.id}"]`)).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`world=${target.id}`))
})

const MIREVAST = 'Mirevast, the Drowned Lantern of Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin'
const WORLD_IDS: Record<string, number> = { [MIREVAST]: 5, Velar: 3, Brightmoor: 12, 'Ark of Thessaly': 13, 'Shattered Ring': 14, 'Ashen Reach': 8 }

async function reachableWorld(page: Page, names: string[]) {
  for (const name of names) {
    const point = await pointOf(page, name)
    await hover(page, point)
    const tip = page.getByRole('tooltip').filter({ hasText: 'Click: card · double-click' })
    const text = (await tip.count()) > 0 ? await tip.first().textContent() : ''
    if (text?.startsWith(name)) return { id: WORLD_IDS[name], point }
  }
  throw new Error('no world could be reached under its label')
}

test('a world with a contacted foreign god and leakage names them in its tip', async ({ page }) => {
  await open3d(page)
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: /^Mirevast/ }).click()
  await reachableWorld(page, [MIREVAST])
  const tip = page.getByRole('tooltip').filter({ hasText: 'Click: card · double-click' })
  await expect(tip).toContainText('Foreign god: Ulmaresh')
  await expect(tip).toContainText('leakage 46')
})

test('clicking a star opens its card in the Star tab', async ({ page }) => {
  await open3d(page)
  const box = await labelBox(page, 'Keth Beacon')
  const point = { x: box.x + box.width / 2, y: box.y - LABEL_REACH_PX }
  await hover(page, point)
  await expect(page.getByRole('tooltip').filter({ hasText: 'Keth Beacon' })).toBeVisible()
  await page.mouse.click(point.x, point.y)
  await expect(page.getByRole('tab', { name: 'Star' })).toHaveAttribute('data-state', 'active')
  await expect(page.locator('article[data-star-id="11"]')).toBeVisible()
})

test('double-clicking a world descends to its map', async ({ page }) => {
  await open3d(page)
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Velar' }).click()
  const velar = await pointOf(page, 'Velar')
  await page.mouse.dblclick(velar.x, velar.y)
  await expect(page).toHaveURL(/\/map\?world=3/)
})

test('choosing a world flies the camera to it and the orbit controls rotate and zoom the scene', async ({ page }) => {
  await open3d(page)
  const before = await transformOf(page, 'Velar Sun')
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Brightmoor' }).click()
  await expect.poll(() => transformOf(page, 'Velar Sun')).not.toBe(before)
  const canvas = page.locator(`[aria-label="${SCENE}"] canvas`)
  const box = await canvas.boundingBox()
  if (!box) throw new Error('canvas has no box')
  const centre = { x: box.x + box.width / 2, y: box.y + box.height / 2 }
  const flown = await transformOf(page, 'Keth Beacon')
  await page.mouse.move(centre.x, centre.y)
  await page.mouse.down()
  await page.mouse.move(centre.x + 120, centre.y + 30, { steps: 8 })
  await page.mouse.up()
  await expect.poll(() => transformOf(page, 'Keth Beacon')).not.toBe(flown)
  const rotated = await transformOf(page, 'Keth Beacon')
  await page.mouse.move(centre.x, centre.y)
  await page.mouse.wheel(0, -400)
  await expect.poll(() => transformOf(page, 'Keth Beacon')).not.toBe(rotated)
})

test('son avatars float above their world and open the son drawer', async ({ page }) => {
  await open3d(page)
  await page.getByRole('radiogroup', { name: 'Choose a world' }).getByRole('radio', { name: 'Velar' }).click()
  const avatar = page.getByRole('button', { name: /^Ithren.* on Velar$/ })
  await expect(avatar).toHaveCount(1)
  await expect.poll(() => avatar.evaluate((node) => (node.parentElement as HTMLElement).style.visibility), { timeout: 15000 }).toBe('visible')
  await avatar.click()
  await expect(page).toHaveURL(/drawer=son/)
})

test('the scene pauses when the tab is hidden and resumes when it returns', async ({ page }) => {
  await open3d(page)
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  const label = await transformOf(page, 'Velar Sun')
  const canvas = page.locator(`[aria-label="${SCENE}"] canvas`)
  const box = await canvas.boundingBox()
  if (!box) throw new Error('canvas has no box')
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await page.mouse.wheel(0, -400)
  await waitFrames(page, PAUSED_FRAMES)
  expect(await transformOf(page, 'Velar Sun')).toBe(label)
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await page.mouse.wheel(0, -400)
  await expect.poll(() => transformOf(page, 'Velar Sun')).not.toBe(label)
})
