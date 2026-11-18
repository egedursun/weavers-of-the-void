import { Feather } from 'lucide-react'
import { EntityLink } from '@/components/domain/EntityLink'
import { Muted } from '@/components/typography'

export function KeeperName({
  id,
  name,
  fallback,
}: {
  id: number | null | undefined
  name: string | null | undefined
  fallback: string
}) {
  if (id == null) return <>{name ?? fallback}</>
  return (
    <EntityLink kind='entity' id={String(id)} showIcon>
      {name ?? fallback}
    </EntityLink>
  )
}

export function KeeperByline({
  lead,
  id,
  name,
  detail,
  fallback,
}: {
  lead: string
  id: number | null | undefined
  name: string | null | undefined
  detail?: string | null
  fallback: string
}) {
  return (
    <Muted
      as='p'
      variant='caption'
      className='flex min-w-0 flex-wrap items-center gap-x-1'
    >
      <Feather aria-hidden='true' className='size-icon-xs shrink-0' />
      <span>{lead}</span>
      <KeeperName id={id} name={name} fallback={fallback} />
      {detail && <span>{`· ${detail}`}</span>}
    </Muted>
  )
}
