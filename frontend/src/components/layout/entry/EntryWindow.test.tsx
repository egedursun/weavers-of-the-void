import { renderScreen } from '@/test-utils/renderScreen'
import { beforeEach, describe, expect, it } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import { Section } from '@/components/domain'
import { PageTitle, Text } from '@/components/typography'
import {
  type EntryPageProps,
  type EntryPages,
  EntryWindow,
} from './EntryWindow'
import { ENTRY_KINDS } from './entryStack'

function FakePage({ id }: EntryPageProps) {
  const name = id === '2' ? 'Bek of the Ford' : 'Orla Vane'
  return (
    <article className='flex min-w-0 flex-col gap-6'>
      <PageTitle>{name}</PageTitle>
      <Section id='section-facts' title='Facts'>
        <Text>Born in the third epoch</Text>
      </Section>
      <Section id='section-biography' title='Biography'>
        <Text>A long life</Text>
      </Section>
      <Section id='section-stats' title='Stats'>
        <Text>Strength 40</Text>
      </Section>
      <Section id='section-images' title='Images'>
        <Text>No image yet</Text>
      </Section>
      <Section id='section-note' title='Note'>
        <Text>Kept by the god</Text>
      </Section>
      <Section id='section-kin' title='Kin'>
        <Text>Mother of three daughters</Text>
      </Section>
      <Section id='section-body' title='Body'>
        <Text>A scar across the brow of the hero</Text>
      </Section>
      <Section id='section-mechanics' title='Mechanics'>
        <Text>Hold the whole record</Text>
      </Section>
    </article>
  )
}

const PAGES = Object.fromEntries(
  ENTRY_KINDS.map((kind) => [kind, FakePage])
) as EntryPages

function entryOf(router: { state: { location: { search: unknown } } }) {
  return (router.state.location.search as { entry?: string }).entry
}

describe('entry window', () => {
  beforeEach(async () => {
    await page.viewport(1400, 900)
  })

  it('opens one large window with the parts of the entry and starts on its overview', async () => {
    const { screen } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1'
    )
    await expect
      .element(screen.getByRole('dialog', { name: 'Orla Vane' }))
      .toBeVisible()
    const rail = screen.getByRole('navigation', {
      name: 'Contents of this entry',
    })
    await expect
      .element(rail.getByRole('button', { name: /^Overview/ }))
      .toHaveAttribute('aria-pressed', 'true')
    await expect
      .element(rail.getByRole('button', { name: /^Life & kin/ }))
      .toBeVisible()
    await expect
      .element(rail.getByRole('button', { name: /^God's controls/ }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Born in the third epoch'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Mother of three daughters'))
      .not.toBeVisible()
  })

  it('shows only the chosen part and everything on demand', async () => {
    const { screen } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1'
    )
    const rail = screen.getByRole('navigation', {
      name: 'Contents of this entry',
    })
    await rail.getByRole('button', { name: /^Life & kin/ }).click()
    await expect
      .element(screen.getByText('Mother of three daughters'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Born in the third epoch'))
      .not.toBeVisible()
    await rail.getByRole('button', { name: /^Everything/ }).click()
    await expect
      .element(screen.getByText('Born in the third epoch'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Hold the whole record'))
      .toBeVisible()
  })

  it('finds a value inside a section of another part and jumps to it', async () => {
    const { screen } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1'
    )
    const search = screen.getByRole('searchbox', { name: 'Search this entry' })
    await search.fill('scar')
    const match = screen.getByRole('option').first()
    await expect.element(match).toHaveTextContent('A scar across the brow')
    await match.click()
    await expect
      .element(screen.getByRole('region', { name: 'Body' }))
      .toBeVisible()
  })

  it('opens the section a link names', async () => {
    const { screen } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1&at=section-kin'
    )
    await expect
      .element(screen.getByText('Mother of three daughters'))
      .toBeVisible()
  })

  it('goes back and forward through the entries opened inside it', async () => {
    const { screen, router } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1,entity:2'
    )
    await expect
      .element(screen.getByRole('dialog', { name: 'Bek of the Ford' }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Back' }).click()
    await expect.poll(() => entryOf(router)).toBe('entity:1')
    await expect
      .element(screen.getByRole('dialog', { name: 'Orla Vane' }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Forward' }).click()
    await expect.poll(() => entryOf(router)).toBe('entity:1,entity:2')
  })

  it('focuses the search with slash and clears it with escape before closing', async () => {
    const { screen, router } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1'
    )
    await expect
      .element(screen.getByRole('dialog', { name: 'Orla Vane' }))
      .toBeVisible()
    await screen.getByText('Born in the third epoch').click()
    await userEvent.keyboard('/')
    const search = screen.getByRole('searchbox', { name: 'Search this entry' })
    await expect.element(search).toHaveFocus()
    await userEvent.keyboard('kin')
    await userEvent.keyboard('{Escape}')
    await expect.element(search).toHaveValue('')
    await expect.poll(() => entryOf(router)).toBe('entity:1')
    await userEvent.keyboard('{Escape}')
    await expect.poll(() => entryOf(router)).toBeUndefined()
  })

  it('jumps to the god controls from the header', async () => {
    const { screen } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {},
      '/?entry=entity:1'
    )
    await screen
      .getByRole('button', { name: /^God's controls/ })
      .first()
      .click()
    await expect
      .element(screen.getByText('Hold the whole record'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Born in the third epoch'))
      .not.toBeVisible()
  })
})
