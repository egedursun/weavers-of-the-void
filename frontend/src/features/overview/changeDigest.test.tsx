import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { ChangeDigestPanel } from './ChangeDigestPanel'

const NARROW = 'w-72'
const WIDE = 'w-3xl'

function changes(version: string, extra: Record<string, unknown> = {}) {
  return {
    full: false,
    version,
    entities: [],
    removed_entity_ids: [],
    sons: [],
    removed_son_ids: [],
    new_chronicle_lines: 0,
    bonds_changed: false,
    cosmos_changed: false,
    worlds_changed: false,
    relations_changed: false,
    foreign_god_ids: [],
    ...extra,
  }
}

async function openDigest(width: string) {
  let calls = 0
  const rendered = await renderScreen(
    <div className={width}>
      <ChangeDigestPanel />
    </div>,
    {
      'GET /api/changes': () => {
        calls += 1
        return calls === 1
          ? changes('v1')
          : changes('v2', { new_chronicle_lines: 19, bonds_changed: true })
      },
    }
  )
  await expect.poll(() => calls).toBe(1)
  await rendered.queryClient.invalidateQueries()
  await expect
    .element(rendered.screen.getByText('Changed', { exact: true }))
    .toBeVisible()
  return rendered
}

function tiles(): HTMLElement[] {
  return [...document.querySelectorAll<HTMLElement>('li')]
}

describe('change digest', () => {
  it('stacks the tiles in a narrow panel and keeps every chip inside its tile', async () => {
    await openDigest(NARROW)
    const items = tiles()
    expect(items.length).toBe(2)
    expect(items[0].getBoundingClientRect().left).toBe(
      items[1].getBoundingClientRect().left
    )
    for (const item of items) {
      const box = item.getBoundingClientRect()
      for (const child of item.children) {
        const inner = child.getBoundingClientRect()
        expect(inner.left).toBeGreaterThanOrEqual(box.left)
        expect(inner.right).toBeLessThanOrEqual(box.right)
      }
    }
  })

  it('places the tiles side by side when the panel is wide', async () => {
    await openDigest(WIDE)
    const [first, second] = tiles()
    expect(first.getBoundingClientRect().top).toBe(
      second.getBoundingClientRect().top
    )
  })
})
