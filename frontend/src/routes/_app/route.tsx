import { createFileRoute } from '@tanstack/react-router'
import { ENTRY_PAGES } from '@/config/entryPages'
import { AppShell } from '@/components/layout/AppShell'
import { CommandPalette } from '@/features/command-palette/CommandPalette'
import { DivineWill } from '@/features/divine-will/DivineWill'
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
import { UniverseBoundary } from '@/features/universes/UniverseBoundary'

export const Route = createFileRoute('/_app')({
  component: () => (
    <UniverseBoundary>
      <AppShell
        entryPages={ENTRY_PAGES}
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
            <DivineWill />
          </>
        }
      />
    </UniverseBoundary>
  ),
})
