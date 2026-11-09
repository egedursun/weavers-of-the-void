import { createFileRoute } from '@tanstack/react-router'
import { HeavensScreen } from '@/features/cosmography/HeavensScreen'
import { validateHeavensSearch } from '@/features/cosmography/heavensSearch'

export const Route = createFileRoute('/_app/heavens')({
  staticData: { layout: 'canvas' },
  validateSearch: validateHeavensSearch,
  component: HeavensScreen,
})
