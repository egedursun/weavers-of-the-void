import { createFileRoute } from '@tanstack/react-router'
import { UsageScreen } from '@/features/usage/UsageScreen'

export const Route = createFileRoute('/_app/usage')({
  component: UsageScreen,
})
