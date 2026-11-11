import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PagedList } from '@/components/domain'
import { Muted } from '@/components/typography'

export type ChoosableNode = {
  id: number
  name: string
}

type NodeChooserProps = {
  label: string
  nodes: readonly ChoosableNode[]
  selectedId: number | undefined
  noun: [string, string]
  onSelect: (id: number) => void
}

export function NodeChooser({
  label,
  nodes,
  selectedId,
  noun,
  onSelect,
}: NodeChooserProps) {
  const [query, setQuery] = useState('')
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return nodes.filter(
      (node) => needle === '' || node.name.toLowerCase().includes(needle)
    )
  }, [nodes, query])
  return (
    <section aria-label={label} className='flex min-w-0 flex-col gap-2'>
      <Input
        type='search'
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={`Search ${noun[1]}`}
        aria-label={`Search ${noun[1]}`}
      />
      <Muted as='span' variant='caption'>
        {`${matches.length} of ${nodes.length} ${noun[1]}`}
      </Muted>
      {matches.length === 0 ? (
        <Muted>{`No ${noun[0]} is called "${query.trim()}".`}</Muted>
      ) : (
        <PagedList
          items={matches}
          initial={12}
          noun={noun}
          className='flex min-w-0 flex-col gap-1'
          itemKey={(node) => node.id}
        >
          {(node) => (
            <li>
              <Button
                variant={node.id === selectedId ? 'secondary' : 'ghost'}
                size='sm'
                className='w-full justify-start'
                aria-pressed={node.id === selectedId}
                onClick={() => onSelect(node.id)}
              >
                {node.name}
              </Button>
            </li>
          )}
        </PagedList>
      )}
    </section>
  )
}
