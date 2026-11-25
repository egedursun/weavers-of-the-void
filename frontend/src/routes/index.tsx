import { createFileRoute } from '@tanstack/react-router'
import { ThemeSwitch } from '@/components/layout/ThemeSwitch'
import { LibraryScreen } from '@/features/universes/LibraryScreen'

export const Route = createFileRoute('/')({
  component: () => <LibraryScreen tools={<ThemeSwitch />} />,
})
