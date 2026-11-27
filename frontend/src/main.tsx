import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import '@fontsource-variable/inter'
import '@fontsource-variable/nunito-sans'
import '@fontsource/cinzel-decorative/700.css'
import '@fontsource/cinzel/500.css'
import '@fontsource/cinzel/600.css'
import '@fontsource/cinzel/700.css'
import { libraryQueryClient } from '@/api/queryClients'
import { AccessibilityProvider } from '@/context/AccessibilityProvider'
import { FontProvider } from '@/context/FontProvider'
import { ThemeProvider } from '@/context/ThemeProvider'
import '@/components/layout/routeStaticData'
import { routeTree } from './routeTree.gen'
import './styles/index.css'

const router = createRouter({
  routeTree,
  context: { queryClient: libraryQueryClient },
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
if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <StrictMode>
      <QueryClientProvider client={libraryQueryClient}>
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
