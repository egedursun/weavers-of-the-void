import { type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from '@tanstack/react-router'
import { RealtimeProvider } from '@/realtime'
import '@/styles/index.css'
import { toast } from 'sonner'
import { render } from 'vitest-browser-react'
import { ThemeProvider } from '@/context/ThemeProvider'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { validateDrawerSearch } from '@/components/layout/drawer/drawerEntries'
import { FakeEventSource } from './fakeEventSource'
import { type MockRoutes, startMockServer } from './mockServer'

const TEST_TOASTS = {
  classNames: {
    toast: 'pointer-events-none',
    actionButton: 'pointer-events-auto',
    cancelButton: 'pointer-events-auto',
    closeButton: 'pointer-events-auto',
  },
}

export async function renderScreen(
  node: ReactNode,
  routes: MockRoutes = {},
  path = '/',
  options: { realtime?: boolean } = { realtime: true }
) {
  toast.dismiss()
  FakeEventSource.reset()
  const server = startMockServer(routes)
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  const rootRoute = createRootRoute({
    validateSearch: validateDrawerSearch,
    component: () => (
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            {options.realtime ? (
              <RealtimeProvider
                createSource={(url) => new FakeEventSource(url)}
              >
                {node}
              </RealtimeProvider>
            ) : (
              node
            )}
            <Toaster toastOptions={TEST_TOASTS} />
          </TooltipProvider>
        </QueryClientProvider>
      </ThemeProvider>
    ),
  })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  const screen = await render(<RouterProvider router={router} />)
  let nextId = 1000
  const emit = (kind: string, payload: Record<string, unknown>) => {
    const source = FakeEventSource.latest()
    source.open()
    nextId += 1
    source.emit(kind, {
      id: nextId,
      kind,
      payload,
      at: new Date().toISOString(),
    })
  }
  return { screen, router, server, queryClient, emit }
}
