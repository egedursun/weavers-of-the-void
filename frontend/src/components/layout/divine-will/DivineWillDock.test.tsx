import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import { Input } from '@/components/ui/input'
import { SidebarProvider } from '@/components/ui/sidebar'
import { useGlobalShortcuts } from '../useGlobalShortcuts'
import { DivineWillDock } from './DivineWillDock'
import { PANEL_DEFAULT_REM, PANEL_STEP_REM, useWillDock } from './dockStore'

function Harness({
  unread = 0,
  attention = false,
}: {
  unread?: number
  attention?: boolean
}) {
  useGlobalShortcuts()
  return (
    <SidebarProvider>
      <Input aria-label='Somewhere else' />
      <DivineWillDock
        running
        attention={attention}
        unread={unread}
        neighbourRem={0}
      >
        <p>Panel body</p>
      </DivineWillDock>
    </SidebarProvider>
  )
}

function reset() {
  useWillDock.setState({ open: false, width: PANEL_DEFAULT_REM, view: 'chat' })
}

beforeEach(async () => {
  reset()
  await page.viewport(1440, 900)
})
afterEach(reset)

describe('Divine Will dock', () => {
  it('shows the medallion with its signals and opens the panel', async () => {
    const { screen } = await renderScreen(<Harness unread={2} attention />)
    const orb = screen.getByRole('button', {
      name: 'Open the Divine Will, it waits for your approval, it is at work, 2 new answers',
    })
    await expect.element(orb).toHaveAttribute('data-running', 'true')
    await expect.element(orb).toHaveAttribute('data-attention', 'true')
    await orb.click()
    const panel = screen.getByRole('complementary', { name: 'The Divine Will' })
    await expect.element(panel).toBeInTheDocument()
    await expect.element(screen.getByText('Panel body')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: /^Open the Divine Will/ }))
      .not.toBeInTheDocument()
  })

  it('closes with Escape and gives the focus back to the medallion', async () => {
    useWillDock.setState({ open: true })
    const { screen } = await renderScreen(<Harness />)
    await screen.getByText('Panel body').click()
    await userEvent.keyboard('{Escape}')
    const orb = screen.getByRole('button', { name: /^Open the Divine Will/ })
    await expect.element(orb).toBeInTheDocument()
    await expect.element(orb).toHaveFocus()
  })

  it('opens and closes with the W shortcut but not while typing elsewhere', async () => {
    const { screen } = await renderScreen(<Harness />)
    await expect
      .element(screen.getByRole('button', { name: /^Open the Divine Will/ }))
      .toBeInTheDocument()
    document.body.focus()
    await userEvent.keyboard('w')
    await expect
      .element(screen.getByRole('complementary', { name: 'The Divine Will' }))
      .toBeInTheDocument()
    document.body.focus()
    await userEvent.keyboard('w')
    await expect
      .element(screen.getByRole('complementary'))
      .not.toBeInTheDocument()
    await screen.getByRole('textbox', { name: 'Somewhere else' }).click()
    await userEvent.keyboard('w')
    await expect
      .element(screen.getByRole('complementary'))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByRole('textbox', { name: 'Somewhere else' }))
      .toHaveValue('w')
  })

  it('becomes a full sheet without a resize handle on a phone', async () => {
    await page.viewport(390, 844)
    useWillDock.setState({ open: true })
    const { screen } = await renderScreen(<Harness />)
    await expect
      .element(screen.getByRole('complementary', { name: 'The Divine Will' }))
      .toHaveAttribute('data-placement', 'sheet')
    await expect.element(screen.getByRole('separator')).not.toBeInTheDocument()
  })

  it('resizes from the keyboard within its bounds', async () => {
    useWillDock.setState({ open: true })
    const { screen } = await renderScreen(<Harness />)
    const handle = screen.getByRole('separator', {
      name: 'Resize the Divine Will',
    })
    await expect
      .element(handle)
      .toHaveAttribute('aria-valuenow', String(PANEL_DEFAULT_REM))
    ;(handle.element() as HTMLElement).focus()
    await userEvent.keyboard('{ArrowLeft}')
    await expect
      .element(handle)
      .toHaveAttribute(
        'aria-valuenow',
        String(PANEL_DEFAULT_REM + PANEL_STEP_REM)
      )
    expect(useWillDock.getState().width).toBe(
      PANEL_DEFAULT_REM + PANEL_STEP_REM
    )
  })
})
