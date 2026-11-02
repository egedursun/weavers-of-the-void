import { createFileRoute } from '@tanstack/react-router'
import { EpochControlScreen } from '@/features/epoch/EpochControlScreen'

export const Route = createFileRoute('/_app/epoch')({
  component: EpochControlScreen,
})
