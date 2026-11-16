import { Muted, Text } from '@/components/typography'
import { IconMarker } from '@/features/map/SwatchMarker'
import { typeIcon } from '@/features/map/iconPaths'
import { type GraphNode } from './graphModel'

type GraphHoverOverlayProps = {
  node: GraphNode
  kindLabel: string
  links: number
  x: number
  y: number
  width: number
}

const OFFSET = 14
const MAX_WIDTH = 288

export function GraphHoverOverlay({
  node,
  kindLabel,
  links,
  x,
  y,
  width,
}: GraphHoverOverlayProps) {
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
      <div className='flex min-w-0 items-center gap-1.5'>
        <IconMarker
          icon={typeIcon(node.kind === 'entity' ? node.type : node.kind)}
          token={node.family.token}
        />
        <Text weight='semibold' truncate={2}>
          {node.name}
        </Text>
      </div>
      <Muted variant='caption'>
        {`${kindLabel} · ${node.family.label} · ${links} ${links === 1 ? 'link' : 'links'}`}
      </Muted>
    </div>
  )
}
