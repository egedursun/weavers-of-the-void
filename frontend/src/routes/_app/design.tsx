import { createFileRoute } from '@tanstack/react-router'
import { DesignScreen } from '@/features/design/DesignScreen'

export const Route = createFileRoute('/_app/design')({
  component: DesignScreen,
})
