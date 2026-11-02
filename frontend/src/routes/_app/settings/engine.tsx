import { createFileRoute } from '@tanstack/react-router'
import { EnginePage } from '@/features/engine/EnginePage'

export const Route = createFileRoute('/_app/settings/engine')({
  component: EnginePage,
})
