import { useMemo, useState } from 'react'
import { Search, Wand } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { useActionCatalogue } from '../api/queries'
import { ActionCard } from './ActionCard'
import { type EntityContext } from './context'
import {
  type ActionSection,
  SECTION_DESCRIPTION,
  SECTION_ORDER,
  SECTION_TITLE,
  actionsFor,
} from './registry'
import { usePickerData } from './usePickerData'

type RecordActionsProps = {
  ctx: EntityContext
  sections?: readonly ActionSection[]
}

export function RecordActions({
  ctx,
  sections = SECTION_ORDER,
}: RecordActionsProps) {
  const catalogue = useActionCatalogue()
  const data = usePickerData()
  const [query, setQuery] = useState('')
  const items = useMemo(
    () => new Map((catalogue.data ?? []).map((item) => [item.id, item])),
    [catalogue.data]
  )
  const available = useMemo(() => new Set(items.keys()), [items])
  const specs = useMemo(() => actionsFor(ctx, available), [ctx, available])
  if (catalogue.isPending)
    return (
      <div className='flex flex-col gap-3'>
        <Skeleton className='h-control-md w-full' />
        <Skeleton className='h-control-md w-full' />
      </div>
    )
  const needle = query.trim().toLowerCase()
  const visible = specs.filter((spec) => {
    const item = items.get(spec.id)
    return item && (!needle || item.title.toLowerCase().includes(needle))
  })
  return (
    <div data-record-actions className='flex min-w-0 flex-col gap-6'>
      {specs.length > 6 && (
        <Input
          type='search'
          leadingIcon={Search}
          placeholder='Find a command'
          aria-label='Find a command'
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      )}
      {sections.map((section) => {
        const group = visible.filter((spec) => spec.section === section)
        if (group.length === 0) return null
        return (
          <Section
            key={section}
            id={`commands-${section}`}
            title={SECTION_TITLE[section]}
            description={SECTION_DESCRIPTION[section]}
            level={3}
          >
            <div className='grid min-w-0 grid-cols-1 gap-2'>
              {group.map((spec) => {
                const item = items.get(spec.id)
                return item ? (
                  <ActionCard
                    key={spec.id}
                    spec={spec}
                    item={item}
                    ctx={ctx}
                    data={data}
                  />
                ) : null
              })}
            </div>
          </Section>
        )
      })}
      {visible.length === 0 && (
        <EmptyState
          size='compact'
          icon={Wand}
          title={needle ? 'No command matches' : 'No commands here'}
          description={
            needle
              ? 'Try another word.'
              : 'Nothing more can be ordered for this record in its present state.'
          }
        />
      )}
    </div>
  )
}
