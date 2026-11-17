import { createFileRoute } from '@tanstack/react-router'
import { KindsScreen } from '@/features/kinds/KindsScreen'

export const Route = createFileRoute('/_app/kinds')({
  component: KindsScreen,
})
