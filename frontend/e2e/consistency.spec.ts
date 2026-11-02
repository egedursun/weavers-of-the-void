import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { type Page, expect, test } from '@playwright/test'
import { MOCK_VARIANT_COOKIE, mockApi } from './mockApi'
import { type CheckOptions, collectViolations } from './pageChecks'
import { type Interaction, SCREENS } from './screens'

const THEMES = ['dark', 'light'] as const
const SCREENSHOT_DIR = path.resolve(import.meta.dirname, 'screenshots')
const CHECK_OPTIONS: CheckOptions = { tolerancePx: 1 }
const THEME_COOKIE = 'aerona-theme'
const BROKEN_IMAGE_PATH = '/images/missing-portrait.png'

async function interact(page: Page, step: Interaction) {
  if ('see' in step) {
    await page.getByText(step.see).waitFor()
  } else if ('click' in step) {
    const dialog = page.getByRole('alertdialog')
    const scope = (await dialog.count()) > 0 ? dialog : page
    await scope
      .getByRole('button', { name: step.click })
      .or(scope.getByRole('radio', { name: step.click }))
      .last()
      .click()
  } else if ('fill' in step) {
    await page.getByLabel(step.fill.field).fill(step.fill.value)
  } else if ('choose' in step) {
    await page.getByRole('combobox', { name: step.choose.field }).click()
    await page.getByRole('option', { name: step.choose.option }).click()
  } else {
    await page.getByLabel(step.upload.field).setInputFiles({
      name: step.upload.name,
      mimeType: 'application/octet-stream',
      buffer: Buffer.from('package'),
    })
  }
}

for (const theme of THEMES) {
  for (const screen of SCREENS) {
    test(`${screen.name} is consistent in the ${theme} theme`, async ({ page, baseURL }, info) => {
      const errors: string[] = []
      page.on('pageerror', (error) => errors.push(error.message))
      page.on('console', (message) => {
        const intentional = message.location().url.endsWith(BROKEN_IMAGE_PATH)
        if (message.type() === 'error' && !intentional) errors.push(message.text())
      })
      await mockApi(page)
      await page.context().addCookies([
        { name: THEME_COOKIE, value: theme, url: baseURL ?? '' },
        ...(screen.mock
          ? [{ name: MOCK_VARIANT_COOKIE, value: screen.mock, url: baseURL ?? '' }]
          : []),
      ])
      if (screen.recordsTab) {
        await page.addInitScript((tab) => localStorage.setItem('aerona.records-tab', tab), screen.recordsTab)
      }
      await page.goto(screen.path)
      await page.waitForLoadState('networkidle')
      if (screen.openPalette) {
        await page.keyboard.press('Control+k')
        await expect(page.getByRole('dialog')).toBeVisible()
      }
      if (screen.toggleSidebar) {
        await page.getByRole('button', { name: 'Toggle Sidebar' }).first().click()
      }
      for (const step of screen.interact ?? []) await interact(page, step)
      if (screen.interact) {
        await expect(page.locator('[data-sonner-toast]')).toHaveCount(0, { timeout: 15_000 })
        await page.evaluate(() => {
          window.scrollTo(0, 0)
          document.querySelectorAll('*').forEach((element) => {
            if (element.scrollTop > 0) element.scrollTop = 0
          })
        })
      }
      await page.evaluate(() => document.fonts.ready)
      await page.waitForFunction(() =>
        document
          .getAnimations()
          .every((animation) => animation.playState !== 'running')
      )
      const directory = path.join(SCREENSHOT_DIR, info.project.name, theme)
      mkdirSync(directory, { recursive: true })
      await page.screenshot({
        path: path.join(directory, `${screen.name}.png`),
        fullPage: !screen.openPalette && !screen.toggleSidebar && !screen.path.includes('drawer='),
      })
      const violations = await page.evaluate(collectViolations, CHECK_OPTIONS)
      expect(violations, JSON.stringify(violations, null, 2)).toEqual([])
      expect(errors, errors.join('\n')).toEqual([])
    })
  }
}
