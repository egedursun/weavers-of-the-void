import '@/styles/index.css'
import { describe, expect, it, vi } from 'vitest'
import { render } from 'vitest-browser-react'
import { ActionButton } from './ActionButton'

const REFUSED = {
  blockedReason: 'Viewers of Probe World cannot change the world.',
}

describe('a god action button', () => {
  it('stays visible and disabled with the reason when the role refuses its act', async () => {
    const run = vi.fn()
    const screen = await render(
      <ActionButton act={REFUSED} label='Summon an outer being' onRun={run} />
    )
    const button = screen.getByRole('button', { name: 'Summon an outer being' })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
    await button.click({ force: true })
    expect(run).not.toHaveBeenCalled()
  })

  it('refuses before its confirmation opens, not only inside it', async () => {
    const run = vi.fn()
    const screen = await render(
      <ActionButton
        act={REFUSED}
        label='End the golden age'
        confirm={{ title: 'End the golden age?', description: 'It ends now.' }}
        onRun={run}
      />
    )
    const button = screen.getByRole('button', { name: 'End the golden age' })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
    await button.click({ force: true })
    await expect
      .element(screen.getByText('End the golden age?'))
      .not.toBeInTheDocument()
    expect(run).not.toHaveBeenCalled()
  })
})
