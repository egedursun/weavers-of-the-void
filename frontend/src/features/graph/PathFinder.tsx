import { useId } from 'react'
import { ArrowRight, Route as RouteIcon, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NodeOptions, NodePicker, type PickableNode } from './NodePicker'
import { type PathResult, usePath } from './api'
import { drawerKindOf, linkLabel } from './graphModel'

export type PathNode = PickableNode & { kind: string }

type PathFinderProps = {
  nodes: readonly PathNode[]
  from: number | null
  to: number | null
  onChange: (from: number | null, to: number | null) => void
  linkLabels: ReadonlyMap<string, string>
}

const NOT_FOUND =
  'No link within six steps; these two are in separate corners of the world.'

function NodeName({
  id,
  name,
  kinds,
}: {
  id: number
  name: string
  kinds: ReadonlyMap<number, string>
}) {
  const kind = drawerKindOf(kinds.get(id))
  if (!kind)
    return (
      <Text as='span' weight='medium'>
        {name}
      </Text>
    )
  return (
    <EntityLink kind={kind} id={kind === 'creator' ? undefined : String(id)}>
      {name}
    </EntityLink>
  )
}

function PathChain({
  result,
  kinds,
  linkLabels,
}: {
  result: PathResult
  kinds: ReadonlyMap<number, string>
  linkLabels: ReadonlyMap<string, string>
}) {
  if (!result.found) return <Muted>{NOT_FOUND}</Muted>
  const name = (id: number) => result.names[String(id)] ?? `Record ${id}`
  return (
    <div data-path-result className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        {result.path.map((id, index) => (
          <span
            key={`${id}-${index}`}
            className='inline-flex min-w-0 items-center gap-1'
          >
            {index > 0 && (
              <ArrowRight
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-muted-foreground'
              />
            )}
            <NodeName id={id} name={name(id)} kinds={kinds} />
          </span>
        ))}
      </div>
      <ol className='flex min-w-0 list-decimal flex-col gap-1.5 ps-5'>
        {result.steps.map((step, index) => {
          const [left, right] = step.forward
            ? [step.source, step.target]
            : [step.target, step.source]
          return (
            <li key={index} className='min-w-0'>
              <Text as='span'>
                {name(left)}{' '}
                <Text as='span' weight='semibold'>
                  {linkLabel({ kind: step.kind, past: false }, linkLabels)}
                </Text>{' '}
                {name(right)}
                {step.description && (
                  <Muted as='span'>{` — ${step.description}`}</Muted>
                )}
              </Text>
            </li>
          )
        })}
      </ol>
      <Muted variant='caption'>
        {result.steps.length === 0
          ? 'That is the same record.'
          : `Connected in ${result.steps.length} ${result.steps.length === 1 ? 'step' : 'steps'}.`}
      </Muted>
    </div>
  )
}

export function PathFinder({
  nodes,
  from,
  to,
  onChange,
  linkLabels,
}: PathFinderProps) {
  const listId = useId()
  const path = usePath(from, to)
  const kinds = new Map(nodes.map((node) => [node.id, node.kind]))
  return (
    <div data-path-finder className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-col gap-2'>
        <NodePicker
          nodes={nodes}
          value={from}
          onPick={(id) => onChange(id, to)}
          label='First record'
          placeholder='First…'
          listId={listId}
        />
        <NodePicker
          nodes={nodes}
          value={to}
          onPick={(id) => onChange(from, id)}
          label='Second record'
          placeholder='Second…'
          listId={listId}
        />
        <NodeOptions id={listId} nodes={nodes} />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          onClick={() => void path.refetch()}
          disabled={from === null || to === null}
          disabledReason='Pick both records from the list.'
        >
          <RouteIcon />
          Find
        </Button>
        {(from !== null || to !== null) && (
          <Button
            size='sm'
            variant='ghost'
            onClick={() => onChange(null, null)}
          >
            <X />
            Clear
          </Button>
        )}
      </div>
      <Muted variant='caption'>
        or click a record, then Shift+click the second.
      </Muted>
      {path.isFetching && !path.data && <Skeleton className='h-16 w-full' />}
      {path.error && (
        <Text variant='caption' tone='destructive'>
          {path.error.message}
        </Text>
      )}
      {path.data && from !== null && to !== null && (
        <PathChain result={path.data} kinds={kinds} linkLabels={linkLabels} />
      )}
    </div>
  )
}
