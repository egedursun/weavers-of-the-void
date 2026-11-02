import { createFileRoute } from '@tanstack/react-router'
import { ChronicleScreen } from '@/features/chronicle/ChronicleScreen'
import { validateChronicleSearch } from '@/features/chronicle/chronicleSearch'

export const Route = createFileRoute('/_app/chronicle')({
  validateSearch: validateChronicleSearch,
  component: ChronicleScreen,
})
