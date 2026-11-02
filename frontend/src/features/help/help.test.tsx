import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { HelpDrawer } from './HelpDrawer'
import { GLOSSARY } from './glossary'

describe('help drawer', () => {
  it('lists the fixed and navigation shortcuts', async () => {
    const { screen } = await renderScreen(<HelpDrawer />)
    await expect
      .element(screen.getByRole('heading', { name: 'Shortcuts and terms' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Search and run anything'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Ctrl K')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Close the open window'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText(/digits and \? are not shortcuts/))
      .toBeInTheDocument()
  })

  it('explains every game term in the glossary', async () => {
    const { screen } = await renderScreen(<HelpDrawer />)
    for (const name of [
      'Chronicle',
      'Codex',
      'Action ledger',
      'Divine essence',
      'Doom clock',
      'Leakage',
      'World rules',
      'Discovery mode',
    ])
      await expect
        .element(
          screen.getByLabelText('Terms').getByText(name, { exact: true })
        )
        .toBeInTheDocument()
    expect(GLOSSARY.map((entry) => entry.term)).toContain('The world’s book')
    expect(new Set(GLOSSARY.map((entry) => entry.term)).size).toBe(
      GLOSSARY.length
    )
  })
})
