import { createFileRoute } from '@tanstack/react-router'
import { LanguagesScreen } from '@/features/languages/LanguagesScreen'
import { validateLanguagesSearch } from '@/features/languages/languagesSearch'

export const Route = createFileRoute('/_app/languages')({
  validateSearch: validateLanguagesSearch,
  component: LanguagesScreen,
})
