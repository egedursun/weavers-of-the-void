import '@/styles/index.css'
import { Shield } from 'lucide-react'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { KpiTile } from './KpiTile'

function lines(element: Element) {
  const range = document.createRange()
  range.selectNodeContents(element)
  return new Set(
    [...range.getClientRects()].map((rect) => Math.round(rect.top))
  ).size
}

describe('KpiTile', () => {
  it('keeps a one-word label whole when the tile is narrow', async () => {
    const screen = await render(
      <div className='grid w-60 grid-cols-2 gap-2'>
        <KpiTile label='Deterrence' value={8} icon={Shield} tone='info' />
        <KpiTile label='Fervour' value={3} icon={Shield} tone='gold' />
      </div>
    )
    for (const name of ['Deterrence', 'Fervour']) {
      const label = screen.getByText(name).element()
      expect(lines(label)).toBe(1)
      expect(label.scrollWidth).toBeLessThanOrEqual(label.clientWidth + 1)
    }
  })
})
