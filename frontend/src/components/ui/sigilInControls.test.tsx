import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { Sigil } from '@/components/domain/Sigil'
import { Button } from './button'
import { CONTROL_SIZES } from './control-size'

function filled(host: HTMLElement): boolean {
  const frame = host.querySelector('[data-testid="frame"]')
  const sigil = host.querySelector('[data-domain="sigil"]')
  if (!frame || !sigil) return false
  return (
    Math.round(sigil.getBoundingClientRect().width) ===
    Math.round(frame.getBoundingClientRect().width)
  )
}

describe('a sigil inside a control', () => {
  it.each([...CONTROL_SIZES, 'card', 'tile'] as const)(
    'fills its frame in a %s button',
    async (size) => {
      const screen = await render(
        <Button size={size} variant='outline'>
          <span data-testid='frame' className='size-portrait-lg'>
            <Sigil seed='Haluvra' />
          </span>
          Open
        </Button>
      )
      expect(filled(screen.container)).toBe(true)
    }
  )
})
