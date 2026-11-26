import { godRoutes } from '@/test-utils/godRoutes'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import { libraryQueryClient } from '@/api/queryClients'
import { chooseUniverse } from '@/api/universeStore'
import {
  FIRST_ID,
  universeSummary,
} from '@/features/universes/universeFixtures'
import cosmosFixture from '../../../e2e/fixtures/cosmos.json'
import { GOD_STATE } from '../../../e2e/godMocks'
import { WorldHeader } from './WorldHeader'

const LONG_STAR =
  'Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin'

function routes(overrides: Record<string, unknown> = {}) {
  return godRoutes({ 'GET /api/cosmos': cosmosFixture.cosmos, ...overrides })
}

describe('world header', () => {
  beforeEach(async () => {
    await page.viewport(1280, 900)
  })

  afterEach(() => {
    chooseUniverse(null)
    libraryQueryClient.clear()
  })

  it('names the world with its seed and shows the epoch and year', async () => {
    const { screen } = await renderScreen(<WorldHeader />, routes())
    await expect
      .element(screen.getByText('Orvael', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText('A cosmos of drowned bells.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Epoch 12, year 1' }))
      .toBeVisible()
  })

  it('names the universe as the library names it, not after its first world', async () => {
    chooseUniverse(FIRST_ID)
    const { screen } = await renderScreen(
      <WorldHeader />,
      routes({
        'GET /api/library/universes/{id}': universeSummary({
          name: 'Rakhesis',
        }),
      })
    )
    await expect
      .element(screen.getByText('Rakhesis', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText('A cosmos of drowned bells.'))
      .toBeVisible()
  })

  it('shows the star of the epoch and the climate of a world with its cycle', async () => {
    const { screen } = await renderScreen(<WorldHeader />, routes())
    const star = screen.getByRole('button', {
      name: 'The bodies that rule the sky of each world this epoch',
    })
    await expect.element(star).toHaveTextContent(LONG_STAR)
    await expect.element(screen.getByText('Rain age')).toBeVisible()
    await screen.getByText('Rain age').hover()
    await expect
      .element(screen.getByText('3 epochs left').first())
      .toBeInTheDocument()
  })

  it('opens the essence breakdown with the net total and the cost rules', async () => {
    const { screen } = await renderScreen(<WorldHeader />, routes())
    await screen
      .getByRole('button', { name: 'Divine essence 186, open breakdown' })
      .click()
    await expect.element(screen.getByText('Epoch refill')).toBeVisible()
    await expect.element(screen.getByText('+120')).toBeVisible()
    await expect.element(screen.getByText('−40')).toBeVisible()
    await expect
      .element(screen.getByRole('dialog').getByText('+80'))
      .toBeVisible()
    await expect
      .element(screen.getByText(/Essence refills every epoch/))
      .toBeVisible()
  })

  it('opens the doom clock with its bands, threshold and target world', async () => {
    const { screen } = await renderScreen(<WorldHeader />, routes())
    await screen
      .getByRole('button', { name: 'Doom clock 62, open details' })
      .click()
    await expect.element(screen.getByText('of 100')).toBeVisible()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Doom clock progress' }))
      .toBeVisible()
    await expect
      .element(screen.getByText(/The clock runs on Orvael/))
      .toBeVisible()
    await expect.element(screen.getByText('Open wars')).toBeVisible()
  })

  it('colours the creator mood and lists the four mood values', async () => {
    const { screen, router } = await renderScreen(<WorldHeader />, routes())
    const mood = screen.getByRole('button', {
      name: 'Creator mood Pleased, open the creator',
    })
    await expect.element(mood).toHaveTextContent('Pleased')
    await mood.hover()
    await expect
      .element(
        screen
          .getByText('Anger 22 · Contentment 64 · Interest 71 · Loneliness 38')
          .first()
      )
      .toBeInTheDocument()
    await mood.click()
    await expect
      .poll(() => String(router.state.location.search.entry ?? ''))
      .toContain('creator')
  })

  it('counts the prayers awaiting an answer and offers summon and revelation', async () => {
    const { screen } = await renderScreen(<WorldHeader />, routes())
    const prayers = screen.getByRole('link', {
      name: '2 prayers awaiting an answer',
    })
    await expect.element(prayers).toHaveAttribute('href', '/prayers')
    await expect
      .element(screen.getByRole('button', { name: /Summon a son/ }).first())
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /Reveal/ }).first())
      .toBeVisible()
  })

  it('disables summoning while an epoch runs', async () => {
    const { screen } = await renderScreen(
      <WorldHeader />,
      routes({ 'GET /api/state': { ...GOD_STATE, epoch_running: true } })
    )
    await expect
      .element(screen.getByRole('button', { name: /Summon a son/ }).first())
      .toHaveAttribute('aria-disabled', 'true')
    await userEvent.keyboard('{Escape}')
  })

  it('folds the status away on a phone until asked', async () => {
    await page.viewport(390, 844)
    const { screen } = await renderScreen(<WorldHeader />, routes())
    await expect
      .element(screen.getByText('Orvael', { exact: true }).first())
      .toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Epoch 12, year 1' }).elements()
    ).toHaveLength(0)
    await screen.getByRole('button', { name: 'Show world status' }).click()
    await expect
      .element(screen.getByRole('link', { name: 'Epoch 12, year 1' }))
      .toBeVisible()
  })
})
