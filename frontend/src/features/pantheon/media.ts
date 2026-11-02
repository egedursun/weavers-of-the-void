export const THUMBNAIL_WIDTH = 320

export function mediaUrl(
  fileName: string | null | undefined,
  width: number = THUMBNAIL_WIDTH
): string | null {
  if (!fileName) return null
  return `/api/media/${encodeURIComponent(fileName)}?w=${width}`
}
