import { createFileRoute } from '@tanstack/react-router'
import { CouncilScreen } from '@/features/council/CouncilScreen'

export const Route = createFileRoute('/_app/council')({
  component: CouncilScreen,
})
