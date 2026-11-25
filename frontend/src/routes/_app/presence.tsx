import { createFileRoute } from '@tanstack/react-router'
import { PresenceScreen } from '@/features/presence/PresenceScreen'
import { validatePresenceSearch } from '@/features/presence/presenceSearch'

export const Route = createFileRoute('/_app/presence')({
  validateSearch: validatePresenceSearch,
  component: PresenceScreen,
})
