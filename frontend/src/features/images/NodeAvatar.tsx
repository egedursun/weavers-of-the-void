import { type PortraitSize, Portrait } from '@/components/domain'
import { useNameIndex } from '@/features/chronicle/linkTargets'
import { mediaUrl } from '@/features/pantheon/media'

const THUMB_WIDTH = 160

type NodeAvatarProps = {
  id: number
  name: string
  size?: PortraitSize
  shape?: 'circle' | 'square'
}

export function NodeAvatar({
  id,
  name,
  size = 'xs',
  shape = 'circle',
}: NodeAvatarProps) {
  const index = useNameIndex()
  const cover = index.get(id)?.cover ?? null
  return (
    <Portrait
      name={name}
      src={mediaUrl(cover, THUMB_WIDTH)}
      size={size}
      shape={shape}
    />
  )
}
