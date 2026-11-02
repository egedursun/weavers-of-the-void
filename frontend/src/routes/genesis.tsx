import { createFileRoute } from '@tanstack/react-router'
import { GenesisScreen } from '@/features/onboarding/GenesisScreen'

export const Route = createFileRoute('/genesis')({
  component: GenesisScreen,
})
