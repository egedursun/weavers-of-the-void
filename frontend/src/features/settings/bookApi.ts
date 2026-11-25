import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { apiUrl } from '@/api/url'

export type BookPdfStatus = components['schemas']['BookPdfStatus']

export function bookPdfUrl(): string {
  return apiUrl('/api/book.pdf')
}

const POLL_MS = 2000

export const bookKeys = {
  pdf: [...queryKeys.world.all, 'book', 'pdf'] as const,
}

export function useBookPdf() {
  return useQuery({
    queryKey: bookKeys.pdf,
    queryFn: () => unwrap(api.GET('/api/book/pdf')),
    refetchInterval: (query) => (query.state.data?.job_id ? POLL_MS : false),
  })
}

export function usePrintBook() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/book/pdf' }],
    mutationFn: () => unwrap(api.POST('/api/book/pdf')),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: bookKeys.pdf }),
  })
}
