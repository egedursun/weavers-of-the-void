import { Muted, Text } from '@/components/typography'
import { type HoverText } from './mapText'

type MapHoverOverlayProps = {
  hover: HoverText
  x: number
  y: number
  width: number
}

const OFFSET = 14
const MAX_WIDTH = 288

export function MapHoverOverlay({ hover, x, y, width }: MapHoverOverlayProps) {
  const flip = x + OFFSET + MAX_WIDTH > width
  return (
    <div
      role='tooltip'
      className='pointer-events-none absolute flex max-w-72 min-w-0 flex-col gap-0.5 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2 text-popover-foreground'
      style={{
        left: flip ? undefined : x + OFFSET,
        right: flip ? width - x + OFFSET : undefined,
        top: y + OFFSET,
      }}
    >
      <Text weight='semibold' truncate={2}>
        {hover.title}
      </Text>
      {hover.lines.map((line, index) => (
        <Muted key={index} variant='caption' truncate={3}>
          {line}
        </Muted>
      ))}
    </div>
  )
}
