import { Outlet } from '@tanstack/react-router'
import { RealtimeProvider } from '@/realtime'
import { TOAST_DURATION_MS } from '@/constants/ui'
import { Toaster } from '@/components/ui/sonner'
import { NavigationProgress } from './NavigationProgress'

export function RootLayout() {
  return (
    <RealtimeProvider>
      <NavigationProgress />
      <Outlet />
      <Toaster duration={TOAST_DURATION_MS} />
    </RealtimeProvider>
  )
}
