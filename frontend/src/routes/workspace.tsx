import { createFileRoute } from '@tanstack/react-router'
import { WorkspaceSettingsScreen } from '@/features/workspaces/WorkspaceSettingsScreen'

export const Route = createFileRoute('/workspace')({
  component: WorkspaceSettingsScreen,
})
