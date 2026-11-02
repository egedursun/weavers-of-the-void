import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import { type Job } from './api'
import {
  ACTION_ICON,
  ACTION_ORDER,
  FALLBACK_ACTION_ICON,
  actionLabel,
  drawerOfNode,
} from './jobItemVisuals'

type JobItem = Job['items'][number]

const ITEMS_SHOWN = 8

function NodeName({
  kind,
  id,
  name,
}: {
  kind: string
  id: number
  name: string
}) {
  const drawer = drawerOfNode(kind)
  if (!drawer) return <Text as='span'>{name}</Text>
  return (
    <EntityLink
      kind={drawer}
      id={drawer === 'creator' ? undefined : String(id)}
    >
      {name}
    </EntityLink>
  )
}

function ItemRow({ item }: { item: JobItem }) {
  const Icon = ACTION_ICON[item.action] ?? FALLBACK_ACTION_ICON
  return (
    <li className='flex min-w-0 items-center gap-2 rounded-md border bg-card px-2 py-1.5'>
      <NodeAvatar id={item.node_id} name={item.name} />
      <span className='flex min-w-0 flex-1 flex-col'>
        <span className='flex min-w-0 items-center gap-1.5'>
          <Icon
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-primary'
          />
          <Muted as='span' variant='caption' truncate>
            {actionLabel(item.action)}
          </Muted>
        </span>
        <span className='flex min-w-0 flex-wrap items-center gap-x-1.5'>
          <NodeName kind={item.node_kind} id={item.node_id} name={item.name} />
          {item.other_id !== null &&
            item.other_id !== undefined &&
            item.other_kind &&
            item.other_name && (
              <>
                <Muted as='span' variant='caption'>
                  {item.note ? `${item.note.replaceAll('_', ' ')} →` : '→'}
                </Muted>
                <NodeName
                  kind={item.other_kind}
                  id={item.other_id}
                  name={item.other_name}
                />
              </>
            )}
          {item.note &&
            (item.other_id === null || item.other_id === undefined) && (
              <Muted as='span' variant='caption' truncate>
                {item.note}
              </Muted>
            )}
        </span>
      </span>
    </li>
  )
}

export function JobItems({ items }: { items: JobItem[] }) {
  const [open, setOpen] = useState(false)
  const [action, setAction] = useState<string | null>(null)
  if (items.length === 0) return null
  const counts = new Map<string, number>()
  for (const item of items)
    counts.set(item.action, (counts.get(item.action) ?? 0) + 1)
  const actions = [...counts.keys()].sort(
    (left, right) =>
      ((ACTION_ORDER.indexOf(left) + 100) % 100) -
      ((ACTION_ORDER.indexOf(right) + 100) % 100)
  )
  const shown = action ? items.filter((item) => item.action === action) : items
  return (
    <div data-job-items className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        {actions.map((key) => {
          const Icon = ACTION_ICON[key] ?? FALLBACK_ACTION_ICON
          const active = action === key
          return (
            <Badge
              key={key}
              size='sm'
              variant={active ? 'default' : 'outline'}
              asChild
            >
              <Button
                variant='ghost'
                size='sm'
                aria-pressed={active}
                onClick={() => {
                  setAction(active ? null : key)
                  setOpen(true)
                }}
                className={cn(active && 'text-primary')}
              >
                <Icon />
                {`${actionLabel(key)} ${counts.get(key)}`}
              </Button>
            </Badge>
          )
        })}
      </div>
      <Button
        variant='ghost'
        size='sm'
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className='self-start'
      >
        {open ? <ChevronUp /> : <ChevronDown />}
        {open
          ? 'Hide the records'
          : `Show the ${items.length} ${items.length === 1 ? 'record' : 'records'}`}
      </Button>
      {open && (
        <PagedList
          key={action ?? 'all'}
          items={shown}
          initial={ITEMS_SHOWN}
          step={ITEMS_SHOWN * 2}
          noun={['record', 'records']}
          className='flex min-w-0 flex-col gap-1.5'
          itemKey={(item, index) =>
            `${item.node_id}-${item.action}-${item.other_id ?? ''}-${index}`
          }
        >
          {(item) => <ItemRow item={item} />}
        </PagedList>
      )}
    </div>
  )
}
