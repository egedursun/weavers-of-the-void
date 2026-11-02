import { createFileRoute } from '@tanstack/react-router'
import { AppearancePage } from '@/features/settings/AppearancePage'

export const Route = createFileRoute('/_app/settings/appearance')({
  component: AppearancePage,
})
