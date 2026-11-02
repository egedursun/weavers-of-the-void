import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import '@fontsource-variable/nunito-sans'
import '@fontsource-variable/inter'
import '@fontsource/cinzel-decorative/700.css'
import '@fontsource/cinzel/500.css'
import '@fontsource/cinzel/600.css'
import '@fontsource/cinzel/700.css'
import { QUERY_STALE_TIME_MS } from '@/constants/ui'
import { AccessibilityProvider } from '@/context/AccessibilityProvider'
import { FontProvider } from '@/context/FontProvider'
import { ThemeProvider } from '@/context/ThemeProvider'
import '@/components/layout/routeStaticData'
import { routeTree } from './routeTree.gen'
import './styles/index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: QUERY_STALE_TIME_MS,
    },
  },
})

const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,
  scrollRestoration: true,
})

const commitLocation = router.commitLocation.bind(router)
router.commitLocation = (next) =>
  commitLocation({
    ...next,
    resetScroll:
      next.resetScroll ?? next.pathname !== router.state.location.pathname,
  })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const rootElement = document.getElementById('root')
if (rootElement && !rootElement.innerHTML) {
  ReactDOM.createRoot(rootElement).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <FontProvider>
            <AccessibilityProvider>
              <RouterProvider router={router} />
            </AccessibilityProvider>
          </FontProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>
  )
}
