import { Lightbulb, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Text } from '@/components/typography'
import { ShowMore } from './ShowMore'
import { useShowMore } from './useShowMore'

const LINES_SHOWN = 6

export type ServerLine = {
  key: string
  text: string
  tension?: boolean
  tools?: string[]
}

type ServerLineListProps = {
  lines: ServerLine[]
  emptyText: string
  onTool?: (tool: string) => void
}

export function ServerLineList({
  lines,
  emptyText,
  onTool,
}: ServerLineListProps) {
  const page = useShowMore(lines, LINES_SHOWN)
  if (lines.length === 0)
    return emptyText ? <Text tone='muted'>{emptyText}</Text> : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ul data-domain='server-lines' className='flex min-w-0 flex-col gap-3'>
        {page.visible.map((line) => {
          const Icon = line.tension ? TriangleAlert : Lightbulb
          return (
            <li key={line.key} className='flex min-w-0 items-start gap-2'>
              <Icon
                aria-hidden='true'
                className={
                  line.tension
                    ? 'size-icon-sm shrink-0 text-warning'
                    : 'size-icon-sm shrink-0 text-primary'
                }
              />
              <div className='flex min-w-0 flex-col gap-2'>
                <Text>{line.text}</Text>
                {line.tools && line.tools.length > 0 && (
                  <div className='flex min-w-0 flex-wrap gap-1'>
                    {line.tools.map((tool) =>
                      onTool ? (
                        <Badge key={tool} variant='outline' asChild>
                          <button type='button' onClick={() => onTool(tool)}>
                            {tool}
                          </button>
                        </Badge>
                      ) : (
                        <Badge key={tool} variant='outline'>
                          {tool}
                        </Badge>
                      )
                    )}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ul>
      <ShowMore state={page} noun={['line', 'lines']} />
    </div>
  )
}
