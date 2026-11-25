import { apiUrl } from '@/api/url'
import { type ThumbnailWidth } from '@/features/images/media'

export const THUMBNAIL_WIDTH: ThumbnailWidth = 320

export function mediaUrl(
  fileName: string | null | undefined,
  width: ThumbnailWidth = THUMBNAIL_WIDTH
): string | null {
  if (!fileName) return null
  return apiUrl(`/api/media/${encodeURIComponent(fileName)}`, { w: width })
}
