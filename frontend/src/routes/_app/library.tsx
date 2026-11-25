import { createFileRoute } from '@tanstack/react-router'
import { LibraryScreen } from '@/features/divine-will/library/LibraryScreen'
import { validateLibrarySearch } from '@/features/divine-will/library/librarySearch'

export const Route = createFileRoute('/_app/library')({
  validateSearch: validateLibrarySearch,
  component: LibraryScreen,
})
