import { createFileRoute } from '@tanstack/react-router'
import { RecordsSettings } from '@/features/settings/RecordsSettings'

export const Route = createFileRoute('/_app/settings/records')({
  component: RecordsSettings,
})
