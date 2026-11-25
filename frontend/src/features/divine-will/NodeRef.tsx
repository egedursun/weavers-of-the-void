import { useMemo } from 'react'
import { EntityLink } from '@/components/domain'
import { Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { type NameEntry, resolveReference } from './references'

export function NodeRef({ id, name }: { id: number; name: string }) {
  const names = useNames()
  const byId = useMemo(() => {
    const map = new Map<number, NameEntry>()
    for (const entry of names.data ?? []) map.set(entry.id, entry)
    return map
  }, [names.data])
  const target = resolveReference({ kind: 'node', id }, byId)
  if (target.type !== 'entry')
    return (
      <Text as='span' weight='medium'>
        {name || target.label}
      </Text>
    )
  return (
    <EntityLink kind={target.kind} id={target.id}>
      {name || target.label}
    </EntityLink>
  )
}
