import { type ReactNode } from 'react'
import { type UseQueryResult } from '@tanstack/react-query'
import { AlertTriangle, type LucideIcon } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { useCosmos } from '@/features/cosmos/api'
import { MindPicker } from '@/features/entity/mind/parts'

export function QuerySection<T>({
  id,
  title,
  description,
  icon,
  tone,
  query,
  children,
}: {
  id: string
  title: string
  description?: string
  icon: LucideIcon
  tone: KpiTone
  query: UseQueryResult<T>
  children: (data: T) => ReactNode
}) {
  return (
    <Section
      id={id}
      title={title}
      description={description}
      icon={icon}
      tone={tone}
    >
      {query.isPending ? (
        <Skeleton className='h-control-lg w-full' />
      ) : query.isError ? (
        <EmptyState
          icon={AlertTriangle}
          size='inline'
          title={`${title} could not be read`}
          description={query.error.message}
        />
      ) : (
        children(query.data)
      )}
    </Section>
  )
}

export function WorldPicker({
  value,
  onPick,
  busy,
  label = 'World',
}: {
  value: string
  onPick: (value: string) => void
  busy: string | null
  label?: string
}) {
  const cosmos = useCosmos()
  const worlds = Object.fromEntries(
    (cosmos.data?.worlds ?? []).map((row) => [
      String(row.world.id),
      row.world.name,
    ])
  )
  return (
    <MindPicker
      label={label}
      value={value}
      table={worlds}
      blocked={busy}
      onPick={onPick}
    />
  )
}
