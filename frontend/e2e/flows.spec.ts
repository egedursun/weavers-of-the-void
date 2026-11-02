import { type Page, type Route, expect, test } from '@playwright/test'
import { MOCK_VARIANT_COOKIE, mockApi } from './mockApi'

const NOW = new Date().toISOString()

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

async function journal(page: Page, events: { id: number; kind: string; payload: Record<string, unknown> }[]) {
  await page.route('**/api/activity-log', (route) =>
    json(route, events.map((event) => ({ ...event, at: NOW })))
  )
}

async function setVariant(page: Page, baseURL: string | undefined, variant: string) {
  await page.context().addCookies([{ name: MOCK_VARIANT_COOKIE, value: variant, url: baseURL ?? '' }])
}

test('completing an epoch shows progress and stops at a safe point', async ({ page }) => {
  await mockApi(page)
  const calls: string[] = []
  await page.route('**/api/epochs/current/complete', (route) => {
    calls.push('complete')
    return json(route, { job_id: 'job-epoch' })
  })
  await page.route('**/api/epochs/current/stop', (route) => {
    calls.push('stop')
    return json(route, { message: 'Stopping after phase 2.' })
  })
  await journal(page, [
    { id: 1, kind: 'epoch.started', payload: { epoch: 8, resuming: false } },
    { id: 2, kind: 'epoch.progress', payload: { epoch: 8, no: 2, total: 5, name: 'Engine', elapsed_s: 4 } },
  ])
  await page.goto('/epoch')
  const strip = page.locator('[data-feature="epoch-progress"]').first()
  await expect(strip).toBeVisible()
  await expect(strip.getByText('Epoch 8')).toBeVisible()
  await expect(strip.getByText('40%')).toBeVisible()
  await expect(strip.getByText(/Phase 2\/5: Engine/)).toBeVisible()
  await page.getByRole('button', { name: 'Stop', exact: true }).first().click()
  await page.getByRole('button', { name: 'Stop at a safe point' }).click()
  await expect(page.getByText('Stopping after phase 2.')).toBeVisible()
  expect(calls).toContain('stop')
})

test('the complete epoch button starts the epoch', async ({ page }) => {
  await mockApi(page)
  let completed = 0
  await page.route('**/api/epochs/current/complete', (route) => {
    completed += 1
    return json(route, { job_id: 'job-epoch' })
  })
  await page.goto('/')
  await page.getByRole('button', { name: /Complete the epoch|Resume epoch/ }).first().click()
  await expect(page.getByText(/The epoch (begins|resumes)/)).toBeVisible()
  expect(completed).toBe(1)
})

test('the genesis wizard walks its steps and fixes the lore language', async ({ page, baseURL }) => {
  await mockApi(page)
  await setVariant(page, baseURL, 'empty')
  let body: Record<string, unknown> | null = null
  await page.route('**/api/genesis', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    body = route.request().postDataJSON() as Record<string, unknown>
    return json(route, { job_id: 'genesis-1' })
  })
  await page.goto('/genesis')
  await page.getByRole('button', { name: 'Dark fantasy' }).or(page.getByRole('radio', { name: 'Dark fantasy' })).last().click()
  await page.getByRole('button', { name: 'Next' }).click()
  await expect(page.getByText('Chosen once, forever')).toBeVisible()
  await expect(page.getByText('It cannot be changed afterwards.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next' })).toHaveAttribute('aria-description', 'Give the Creator a name.')
  await page.getByLabel('Name of the Creator').fill('Aeron')
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('button', { name: 'Next' }).click()
  await expect(page.getByRole('heading', { name: 'First sons' })).toBeVisible()
  await expect(page.getByText('Lore language')).toBeVisible()
  await page.getByRole('button', { name: 'Create the world' }).click()
  await expect(page.getByText('The world is being thought').first()).toBeVisible()
  expect(body).toMatchObject({ creator_name: 'Aeron', lore_language: 'english' })
})

test('world rules reject an edit with a constraint error from the server', async ({ page }) => {
  await mockApi(page)
  await page.route('**/api/rules/**', (route) => {
    if (route.request().method() !== 'PUT') return route.fallback()
    return json(route, { detail: 'balance.doom_threshold must stay above apocalypse.warning_2_pct' }, 422)
  })
  await page.goto('/settings/world-rules?q=doom')
  const field = page.locator('[id="rule-balance.doom_threshold"]')
  await field.fill('50')
  await page.getByRole('button', { name: 'Save 1 changes' }).click()
  await expect(page.getByRole('alert').first()).toContainText('must stay above apocalypse.warning_2_pct')
  await expect(page.locator('[id="rule-balance.doom_threshold-error"]')).toBeVisible()
})

test('the ledger undoes a page and lists the conflicts', async ({ page }) => {
  await mockApi(page)
  await page.route('**/api/ledger/88/undo', (route) =>
    json(route, { entry_id: 88, applied: ['changed: son essence 80 → 40'], conflicts: ['bond 12 was already removed'] })
  )
  await page.goto('/ledger')
  await expect(page.getByText(/The next page touched what this one created: #91/)).toBeVisible()
  await page.getByRole('button', { name: 'Undo', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: 'Undo page #88?' })).toBeVisible()
  await page.getByRole('button', { name: 'Undo anyway' }).click()
  await expect(page.getByText('Undone: 1 change reverted, 1 conflict skipped').first()).toBeVisible()
  await expect(page.getByText('bond 12 was already removed').first()).toBeVisible()
})

test('a backup restores only after typing RESTORE', async ({ page }) => {
  await mockApi(page)
  let restored: unknown = null
  await page.route('**/api/backups/restore', (route) => {
    restored = route.request().postDataJSON()
    return json(route, { ok: true, safety_backup: 'safety-1.db' })
  })
  await page.goto('/settings/data')
  await page.getByRole('button', { name: 'Restore' }).first().click()
  const confirm = page.getByRole('alertdialog').getByRole('button', { name: 'Restore' })
  await expect(confirm).toBeDisabled()
  await page.getByLabel('Type RESTORE to confirm').fill('restore')
  await expect(confirm).toBeDisabled()
  await page.getByLabel('Type RESTORE to confirm').fill('RESTORE')
  await confirm.click()
  await expect(page.getByText(/Safety copy: safety-1.db/)).toBeVisible()
  expect(restored).toEqual({ file: 'epoch-0006.db', confirm: 'RESTORE' })
})

test('discovery mode shows the read-only banner and blocks changes', async ({ page, baseURL }) => {
  await mockApi(page)
  await setVariant(page, baseURL, 'discovery')
  await page.goto('/settings/data')
  const banner = page.locator('[data-layout="discovery-banner"]')
  await expect(banner).toBeVisible()
  await expect(banner).toContainText('Discovery mode')
  await expect(banner).toContainText('read-only')
  await expect(page.getByRole('button', { name: 'Take a backup now' })).toBeDisabled()
  await expect(banner.getByRole('button', { name: 'Return to my world' })).toBeVisible()
})

test('the command palette runs an action', async ({ page }) => {
  await mockApi(page)
  let taken = 0
  await page.route('**/api/backups', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    taken += 1
    return json(route, { file: 'manual.db', size: 1, modified: NOW, label: 'Manual' })
  })
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.keyboard.press('Control+k')
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByPlaceholder(/Search the world/).fill('backup')
  await page.getByRole('option', { name: 'Take a backup now' }).click()
  await expect(page.getByText('Backup taken')).toBeVisible()
  expect(taken).toBe(1)
})

test('notifications toggle between read and unread and mark a category read', async ({ page }) => {
  await mockApi(page)
  const reads: unknown[] = []
  await page.route('**/api/notifications/read', (route) => {
    reads.push(route.request().postDataJSON())
    return json(route, { changed: 1 })
  })
  await page.goto('/notifications')
  const first = page.locator('[data-notification="300"]')
  await expect(first).toBeVisible()
  await first.getByRole('button', { name: 'Mark read' }).click()
  await expect.poll(() => reads.length).toBe(1)
  expect(reads[0]).toEqual({ ids: [300], every: false, unread: false })
  const read = page.locator('[data-notification="299"]')
  await read.getByRole('button', { name: 'Mark unread' }).click()
  await expect.poll(() => reads.length).toBe(2)
  expect(reads[1]).toEqual({ ids: [299], every: false, unread: true })
  await page.getByRole('button', { name: 'Mark all read' }).click()
  await expect(page.getByText('1 marked read')).toBeVisible()
})
