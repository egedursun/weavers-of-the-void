export const THUMBNAIL_WIDTHS = [64, 160, 320, 640] as const

export type ThumbnailWidth = (typeof THUMBNAIL_WIDTHS)[number]

export function mediaUrl(fileName: string, width?: ThumbnailWidth): string {
  const base = `/api/media/${encodeURIComponent(fileName)}`
  return width ? `${base}?w=${width}` : base
}
