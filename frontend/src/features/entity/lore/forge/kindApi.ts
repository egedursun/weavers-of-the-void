import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../../api/keys'

type Catalog = components['schemas']['CustomCatalog']

export const kindKeys = {
  list: (catalog: Catalog) => [...loreKeys.state, 'kinds', catalog] as const,
}

export function useCustomKinds(catalog: Catalog) {
  return useQuery({
    queryKey: kindKeys.list(catalog),
    queryFn: () =>
      unwrap(api.GET('/api/custom-kinds', { params: { query: { catalog } } })),
  })
}
