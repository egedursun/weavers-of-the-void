import {
  BookOpen,
  CalendarDays,
  Compass,
  Crosshair,
  ExternalLink,
  Link2,
  type LucideIcon,
  X,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Medallion, Paged } from '@/components/domain'
import { RecordNavLink } from '@/components/domain/RecordNavLink'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { Label, Muted, Text } from '@/components/typography'
import { useNameIndex } from '@/features/chronicle/linkTargets'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import { typeIcon } from '@/features/map/iconPaths'
import { NodePicker, type PickableNode } from './NodePicker'
import { typeLabel } from './families'
import { type GraphNode, entryKindOf } from './graphModel'

export type NodeTie = { id: number; name: string; label: string }

const TIES_SHOWN = 6

function iconOf(node: GraphNode): LucideIcon {
  return typeIcon(node.kind === 'entity' ? node.type : node.kind)
}

type NodeInfoCardProps = {
  node: GraphNode
  ties: readonly NodeTie[]
  onSelect: (id: number) => void
  visibleLinks: number
  typeLabels: ReadonlyMap<string, string>
  nodes: readonly PickableNode[]
  onClose: () => void
  onFocus: (node: GraphNode) => void
  onPathTo: (id: number | null) => void
  pathTarget: number | null
}

export function NodeInfoCard({
  node,
  ties,
  onSelect,
  visibleLinks,
  typeLabels,
  nodes,
  onClose,
  onFocus,
  onPathTo,
  pathTarget,
}: NodeInfoCardProps) {
  const entryStack = useEntryStack()
  const kind = entryKindOf(node.kind)
  const world = node.kind === 'world'
  const names = useNameIndex()
  const hasCover = Boolean(names.get(node.id)?.cover)
  return (
    <Card data-node-info>
      <CardContent className='flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 items-start gap-3'>
          {hasCover ? (
            <NodeAvatar
              id={node.id}
              name={node.name}
              size='lg'
              shape='square'
            />
          ) : (
            <Medallion icon={iconOf(node)} />
          )}
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Label variant='overline'>{typeLabel(node.type, typeLabels)}</Label>
            <Text weight='semibold' truncate={2}>
              {node.name}
            </Text>
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Badge size='sm' variant='info'>
                <Link2 />
                {`${visibleLinks} ${visibleLinks === 1 ? 'link' : 'links'}`}
              </Badge>
              <Badge size='sm' variant='outline'>
                <CalendarDays />
                {`Since epoch ${node.epoch}`}
              </Badge>
              {node.status !== 'canon' && (
                <Badge size='sm' variant='warning'>
                  {node.status}
                </Badge>
              )}
            </div>
          </div>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Close'
            onClick={onClose}
          >
            <X />
          </Button>
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          {world ? (
            <>
              <Button
                size='sm'
                variant='outline'
                onClick={() =>
                  entryStack.open({ kind: 'world', id: String(node.id) })
                }
              >
                <BookOpen />
                Lore and history
              </Button>
              <Button
                size='sm'
                variant='outline'
                onClick={() =>
                  entryStack.open({ kind: 'world-guide', id: String(node.id) })
                }
              >
                <Compass />
                {"Traveller's guide"}
              </Button>
              <RecordNavLink to={{ view: 'world-map', world: node.id }} />
            </>
          ) : (
            kind && (
              <Button
                size='sm'
                variant='outline'
                onClick={() =>
                  entryStack.open(
                    kind === 'creator'
                      ? { kind }
                      : { kind, id: String(node.id) }
                  )
                }
              >
                <ExternalLink />
                Open its page
              </Button>
            )
          )}
          {node.kind === 'entity' && node.worldId !== null && (
            <RecordNavLink
              to={{ view: 'map', world: node.worldId, focus: node.id }}
            />
          )}
          <Button size='sm' variant='outline' onClick={() => onFocus(node)}>
            <Crosshair />
            Focus on its surroundings
          </Button>
        </div>
        {ties.length > 0 && (
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label variant='overline'>{`Ties · ${ties.length}`}</Label>
            <ul className='flex min-w-0 flex-col gap-1'>
              <Paged items={ties.slice(0, TIES_SHOWN)} as='li'>
                {(tie) => (
                  <li
                    key={`${tie.id}-${tie.label}`}
                    className='flex min-w-0 items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 px-2 py-1'
                  >
                    <Button
                      variant='link'
                      size='sm'
                      onClick={() => onSelect(tie.id)}
                    >
                      {tie.name}
                    </Button>
                    <Muted
                      variant='caption'
                      truncate
                      className='flex-1 text-end'
                    >
                      {tie.label}
                    </Muted>
                  </li>
                )}
              </Paged>
            </ul>
            {ties.length > TIES_SHOWN && (
              <Muted variant='caption'>{`${ties.length - TIES_SHOWN} more ties in the graph.`}</Muted>
            )}
          </div>
        )}
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>
            How are they connected? Shift+click another record or search:
          </Label>
          <NodePicker
            nodes={nodes}
            value={pathTarget}
            onPick={onPathTo}
            label='Second record'
            placeholder='Second record…'
          />
        </div>
      </CardContent>
    </Card>
  )
}
