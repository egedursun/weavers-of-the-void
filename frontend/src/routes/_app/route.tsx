import { createFileRoute } from '@tanstack/react-router'
import { DRAWER_PAGES } from '@/config/drawerPages'
import { AppShell } from '@/components/layout/AppShell'
import { CommandPalette } from '@/features/command-palette/CommandPalette'
import {
  ShellActions,
  ShellAside,
  ShellBanner,
  ShellContext,
  ShellNavBadges,
  ShellServices,
  ShellSidebarTools,
} from '@/features/epoch/ShellStatus'
import { SonRevealOverlay } from '@/features/pantheon/SonRevealOverlay'

export const Route = createFileRoute('/_app')({
  component: () => (
    <AppShell
      drawerPages={DRAWER_PAGES}
      topBarContext={<ShellContext />}
      topBarActions={<ShellActions />}
      banner={<ShellBanner />}
      aside={<ShellAside />}
      sidebarFooter={<ShellSidebarTools />}
      navBadges={ShellNavBadges}
      overlays={
        <>
          <ShellServices />
          <CommandPalette />
          <SonRevealOverlay />
        </>
      }
    />
  ),
})
