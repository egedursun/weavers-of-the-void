import { createFileRoute } from '@tanstack/react-router'
import { FateControlsPage } from '@/features/fate/FateControlsPage'

export const Route = createFileRoute('/_app/settings/fate')({
  component: FateControlsPage,
})
