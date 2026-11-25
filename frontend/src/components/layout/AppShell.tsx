import { type ComponentType, type ReactNode } from 'react'
import { Outlet } from '@tanstack/react-router'
import { getCookie } from '@/lib/cookies'
import { LayoutProvider } from '@/context/LayoutProvider'
import { SearchProvider } from '@/context/SearchProvider'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { AppSidebar } from './AppSidebar'
import { Main } from './Main'
import { SkipToMain } from './SkipToMain'
import { TopBar } from './TopBar'
import { EntryWindow, type EntryPages } from './entry/EntryWindow'
import { useGlobalShortcuts } from './useGlobalShortcuts'

type AppShellProps = {
  entryPages: EntryPages
  topBarContext?: ReactNode
  topBarActions?: ReactNode
  topBarAccount?: ReactNode
  banner?: ReactNode
  overlays?: ReactNode
  aside?: ReactNode
  sidebarFooter?: ReactNode
  navBadges?: ComponentType<{ children: ReactNode }>
}

function Passthrough({ children }: { children: ReactNode }) {
  return children
}

function GlobalShortcuts() {
  useGlobalShortcuts()
  return null
}

export function AppShell({
  entryPages,
  topBarContext,
  topBarActions,
  topBarAccount,
  banner,
  overlays,
  aside,
  sidebarFooter,
  navBadges: NavBadges = Passthrough,
}: AppShellProps) {
  const defaultOpen = getCookie('sidebar_state') !== 'false'
  return (
    <SearchProvider>
      <LayoutProvider>
        <SidebarProvider defaultOpen={defaultOpen}>
          <SkipToMain />
          <GlobalShortcuts />
          <NavBadges>
            <AppSidebar footer={sidebarFooter} />
          </NavBadges>
          <SidebarInset className='min-w-0'>
            <TopBar
              context={topBarContext}
              actions={topBarActions}
              account={topBarAccount}
            />
            {banner}
            <Main>
              <Outlet />
            </Main>
          </SidebarInset>
          {aside}
          <EntryWindow pages={entryPages} />
          {overlays}
        </SidebarProvider>
      </LayoutProvider>
    </SearchProvider>
  )
}
