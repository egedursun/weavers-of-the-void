import { createFileRoute } from '@tanstack/react-router'
import { ServerAccountsScreen } from '@/features/accounts/ServerAccountsScreen'

export const Route = createFileRoute('/accounts')({
  component: ServerAccountsScreen,
})
