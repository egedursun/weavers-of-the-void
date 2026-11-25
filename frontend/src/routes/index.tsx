import { createFileRoute } from '@tanstack/react-router'
import { ThemeSwitch } from '@/components/layout/ThemeSwitch'
import { AccountMenu } from '@/features/accounts/AccountMenu'
import { LibraryScreen } from '@/features/universes/LibraryScreen'
import { WorkspaceBar } from '@/features/workspaces/WorkspaceBar'

export const Route = createFileRoute('/')({
  component: () => (
    <LibraryScreen
      workspace={<WorkspaceBar />}
      tools={
        <>
          <ThemeSwitch />
          <AccountMenu />
        </>
      }
    />
  ),
})
