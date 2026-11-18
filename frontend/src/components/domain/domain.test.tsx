import { type ReactNode } from 'react'
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from '@tanstack/react-router'
import '@/styles/index.css'
import { Crown, Sparkles } from 'lucide-react'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { page } from 'vitest/browser'
import { RARITIES } from '@/constants/rarity'
import { validateDrawerSearch } from '@/components/layout/drawer/drawerEntries'
import {
  EmptyState,
  EntityLink,
  JobProgress,
  KeyValueList,
  PageHeader,
  Portrait,
  RarityBadge,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '.'

async function renderInRouter(node: ReactNode, path = '/') {
  const rootRoute = createRootRoute({
    validateSearch: validateDrawerSearch,
    component: () => node,
  })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  const screen = await render(<RouterProvider router={router} />)
  return { screen, router }
}

describe('domain components', () => {
  it('labels every rarity with its own color token', async () => {
    const screen = await render(
      <>
        {RARITIES.map((rarity) => (
          <RarityBadge key={rarity} rarity={rarity} />
        ))}
      </>
    )
    await expect.element(screen.getByText('Mythic')).toBeInTheDocument()
    const colors = new Set(
      RARITIES.map(
        (rarity) =>
          getComputedStyle(
            document.querySelector(`[data-rarity="${rarity}"]`) as Element
          ).color
      )
    )
    expect(colors.size).toBe(RARITIES.length)
  })

  it('pushes the record onto the drawer stack', async () => {
    const { screen, router } = await renderInRouter(
      <EntityLink kind='son' id='7'>
        Ithren
      </EntityLink>,
      '/?drawer=entity:3'
    )
    await screen.getByRole('link', { name: 'Ithren' }).click()
    await expect
      .poll(() => router.state.location.search)
      .toEqual({ drawer: 'entity:3,son:7' })
  })

  it('falls back to initials when a plain portrait has no image', async () => {
    const screen = await render(<Portrait name='Ithren Unbowed' size='lg' />)
    await expect.element(screen.getByText('IU')).toBeInTheDocument()
  })

  it('falls back to a sigil when a rarity portrait has no image', async () => {
    const screen = await render(
      <Portrait name='Ithren Unbowed' size='lg' rarity='epic' />
    )
    await expect
      .element(
        screen.container.querySelector<SVGSVGElement>('[data-domain="sigil"]')
      )
      .toBeInTheDocument()
  })

  it('renders an empty state with its action', async () => {
    const screen = await render(
      <EmptyState
        icon={Sparkles}
        title='No prayers yet'
        description='They appear here when your sons wish for something.'
        action={<button type='button'>Write</button>}
      />
    )
    await expect.element(screen.getByText('No prayers yet')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Write' }))
      .toBeInTheDocument()
  })

  it('renders headers and sections as landmarks with headings', async () => {
    const screen = await render(
      <>
        <PageHeader
          title='Pantheon'
          description='Your sons.'
          icon={Crown}
          actions={<span>Act</span>}
        />
        <Section title='Sons'>
          <p>Body</p>
        </Section>
      </>
    )
    await expect
      .element(screen.getByRole('heading', { level: 1, name: 'Pantheon' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('region', { name: 'Sons' }))
      .toBeInTheDocument()
  })

  it('keeps the page title and description readable however wide the actions are', async () => {
    await page.viewport(1512, 900)
    const screen = await render(
      <div style={{ width: 700 }}>
        <PageHeader
          title='Cards'
          description='Every god, mortal, beast, spirit and place as a collectible card.'
          icon={Crown}
          actions={
            <>
              <span className='whitespace-nowrap'>Open every pack</span>
              <span className='whitespace-nowrap'>Seal every pack</span>
              <span className='whitespace-nowrap'>Card guide</span>
              <span className='whitespace-nowrap'>Binder and deck</span>
            </>
          }
        />
      </div>
    )
    await expect
      .element(screen.getByRole('heading', { level: 1, name: 'Cards' }))
      .toBeVisible()
    const description = screen
      .getByText('Every god, mortal, beast', { exact: false })
      .element()
    expect(description.getBoundingClientRect().width).toBeGreaterThan(500)
  })

  it('renders key value pairs as a description list', async () => {
    await render(<KeyValueList items={[{ label: 'Epoch', value: '12' }]} />)
    expect(document.querySelector('dt')?.textContent).toBe('Epoch')
    expect(document.querySelector('dd')?.textContent).toBe('12')
  })

  it('shows the value and the maximum of a stat bar', async () => {
    const screen = await render(
      <StatBar label='Strength' value={14} max={20} />
    )
    await expect.element(screen.getByText('14')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Strength' }))
      .toBeInTheDocument()
  })

  it('frames a stat bar like the value tiles beside it when asked', async () => {
    await render(
      <>
        <StatBar label='Bare' value={3} max={10} />
        <StatBar framed label='Framed' value={7} max={10} />
      </>
    )
    const [bare, framed] = document.querySelectorAll('[data-domain="stat-bar"]')
    expect(bare.classList.contains('surface-sheen')).toBe(false)
    expect(framed.classList.contains('surface-sheen')).toBe(true)
  })

  it('renders a timeline as an ordered list', async () => {
    await render(
      <Timeline label='History'>
        <TimelineItem icon={Crown} title='Ascended' timestamp='Epoch 12' last />
      </Timeline>
    )
    expect(document.querySelectorAll('ol > li')).toHaveLength(1)
  })

  it('shows job status, percent, stage and error', async () => {
    const screen = await render(
      <>
        <JobProgress
          job={{
            kind: 'epoch',
            status: 'running',
            progress: 0.42,
            stage: 'Sons act',
            error: null,
          }}
        />
        <JobProgress
          job={{
            kind: 'backup',
            status: 'failed',
            progress: 0.6,
            stage: null,
            error: 'Disk full',
          }}
        />
        <JobProgress
          job={{
            kind: 'image',
            status: 'queued',
            progress: 0,
            stage: null,
            error: null,
          }}
        />
      </>
    )
    await expect.element(screen.getByText('42%')).toBeInTheDocument()
    await expect.element(screen.getByText('Sons act')).toBeInTheDocument()
    await expect.element(screen.getByText('Disk full')).toBeInTheDocument()
    await expect.element(screen.getByText('Queued')).toBeInTheDocument()
    const bars = document.querySelectorAll('[data-slot="progress"]')
    expect(bars[2].getAttribute('data-state')).toBe('indeterminate')
  })
})
