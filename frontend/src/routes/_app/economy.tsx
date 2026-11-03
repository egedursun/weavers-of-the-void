import { createFileRoute } from '@tanstack/react-router'
import { EconomyScreen } from '@/features/economy/EconomyScreen'
import { validateEconomySearch } from '@/features/economy/economyTabs'

export const Route = createFileRoute('/_app/economy')({
  validateSearch: validateEconomySearch,
  component: EconomyScreen,
})
