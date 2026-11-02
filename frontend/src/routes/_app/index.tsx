import { createFileRoute } from '@tanstack/react-router'
import { OverviewScreen } from '@/features/overview/OverviewScreen'

export const Route = createFileRoute('/_app/')({
  component: OverviewScreen,
})
