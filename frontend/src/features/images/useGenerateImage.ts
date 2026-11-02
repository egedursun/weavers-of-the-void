import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { generateImage, imageKeys } from './api'

export const QUEUED_MESSAGE = 'The image is queued'

export function useGenerateImage(nodeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => generateImage(nodeId),
    onSuccess: () => {
      toast.success(QUEUED_MESSAGE)
      void queryClient.invalidateQueries({ queryKey: imageKeys.status })
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : String(error)),
  })
}
