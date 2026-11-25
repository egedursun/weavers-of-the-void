import { createFileRoute } from '@tanstack/react-router'
import { WorkspaceSettingsScreen } from '@/features/workspaces/WorkspaceSettingsScreen'
import { validateTeamSearch } from '@/features/workspaces/teamParts'

export const Route = createFileRoute('/workspace')({
  validateSearch: validateTeamSearch,
  component: WorkspaceSettingsScreen,
})
