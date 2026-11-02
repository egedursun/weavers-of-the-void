import { expect, test } from '@playwright/test'
import { type CheckOptions, collectViolations } from './pageChecks'

const OPTIONS: CheckOptions = { tolerancePx: 1 }

const TOKENS = `
  :root {
    --control-height-sm: 32px;
    --control-height-md: 36px;
    --control-height-lg: 44px;
    --control-font-size: 14px;
    --spacing-badge-sm: 20px;
    --spacing-badge-md: 24px;
    --display-font-size: 36px;
    --text-title: 20px;
    --text-body: 14px;
    --text-prose: 16px;
    --text-caption: 12px;
    --text-overline: 11px;
    --text-kpi: 24px;
  }
  body { margin: 0; font: 14px sans-serif; }
`

async function violationsOf(page: import('@playwright/test').Page, body: string) {
  await page.setContent(`<html><head><style>${TOKENS}</style></head><body>${body}</body></html>`)
  return page.evaluate(collectViolations, OPTIONS)
}

test('a clean page has no violations', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="display:flex;gap:8px">
      <button data-control-size="default" style="height:36px;font-size:14px">Go</button>
      <input data-control-size="default" style="height:36px;font-size:14px;box-sizing:border-box" />
    </div>
    <p data-typography="body" style="font-size:14px">Body</p>`
  )
  expect(violations).toEqual([])
})

test('detects a control that is taller than its size', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<button data-control-size="default" style="height:40px;font-size:14px">Go</button>`
  )
  expect(violations.map((item) => item.rule)).toContain('control-height')
})

test('detects a control with the wrong font size and a wrong text role size', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<button data-control-size="sm" style="height:32px;font-size:16px">Go</button>
     <p data-typography="caption" style="font-size:14px">Caption</p>`
  )
  expect(violations.map((item) => item.rule)).toEqual(
    expect.arrayContaining(['control-font-size', 'typography-size'])
  )
})

test('detects overlapping text', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="position:relative;height:40px">
      <span style="position:absolute;left:0;top:0">Overlapping words</span>
      <span style="position:absolute;left:10px;top:4px">Collide here</span>
    </div>`
  )
  expect(violations.map((item) => item.rule)).toContain('text-overlap')
})

test('detects an icon on top of text', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="position:relative">
      <span>Summon a son</span>
      <svg style="position:absolute;left:4px;top:0;width:16px;height:16px"></svg>
    </div>`
  )
  expect(violations.map((item) => item.rule)).toContain('icon-text-overlap')
})

test('detects horizontal overflow', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="width:100px"><div style="width:4000px;height:10px;background:red"></div></div>`
  )
  expect(violations.map((item) => item.rule)).toEqual(
    expect.arrayContaining(['page-horizontal-overflow', 'element-outside-viewport'])
  )
})

test('ignores text clipped by an ellipsis', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="display:flex;width:300px;gap:8px">
      <span style="width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">A very long name that is cut</span>
      <span>Neighbour</span>
    </div>`
  )
  expect(violations).toEqual([])
})

test('detects content spilling out of its box', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="width:300px"><div style="width:100px"><div style="width:200px;height:10px;background:red"></div></div></div>`
  )
  expect(violations.map((item) => item.rule)).toContain('content-overflows-box')
})

test('ignores content that an ancestor clips', async ({ page }) => {
  const violations = await violationsOf(
    page,
    `<div style="width:100px;overflow:hidden"><div style="width:100px"><div style="width:200px;height:10px;background:red"></div></div></div>`
  )
  expect(violations).toEqual([])
})
