import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type LawGrammarView = components['schemas']['LawGrammarView']
export type LawExceptionView = components['schemas']['LawExceptionView']
export type LawTheoryView = components['schemas']['LawTheoryView']

export function useLawGrammar(lawId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'law-grammar', lawId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/natural-laws/{law_id}/grammar', {
          params: { path: { law_id: lawId } },
        })
      ),
  })
}
