import { ImageGenFeedLines } from './ImageGenFeedLines'

export const IMAGE_FEED_LINES = 6

export function ImageQueueFeed() {
  return <ImageGenFeedLines limit={IMAGE_FEED_LINES} />
}
