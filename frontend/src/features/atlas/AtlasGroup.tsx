import { createElement } from 'react'
import { ChevronRight, Folder } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Medallion, MiniStat, Paged, Section } from '@/components/domain'
import { Muted, PageTitle, Text } from '@/components/typography'
import { type AtlasNode, countLeaves } from './atlasModel'
import { KIND_TONE, nodeIcon } from './nodeVisuals'

function ChildRow({
  node,
  onSelect,
}: {
  node: AtlasNode
  onSelect: (key: string) => void
}) {
  const inside = node.children.length > 0 ? countLeaves(node) : 0
  return (
    <li>
      <Button
        variant='outline'
        onClick={() => onSelect(node.key)}
        size='lg'
        className='w-full min-w-0 justify-start gap-3 text-start hover:border-primary/50'
      >
        {createElement(nodeIcon(node), {
          'aria-hidden': true,
          className: cn('size-icon-md shrink-0', KIND_TONE[node.kind]),
        })}
        <span className='flex min-w-0 flex-1 items-baseline gap-2'>
          <Text as='span' weight='medium' truncate>
            {node.label}
          </Text>
          {node.hint && (
            <Muted as='span' variant='caption' truncate>
              {node.hint}
            </Muted>
          )}
        </span>
        {inside > 0 && (
          <Badge size='sm' variant='secondary'>
            {formatInteger(inside)}
          </Badge>
        )}
        <ChevronRight
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
      </Button>
    </li>
  )
}

export function AtlasGroup({
  node,
  onSelect,
}: {
  node: AtlasNode
  onSelect: (key: string) => void
}) {
  const groups = node.children.filter((child) => child.kind === 'group')
  const records = node.children.filter((child) => child.kind !== 'group')
  const total = countLeaves(node)
  return (
    <div data-surface='AtlasGroup' className='flex min-w-0 flex-col gap-6'>
      <header className='flex min-w-0 items-center gap-4'>
        <Medallion icon={Folder} tone='gold' />
        <div className='flex min-w-0 flex-col gap-0.5'>
          <PageTitle>{node.label}</PageTitle>
          <Muted>{`${formatInteger(total)} ${total === 1 ? 'record' : 'records'} under this branch`}</Muted>
        </div>
      </header>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <MiniStat icon={Folder} label='Records' value={total} tone='gold' />
        <MiniStat
          icon={nodeIcon(records[0] ?? node)}
          label='Directly here'
          value={records.length}
          tone='info'
        />
        {groups.length > 0 && (
          <MiniStat
            icon={Folder}
            label='Branches'
            value={groups.length}
            tone='muted'
          />
        )}
      </div>
      {groups.length > 0 && (
        <Section title='Branches' icon={Folder} level={3}>
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <Paged items={groups} as='li'>
              {(child) => (
                <ChildRow key={child.key} node={child} onSelect={onSelect} />
              )}
            </Paged>
          </ul>
        </Section>
      )}
      {records.length > 0 && (
        <Section title='Records' icon={nodeIcon(records[0])} level={3}>
          <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <Paged items={records} as='li'>
              {(child) => (
                <ChildRow key={child.key} node={child} onSelect={onSelect} />
              )}
            </Paged>
          </ul>
        </Section>
      )}
    </div>
  )
}
