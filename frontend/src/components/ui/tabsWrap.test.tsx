import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { Tabs, TabsList, TabsTrigger } from './tabs'

const NAMES = ['Ledger', 'Notes', 'Bookmarks', 'Proposals', 'Waiting acts']

describe('a tab list on a narrow screen', () => {
  it('wraps every tab into view instead of hiding some', async () => {
    const screen = await render(
      <div data-testid='frame' className='w-portrait-2xl'>
        <Tabs defaultValue='Ledger'>
          <TabsList aria-label='Records' className='w-full'>
            {NAMES.map((name) => (
              <TabsTrigger key={name} value={name}>
                {name}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
    )
    const frame = screen.container
      .querySelector('[data-testid="frame"]')
      ?.getBoundingClientRect()
    expect(frame).toBeDefined()
    const tabs = [...screen.container.querySelectorAll('[role="tab"]')]
    expect(tabs).toHaveLength(NAMES.length)
    for (const tab of tabs) {
      const box = tab.getBoundingClientRect()
      expect(box.right).toBeLessThanOrEqual((frame?.right ?? 0) + 1)
      expect(box.left).toBeGreaterThanOrEqual((frame?.left ?? 0) - 1)
    }
  })
})
