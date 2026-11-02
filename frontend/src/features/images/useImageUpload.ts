import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { queryKeys } from '@/api/queryKeys'
import { imageKeys, isImageMime, uploadImage } from './api'
import { captionFromFileName } from './caption'

export const CAPTION_MAX_LENGTH = 120
const UNSUPPORTED = 'Images must be PNG, JPEG or WEBP.'

export function useImageUpload(nodeId: number) {
  const queryClient = useQueryClient()
  const [pending, setPending] = useState(0)
  const upload = useCallback(
    async (files: File[]) => {
      const images = files.filter((file) => isImageMime(file.type))
      if (images.length < files.length) toast.error(UNSUPPORTED)
      if (images.length === 0) return
      setPending(images.length)
      let saved = 0
      for (const file of images) {
        try {
          const caption = captionFromFileName(file.name)
          await uploadImage(
            nodeId,
            file,
            caption ? caption.slice(0, CAPTION_MAX_LENGTH) : null
          )
          saved += 1
        } catch (error) {
          toast.error(error instanceof Error ? error.message : String(error))
        }
        setPending((current) => Math.max(0, current - 1))
      }
      if (saved > 0)
        toast.success(saved === 1 ? 'Image added' : `${saved} images added`)
      void queryClient.invalidateQueries({ queryKey: imageKeys.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
    [nodeId, queryClient]
  )
  return { upload, pending }
}
