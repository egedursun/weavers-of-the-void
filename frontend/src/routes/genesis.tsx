import { createFileRoute } from '@tanstack/react-router'
import { GenesisScreen } from '@/features/onboarding/GenesisScreen'
import { UniverseBoundary } from '@/features/universes/UniverseBoundary'

export const Route = createFileRoute('/genesis')({
  component: () => (
    <UniverseBoundary>
      <GenesisScreen />
    </UniverseBoundary>
  ),
})
