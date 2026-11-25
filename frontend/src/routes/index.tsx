import { createFileRoute } from '@tanstack/react-router'
import { ThemeSwitch } from '@/components/layout/ThemeSwitch'
import { AccountMenu } from '@/features/accounts/AccountMenu'
import { LibraryScreen } from '@/features/universes/LibraryScreen'
import { WorkspaceSwitcher } from '@/features/workspaces/WorkspaceSwitcher'

export const Route = createFileRoute('/')({
  component: () => (
    <LibraryScreen
      workspace={<WorkspaceSwitcher />}
      tools={
        <>
          <ThemeSwitch />
          <AccountMenu />
        </>
      }
    />
  ),
})
