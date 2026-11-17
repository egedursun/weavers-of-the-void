import { createFileRoute } from '@tanstack/react-router'
import { UsageScreen } from '@/features/usage/UsageScreen'
import { validateUsageSearch } from '@/features/usage/usageSearch'

export const Route = createFileRoute('/_app/usage')({
  validateSearch: validateUsageSearch,
  component: UsageScreen,
})
