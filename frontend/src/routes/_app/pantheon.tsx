import { createFileRoute } from '@tanstack/react-router'
import { PantheonScreen } from '@/features/pantheon/PantheonScreen'

export const Route = createFileRoute('/_app/pantheon')({
  component: PantheonScreen,
})
