import { createFileRoute } from '@tanstack/react-router'
import { LedgerScreen } from '@/features/ledger/LedgerScreen'

export const Route = createFileRoute('/_app/ledger')({
  component: LedgerScreen,
})
