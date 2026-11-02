import { createFileRoute } from '@tanstack/react-router'
import { CosmosView } from '@/features/cosmos/CosmosView'
import { validateCosmosSearch } from '@/features/cosmos/cosmosSearch'

export const Route = createFileRoute('/_app/cosmos')({
  staticData: { layout: 'canvas' },
  validateSearch: validateCosmosSearch,
  component: CosmosView,
})
