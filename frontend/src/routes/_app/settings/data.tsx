import { createFileRoute } from '@tanstack/react-router'
import { DataSettings } from '@/features/settings/DataSettings'

export const Route = createFileRoute('/_app/settings/data')({
  component: DataSettings,
})
