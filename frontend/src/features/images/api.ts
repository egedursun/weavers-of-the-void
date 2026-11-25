import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { fetchHealth } from '@/api/system'
import { type WriteTarget } from '@/features/team/writeGate'

export type ImageRecord = components['schemas']['ImageRecord']
export type ImageListView = components['schemas']['ImageListView']
export type ImageGenStatus = components['schemas']['ImageGenStatus']
export type QueueStatus = components['schemas']['QueueStatus']
export type BulkRun = components['schemas']['BulkRun']
export type LogLine = components['schemas']['LogLine']
export type ImageMime = components['schemas']['ImageMime']
export type EntitySummary = components['schemas']['EntitySummary']
export type EntityType = components['schemas']['EntityType']

export const imageKeys = {
  all: queryKeys.images.all,
  list: (nodeId: number | null) =>
    [...queryKeys.images.all, 'list', nodeId ?? 'all'] as const,
  status: [...queryKeys.images.all, 'status'] as const,
  missing: (type: string | null, limit: number) =>
    [...queryKeys.images.all, 'missing', type ?? 'all', limit] as const,
}

export const IMAGE_MIMES: readonly ImageMime[] = [
  'image/png',
  'image/jpeg',
  'image/webp',
]

export function isImageMime(value: string): value is ImageMime {
  return (IMAGE_MIMES as readonly string[]).includes(value)
}

export function useImages(nodeId: number | null) {
  return useQuery({
    queryKey: imageKeys.list(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/images', {
          params: { query: { node_id: nodeId ?? undefined } },
        })
      ),
    placeholderData: keepPreviousData,
  })
}

export function useImageGenStatus() {
  return useQuery({
    queryKey: imageKeys.status,
    queryFn: () => unwrap(api.GET('/api/image-gen')),
  })
}

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: fetchHealth,
  })
}

export function useMissingImages(type: string | null, limit: number) {
  return useQuery({
    queryKey: imageKeys.missing(type, limit),
    queryFn: () =>
      unwrap(
        api.GET('/api/gallery/missing', {
          params: {
            query: { type: (type ?? undefined) as never, limit },
          },
        })
      ),
    placeholderData: keepPreviousData,
  })
}

export function uploadImage(
  nodeId: number,
  file: File,
  caption: string | null
): Promise<ImageRecord> {
  return unwrap(
    api.POST('/api/images', {
      params: { query: { node_id: nodeId, caption: caption ?? undefined } },
      body: file as never,
      bodySerializer: (body: unknown) => body as never,
      headers: { 'content-type': file.type },
    })
  )
}

export function setCover(imageId: number): Promise<ImageRecord> {
  return unwrap(
    api.PUT('/api/images/{image_id}/cover', {
      params: { path: { image_id: imageId } },
    })
  )
}

export function setCaption(
  imageId: number,
  caption: string | null
): Promise<ImageRecord> {
  return unwrap(
    api.PUT('/api/images/{image_id}/caption', {
      params: { path: { image_id: imageId } },
      body: { caption },
    })
  )
}

export function deleteImage(imageId: number) {
  return unwrap(
    api.DELETE('/api/images/{image_id}', {
      params: { path: { image_id: imageId } },
    })
  )
}

export function generateImage(nodeId: number) {
  return unwrap(api.POST('/api/image-gen', { body: { node_id: nodeId } }))
}

export function startBulk() {
  return unwrap(api.POST('/api/image-gen/batch/start'))
}

export function restyleBulk() {
  return unwrap(api.POST('/api/image-gen/batch/restyle'))
}

export function stopBulk() {
  return unwrap(api.POST('/api/image-gen/batch/stop'))
}

export function writeMissingPrompts() {
  return unwrap(api.POST('/api/entities/prompts/write-missing'))
}

export function useImageAction<T>(
  writes: readonly WriteTarget[],
  run: (imageId: number) => Promise<T>,
  message: string
) {
  const queryClient = useQueryClient()
  return useMutation({
    writes,
    mutationFn: run,
    onSuccess: () => {
      toast.success(message)
      void queryClient.invalidateQueries({ queryKey: imageKeys.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : String(error)),
  })
}
