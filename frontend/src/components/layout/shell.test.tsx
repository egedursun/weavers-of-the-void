import { type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { RealtimeProvider } from '@/realtime'
import '@/styles/index.css'
import { FakeEventSource } from '@/test-utils/fakeEventSource'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { page } from 'vitest/browser'
import { TooltipProvider } from '@/components/ui/tooltip'
import { LiveFeedDock } from '@/features/feed/LiveFeedDock'
import { LiveFeedSheet } from '@/features/feed/LiveFeedSheet'
import { useFeedPreferences } from '@/features/feed/feedStore'
import { useFeedOverlay } from '@/features/feed/useFeedDock'
import { WorldSwitcher } from './WorldSwitcher'
import { nextCollapsed } from './useCollapseOnScroll'
import { filteredRoute, useWorldFilter, worldSearch } from './worldFilter'

const WORLDS = [
  { id: 3, name: 'Velar' },
  { id: 4, name: 'Mirevast' },
]

async function renderRoutes(shell: ReactNode, path: string) {
  const root = createRootRoute({
    component: () => (
      <QueryClientProvider client={new QueryClient()}>
        <RealtimeProvider createSource={(url) => new FakeEventSource(url)}>
          <TooltipProvider>
            <div className='flex min-h-svh w-full'>
              <main className='flex min-w-0 flex-1 flex-col'>
                <Outlet />
              </main>
              {shell}
            </div>
          </TooltipProvider>
        </RealtimeProvider>
      </QueryClientProvider>
    ),
  })
  const routes = [
    '/map',
    '/cosmos',
    '/network',
    '/chronicle',
    '/atlas',
    '/pantheon',
  ].map((route) =>
    createRoute({
      getParentRoute: () => root,
      path: route,
      staticData: {
        layout: ['/map', '/cosmos', '/network'].includes(route)
          ? 'canvas'
          : 'page',
      },
      validateSearch: (search: Record<string, unknown>) => search,
      component: () => <div data-testid='canvas'>{route}</div>,
    })
  )
  const router = createRouter({
    routeTree: root.addChildren(routes),
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  const screen = await render(<RouterProvider router={router} />)
  return { screen, router }
}

describe('world filter', () => {
  beforeEach(() => useWorldFilter.setState({ worldId: null }))

  it('resets dependent view state when the world changes', () => {
    expect(filteredRoute('/map')).toBe('/map')
    expect(filteredRoute('/pantheon')).toBeNull()
    expect(
      worldSearch('/map', { world: 3, epoch: 2, focus: 9, drawer: 'son:1' }, 4)
    ).toEqual({ world: 4, drawer: 'son:1' })
    expect(
      worldSearch(
        '/atlas',
        { world: 3, page: 2, select: 'entity:4', q: 'salt' },
        null
      )
    ).toEqual({ q: 'salt' })
  })

  it('is hidden while the cosmos has a single world', async () => {
    const { screen } = await renderRoutes(
      <WorldSwitcher worlds={[WORLDS[0]]} />,
      '/map'
    )
    await expect.element(screen.getByText('/map')).toBeVisible()
    expect(document.querySelector('[data-layout="world-switcher"]')).toBeNull()
  })

  it('filters the current view and resets its dependent state', async () => {
    const { screen, router } = await renderRoutes(
      <WorldSwitcher worlds={WORLDS} />,
      '/chronicle?epoch=3&q=salt'
    )
    await screen.getByRole('combobox', { name: 'World filter' }).click()
    await screen.getByRole('option', { name: 'Mirevast' }).click()
    expect(useWorldFilter.getState().worldId).toBe(4)
    await expect
      .poll(() => router.state.location.search)
      .toEqual({ q: 'salt', world: 4 })
    await screen.getByRole('combobox', { name: 'World filter' }).click()
    await screen.getByRole('option', { name: 'Whole cosmos' }).click()
    expect(useWorldFilter.getState().worldId).toBeNull()
    await expect.poll(() => router.state.location.search).toEqual({ q: 'salt' })
  })

  it('forgets a world that no longer exists', async () => {
    useWorldFilter.setState({ worldId: 99 })
    await renderScreen(<WorldSwitcher worlds={WORLDS} />)
    await expect.poll(() => useWorldFilter.getState().worldId).toBeNull()
  })
})

describe('collapsing top bar', () => {
  it('collapses while scrolling down past the threshold and returns on the way up', () => {
    expect(nextCollapsed(false, 0, 40, 60)).toBe(false)
    expect(nextCollapsed(false, 40, 120, 60)).toBe(true)
    expect(nextCollapsed(true, 120, 100, 60)).toBe(false)
    expect(nextCollapsed(true, 120, 120, 60)).toBe(true)
    expect(nextCollapsed(true, 200, 30, 60)).toBe(false)
  })
})

describe('live feed dock on canvas routes', () => {
  beforeEach(async () => {
    await page.viewport(1440, 900)
    useFeedPreferences.setState({ open: true })
    useFeedOverlay.setState({ open: false })
  })
  afterEach(() => useFeedPreferences.setState({ open: null }))

  it('docks beside page routes but never squeezes a canvas route', async () => {
    const shell = (
      <>
        <LiveFeedSheet />
        <LiveFeedDock />
      </>
    )
    const pageRoute = await renderRoutes(shell, '/chronicle')
    await expect
      .element(
        pageRoute.screen.getByRole('complementary', { name: 'Live feed dock' })
      )
      .toBeVisible()
    await pageRoute.router.navigate({ to: '/cosmos' as never })
    await expect.element(pageRoute.screen.getByText('/cosmos')).toBeVisible()
    expect(document.querySelector('[data-layout="feed-dock"]')).toBeNull()
    const canvas = document.querySelector(
      '[data-testid="canvas"]'
    ) as HTMLElement
    expect(canvas.getBoundingClientRect().width).toBeGreaterThan(1000)
    await pageRoute.screen.getByRole('button', { name: 'Live feed' }).click()
    await expect
      .element(pageRoute.screen.getByRole('dialog', { name: 'Live feed' }))
      .toBeVisible()
    expect(document.querySelector('[data-layout="feed-dock"]')).toBeNull()
    expect(useFeedPreferences.getState().open).toBe(true)
  })
})
