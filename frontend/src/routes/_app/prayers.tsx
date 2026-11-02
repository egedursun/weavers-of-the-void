import { createFileRoute } from '@tanstack/react-router'
import { PrayersScreen } from '@/features/prayers/PrayersScreen'

export const Route = createFileRoute('/_app/prayers')({
  component: PrayersScreen,
})
