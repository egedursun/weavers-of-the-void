import { Fragment, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, ArrowRight, Route, Waypoints } from 'lucide-react'
import { nodeKindValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, FormRow, Paged, Section } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { entryKindOf } from '@/features/chronicle/linkTargets'
import { wordOf } from '@/features/entity/affairs/labels'
import { humanize } from '../actions/schema'
import { useCatalogue, useNames, usePath } from '../api/queries'
import { type NameEntry } from '../api/types'

const remembered = new Map<number, number>()

type PathFinderProps = {
  fromId: number
  fromName: string
}

function NodeName({
  id,
  name,
  entry,
}: {
  id: number
  name: string
  entry?: NameEntry
}) {
  const kind = entry ? entryKindOf(entry.kind) : undefined
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

export function PathFinder({ fromId, fromName }: PathFinderProps) {
  const names = useNames()
  const catalogue = useCatalogue()
  const [target, setTarget] = useState<number | null>(
    remembered.get(fromId) ?? null
  )
  const path = usePath(fromId, target)
  const index = useMemo(
    () => new Map((names.data ?? []).map((entry) => [entry.id, entry])),
    [names.data]
  )
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter((entry) => entry.id !== fromId)
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint:
            entry.kind === 'entity'
              ? humanize(entry.type)
              : wordOf(nodeKindValues, entry.kind),
        })),
    [names.data, fromId]
  )
  const labelOf = (kind: string) =>
    catalogue.data?.bond_kinds.find((item) => item.key === kind)?.label ??
    humanize(kind)
  const choose = (value: string | null) => {
    const next = value === null ? null : Number(value)
    if (next === null) remembered.delete(fromId)
    else remembered.set(fromId, next)
    setTarget(next)
  }
  const result = path.data
  return (
    <Section
      id='section-path'
      title='How are they connected?'
      description='The shortest chain of bonds between two things: records, sons, the Creator, worlds or foreign gods.'
    >
      <FormRow label={`From ${fromName} to`}>
        {(id) => (
          <RecordCombobox
            id={id}
            options={options}
            value={target === null ? null : String(target)}
            onChange={choose}
            placeholder='Choose any named thing'
            clearable
            aria-label='Connected to'
          />
        )}
      </FormRow>
      <div>
        <Button variant='outline' size='sm' asChild>
          <Link
            to='/network'
            search={
              target === null ? { from: fromId } : { from: fromId, to: target }
            }
          >
            <Waypoints />
            Open in the network
          </Link>
        </Button>
      </div>
      {path.isFetching && !result && (
        <Skeleton className='h-control-md w-full' />
      )}
      {path.isError && <Text tone='destructive'>{path.error.message}</Text>}
      {result && !result.found && (
        <Muted>
          No bond chain was found within six steps. They may not know each other
          at all.
        </Muted>
      )}
      {result?.found && (
        <ol aria-label='Bond chain' className='flex min-w-0 flex-col gap-2'>
          <Paged items={result.path} as='li'>
            {(nodeId, position) => {
              const step = result.steps[position]
              const name = result.names[String(nodeId)] ?? `Node ${nodeId}`
              return (
                <Fragment key={`${nodeId}-${position}`}>
                  <li className='flex min-w-0 items-center gap-2'>
                    <Route
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                    <NodeName
                      id={nodeId}
                      name={name}
                      entry={index.get(nodeId)}
                    />
                  </li>
                  {step && (
                    <li className='flex min-w-0 items-center gap-2 ps-6'>
                      {step.forward ? (
                        <ArrowRight
                          aria-hidden='true'
                          className='size-icon-xs shrink-0 text-muted-foreground'
                        />
                      ) : (
                        <ArrowLeft
                          aria-hidden='true'
                          className='size-icon-xs shrink-0 text-muted-foreground'
                        />
                      )}
                      <Muted as='span' variant='caption' truncate>
                        {step.description
                          ? `${labelOf(step.kind)} · ${step.description}`
                          : labelOf(step.kind)}
                      </Muted>
                    </li>
                  )}
                </Fragment>
              )
            }}
          </Paged>
        </ol>
      )}
    </Section>
  )
}
