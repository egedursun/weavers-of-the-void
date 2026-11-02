import { createFileRoute } from '@tanstack/react-router'
import { GoalsScreen } from '@/features/goals/GoalsScreen'

export const Route = createFileRoute('/_app/goals')({
  component: GoalsScreen,
})
