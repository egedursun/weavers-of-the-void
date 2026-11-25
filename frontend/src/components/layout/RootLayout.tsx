import { Outlet } from '@tanstack/react-router'
import { TOAST_DURATION_MS } from '@/constants/ui'
import { Toaster } from '@/components/ui/sonner'
import { NavigationProgress } from './NavigationProgress'

const TOAST_LIFT = '5.5rem'

export function RootLayout() {
  return (
    <>
      <NavigationProgress />
      <Outlet />
      <Toaster
        duration={TOAST_DURATION_MS}
        offset={{ bottom: TOAST_LIFT }}
        mobileOffset={{ bottom: TOAST_LIFT }}
      />
    </>
  )
}
