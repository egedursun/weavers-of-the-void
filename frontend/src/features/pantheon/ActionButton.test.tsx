import { describe, expect, it, vi } from 'vitest'
import { render } from 'vitest-browser-react'
import { userEvent } from 'vitest/browser'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ActionButton } from './ActionButton'

describe('ActionButton', () => {
  it('runs directly and shows the essence cost', async () => {
    const onRun = vi.fn()
    const screen = await render(
      <ActionButton label='Bless' cost={15} onRun={onRun} />
    )
    await expect.element(screen.getByText('15')).toBeInTheDocument()
    await screen.getByRole('button', { name: /Bless/ }).click()
    expect(onRun).toHaveBeenCalledOnce()
  })

  it('explains why it is blocked and does not run', async () => {
    const onRun = vi.fn()
    const screen = await render(
      <TooltipProvider>
        <ActionButton
          label='Kill'
          blocked='100 essence needed; you have 4.'
          onRun={onRun}
        />
      </TooltipProvider>
    )
    const button = screen.getByRole('button', { name: /Kill/ })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(button)
      .toHaveAttribute('aria-description', '100 essence needed; you have 4.')
    await button.click({ force: true })
    expect(onRun).not.toHaveBeenCalled()
  })

  it('asks for confirmation and the typed word before running', async () => {
    const onRun = vi.fn()
    const screen = await render(
      <ActionButton
        label='Merge'
        variant='destructive'
        confirm={{
          title: 'Merge the records?',
          description: 'Both become one.',
          word: 'MERGE',
        }}
        onRun={onRun}
      />
    )
    await screen.getByRole('button', { name: /Merge/ }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Merge the records?' }))
      .toBeInTheDocument()
    const confirm = screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Merge' })
    await expect.element(confirm).toBeDisabled()
    await userEvent.type(
      screen.getByLabelText('Type MERGE to confirm'),
      'MERGE'
    )
    await confirm.click()
    expect(onRun).toHaveBeenCalledOnce()
  })

  it('shows a gain instead of a cost', async () => {
    const screen = await render(
      <ActionButton label='Drain' gain={40} onRun={vi.fn()} />
    )
    await expect.element(screen.getByText('+40')).toBeInTheDocument()
  })
})
