import { createFileRoute } from '@tanstack/react-router'
import { AtlasScreen } from '@/features/atlas/AtlasScreen'
import { validateAtlasSearch } from '@/features/atlas/atlasSearch'

export const Route = createFileRoute('/_app/atlas')({
  validateSearch: validateAtlasSearch,
  component: AtlasScreen,
})
