import { mediaUrl } from '@/features/pantheon/media'

const IMAGE_WIDTH = 160
const MAX_LOADING = 24

const images = new Map<string, HTMLImageElement | null>()
let loading = 0

export function markerImage(
  cover: string,
  onReady: () => void
): HTMLImageElement | null {
  const known = images.get(cover)
  if (known === null) return null
  if (known) return known.complete && known.naturalWidth > 0 ? known : null
  const source = mediaUrl(cover, IMAGE_WIDTH)
  if (!source || loading >= MAX_LOADING) return null
  const image = new Image()
  image.decoding = 'async'
  loading += 1
  image.onload = () => {
    loading -= 1
    onReady()
  }
  image.onerror = () => {
    loading -= 1
    images.set(cover, null)
  }
  image.src = source
  images.set(cover, image)
  return null
}
