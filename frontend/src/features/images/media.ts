import { apiUrl } from '@/api/url'

export const THUMBNAIL_WIDTHS = [64, 160, 320, 640, 960, 1280] as const

export type ThumbnailWidth = (typeof THUMBNAIL_WIDTHS)[number]

export function mediaUrl(fileName: string, width?: ThumbnailWidth): string {
  return apiUrl(`/api/media/${encodeURIComponent(fileName)}`, { w: width })
}
