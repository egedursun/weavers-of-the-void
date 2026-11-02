import { createFileRoute } from '@tanstack/react-router'
import { MaintenancePage } from '@/features/maintenance/MaintenancePage'

export const Route = createFileRoute('/_app/settings/maintenance')({
  component: MaintenancePage,
})
