import { useState } from 'react'
import { ChevronDown, ChevronUp, ListTree, Sparkles, Zap } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label, Muted, Text } from '@/components/typography'
import { ExpandableText } from './ExpandableText'
import { ToolIcon } from './ToolIcon'
import { toolAnchor } from './revealTool'
import { toolTitle } from './toolTitle'

export type ToolCardData = {
  id?: string
  name: string
  description: string
  fields?: Record<string, string>
  actionCost: number
  essenceCost: number
  readOnly: boolean
  longJob: boolean
  minimumRarity?: string | null
}

export function ToolCard({ tool }: { tool: ToolCardData }) {
  const [open, setOpen] = useState(false)
  const fields = Object.entries(tool.fields ?? {})
  return (
    <article
      id={toolAnchor(tool.name)}
      data-domain='tool-card'
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <span className='flex size-control-sm shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary'>
          <ToolIcon tool={tool.name} />
        </span>
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {toolTitle(tool.name)}
          </Text>
          <Muted as='span' variant='caption' truncate className='font-mono'>
            {tool.name}
          </Muted>
        </div>
        <div className='flex shrink-0 flex-wrap items-center justify-end gap-1'>
          {tool.actionCost > 0 && (
            <Badge size='sm' variant='secondary'>
              <Zap />
              {`${formatInteger(tool.actionCost)} action${tool.actionCost === 1 ? '' : 's'}`}
            </Badge>
          )}
          {tool.essenceCost > 0 && (
            <Badge size='sm' variant='default'>
              <Sparkles />
              {formatInteger(tool.essenceCost)}
            </Badge>
          )}
          {tool.readOnly && (
            <Badge size='sm' variant='outline'>
              free to read
            </Badge>
          )}
          {tool.longJob && (
            <Badge size='sm' variant='warning'>
              long job
            </Badge>
          )}
          {tool.minimumRarity && (
            <Badge size='sm' variant='outline'>
              {`from ${tool.minimumRarity}`}
            </Badge>
          )}
        </div>
      </div>
      <ExpandableText variant='caption' tone='muted' lines={2}>
        {tool.description}
      </ExpandableText>
      {fields.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Button
            variant='ghost'
            size='sm'
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className='self-start'
          >
            <ListTree />
            {`${fields.length} ${fields.length === 1 ? 'parameter' : 'parameters'}`}
            {open ? <ChevronUp /> : <ChevronDown />}
          </Button>
          {open && (
            <dl className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2.5'>
              {fields.map(([field, text]) => (
                <div key={field} className='flex min-w-0 flex-col gap-0.5'>
                  <Label as='dt' variant='overline' truncate>
                    {field}
                  </Label>
                  <Text as='dd' variant='caption'>
                    {text}
                  </Text>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </article>
  )
}
