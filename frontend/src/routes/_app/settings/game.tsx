import { createFileRoute } from '@tanstack/react-router'
import { GameSettings } from '@/features/settings/GameSettings'

export const Route = createFileRoute('/_app/settings/game')({
  component: GameSettings,
})
