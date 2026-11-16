import { type KeyboardEvent, useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { GenerateImageMini } from '@/features/images/GenerateImageMini'
import { Highlight } from './Highlight'
import { type AtlasNode, countLeaves, flattenVisible } from './atlasModel'
import { KIND_TONE, nodeIcon } from './nodeVisuals'

const INDENT = [
  'ps-0',
  'ps-4',
  'ps-8',
  'ps-12',
  'ps-16',
  'ps-20',
  'ps-24',
  'ps-28',
  'ps-32',
] as const

type AtlasTreeProps = {
  nodes: AtlasNode[]
  open: ReadonlySet<string>
  onToggle: (key: string, open: boolean) => void
  selected: string | null
  onSelect: (node: AtlasNode) => void
  onActivate: (node: AtlasNode) => void
  query: string
  imageWorkerOn: boolean
}

export function AtlasTree({
  nodes,
  open,
  onToggle,
  selected,
  onSelect,
  onActivate,
  query,
  imageWorkerOn,
}: AtlasTreeProps) {
  const rows = useMemo(() => flattenVisible(nodes, open), [nodes, open])
  const counts = useMemo(() => {
    const map = new Map<string, number>()
    for (const row of rows)
      if (row.node.kind === 'group')
        map.set(row.node.key, countLeaves(row.node))
    return map
  }, [rows])
  const [focused, setFocused] = useState<string | null>(null)
  const active =
    focused && rows.some((row) => row.node.key === focused)
      ? focused
      : (selected ?? rows[0]?.node.key ?? null)
  const focusRow = (key: string) => {
    setFocused(key)
    document.getElementById(`atlas-row-${key}`)?.focus()
  }
  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    const index = rows.findIndex((row) => row.node.key === active)
    if (index < 0) return
    const row = rows[index]
    const expandable = row.node.children.length > 0
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        if (rows[index + 1]) focusRow(rows[index + 1].node.key)
        break
      case 'ArrowUp':
        event.preventDefault()
        if (rows[index - 1]) focusRow(rows[index - 1].node.key)
        break
      case 'ArrowRight':
        event.preventDefault()
        if (expandable && !open.has(row.node.key)) onToggle(row.node.key, true)
        else if (expandable && rows[index + 1])
          focusRow(rows[index + 1].node.key)
        break
      case 'ArrowLeft':
        event.preventDefault()
        if (expandable && open.has(row.node.key)) onToggle(row.node.key, false)
        else if (row.parent) focusRow(row.parent)
        break
      case 'Enter':
        event.preventDefault()
        onActivate(row.node)
        break
      case ' ':
        event.preventDefault()
        onSelect(row.node)
        break
      default:
        break
    }
  }
  return (
    <ul
      role='tree'
      aria-label='Atlas tree'
      className='flex min-w-0 flex-col'
      onKeyDown={onKeyDown}
    >
      <Paged items={rows} as='li'>
        {({ node, depth }) => {
          const Icon = nodeIcon(node)
          const expandable = node.children.length > 0
          const isOpen = open.has(node.key)
          const isSelected = selected === node.key
          return (
            <li
              key={node.key}
              id={`atlas-row-${node.key}`}
              role='treeitem'
              aria-level={depth + 1}
              aria-expanded={expandable ? isOpen : undefined}
              aria-selected={isSelected}
              tabIndex={node.key === active ? 0 : -1}
              onFocus={() => setFocused(node.key)}
              onClick={() => onSelect(node)}
              onDoubleClick={() =>
                expandable ? onToggle(node.key, !isOpen) : onActivate(node)
              }
              className={cn(
                'group flex min-w-0 cursor-pointer items-center gap-1 rounded-md pe-1 outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring',
                INDENT[Math.min(depth, INDENT.length - 1)],
                isSelected && 'bg-accent text-accent-foreground'
              )}
            >
              {expandable ? (
                <Button
                  variant='ghost'
                  size='icon-sm'
                  tabIndex={-1}
                  aria-label={
                    isOpen ? `Close ${node.label}` : `Open ${node.label}`
                  }
                  onClick={(event) => {
                    event.stopPropagation()
                    onToggle(node.key, !isOpen)
                  }}
                >
                  {isOpen ? <ChevronDown /> : <ChevronRight />}
                </Button>
              ) : (
                <span aria-hidden='true' className='size-control-sm shrink-0' />
              )}
              <Icon
                aria-hidden='true'
                className={cn('size-icon-sm shrink-0', KIND_TONE[node.kind])}
              />
              <Text as='span' truncate className='min-w-0 flex-1'>
                <Highlight text={node.label} query={query} />
              </Text>
              {node.kind === 'group' ? (
                <Muted as='span' variant='caption'>
                  {formatInteger(counts.get(node.key) ?? 0)}
                </Muted>
              ) : node.hint ? (
                <Muted
                  as='span'
                  variant='caption'
                  truncate
                  className='hidden max-w-1/3 sm:block'
                >
                  {node.hint}
                </Muted>
              ) : null}
              {node.kind === 'entity' &&
                node.id !== undefined &&
                imageWorkerOn && (
                  <span className='flex opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100'>
                    <GenerateImageMini nodeId={node.id} name={node.label} />
                  </span>
                )}
            </li>
          )
        }}
      </Paged>
    </ul>
  )
}
