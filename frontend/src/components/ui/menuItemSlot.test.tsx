import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './dropdown-menu'

describe('a menu item that slots onto its child', () => {
  it('renders a link item even when an act refuses it', async () => {
    const screen = await render(
      <DropdownMenu open>
        <DropdownMenuTrigger>Export</DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem asChild>
            <a href='/download/one'>Markdown</a>
          </DropdownMenuItem>
          <DropdownMenuItem
            asChild
            act={{ blockedReason: 'Viewers cannot export.' }}
          >
            <a href='/download/two'>Word</a>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
    await expect
      .element(screen.getByRole('menuitem', { name: 'Markdown' }))
      .toHaveAttribute('href', '/download/one')
    await expect
      .element(screen.getByRole('menuitem', { name: 'Word' }))
      .toHaveAttribute('aria-description', 'Viewers cannot export.')
  })
})
