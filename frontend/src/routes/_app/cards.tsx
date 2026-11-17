import { createFileRoute } from '@tanstack/react-router'
import { CardsScreen } from '@/features/cards/CardsScreen'

export const Route = createFileRoute('/_app/cards')({
  component: CardsScreen,
})
