import { useEffect, useState } from 'react'
import { Search, Wrench } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import { EmptyState } from './EmptyState'
import { ShowMore } from './ShowMore'
import { ToolCard, type ToolCardData } from './ToolCard'
import { REVEAL_TOOL_EVENT } from './revealTool'
import { toolTitle } from './toolTitle'
import { useShowMore } from './useShowMore'

const SEARCH_FROM = 8
const TOOLS_SHOWN = 6

type ToolListProps = {
  tools: ToolCardData[]
  columns?: 1 | 2
  initial?: number
}

function matches(tool: ToolCardData, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase()
  if (!needle) return true
  return [tool.name, toolTitle(tool.name), tool.description].some((text) =>
    text.toLocaleLowerCase().includes(needle)
  )
}

export function ToolList({
  tools,
  columns = 1,
  initial = TOOLS_SHOWN,
}: ToolListProps) {
  const [query, setQuery] = useState('')
  const filtered = tools.filter((tool) => matches(tool, query))
  const page = useShowMore(filtered, initial)
  const { all } = page
  const names = tools.map((tool) => tool.name).join(',')
  useEffect(() => {
    const known = new Set(names.split(','))
    const reveal = (event: Event) => {
      if (!(event instanceof CustomEvent)) return
      if (typeof event.detail !== 'string' || !known.has(event.detail)) return
      setQuery('')
      all()
    }
    window.addEventListener(REVEAL_TOOL_EVENT, reveal)
    return () => window.removeEventListener(REVEAL_TOOL_EVENT, reveal)
  }, [all, names])
  return (
    <div data-domain='tool-list' className='flex min-w-0 flex-col gap-3'>
      {tools.length >= SEARCH_FROM && (
        <Input
          type='search'
          leadingIcon={Search}
          placeholder={`Find among ${tools.length} tools`}
          aria-label='Find a tool'
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            page.less()
          }}
        />
      )}
      {filtered.length === 0 ? (
        <EmptyState
          size='compact'
          icon={Wrench}
          title='No tool matches'
          description='Try another word from its name or description.'
        />
      ) : (
        <div
          className={cn(
            'grid min-w-0 grid-cols-1 gap-2',
            columns === 2 && 'lg:grid-cols-2'
          )}
        >
          {page.visible.map((tool) => (
            <ToolCard key={tool.id ?? tool.name} tool={tool} />
          ))}
        </div>
      )}
      <ShowMore state={page} noun={['tool', 'tools']} />
    </div>
  )
}
