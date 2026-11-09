import { createFileRoute } from '@tanstack/react-router'
import { HeavensScreen } from '@/features/cosmography/HeavensScreen'

export const Route = createFileRoute('/_app/heavens')({
  component: HeavensScreen,
})
