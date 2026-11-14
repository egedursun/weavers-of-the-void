import { Bot } from 'lucide-react'
import { plural } from '@/lib/units'
import { RARITY_LABEL } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { Section, ToolList, toolTitle, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { humanize } from '../actions/schema'
import { useEntityAgentContext } from '../api/queries'

export function EntityAgentContext({
  entityId,
  name,
}: {
  entityId: number
  name: string
}) {
  const query = useEntityAgentContext(entityId, true)
  const data = query.data
  return (
    <Section
      id='section-agent'
      title='Agent context'
      description={`The exact prompts and tools ${name} would receive if it were given a turn now. Nothing is sent.`}
    >
      {query.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : query.isError ? (
        <Muted>{query.error.message}</Muted>
      ) : (
        data && (
          <div className='flex min-w-0 flex-col gap-4'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant='secondary'>{`${plural(data.action_points, 'action', 'actions')}`}</Badge>
              <Badge variant='outline'>{`${data.available.length} usable tools`}</Badge>
              <Paged items={data.counters}>
                {(counter) => (
                  <Badge key={counter.counter} variant='outline'>
                    {`${humanize(counter.counter)}: ${counter.value}`}
                  </Badge>
                )}
              </Paged>
            </div>
            <Collapsible className='flex min-w-0 flex-col gap-2'>
              <CollapsibleTrigger asChild>
                <Button variant='ghost' size='sm' className='self-start'>
                  <Bot />
                  Show the prompts
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
                <Label variant='overline'>System prompt</Label>
                <Textarea
                  readOnly
                  value={data.system_prompt}
                  aria-label='System prompt'
                />
                <Label variant='overline'>Turn prompt</Label>
                <Textarea
                  readOnly
                  value={data.user_prompt}
                  aria-label='Turn prompt'
                />
              </CollapsibleContent>
            </Collapsible>
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>{`Tools it can use · ${data.available.length}`}</Label>
              <ToolList
                tools={data.available.map((tool) => ({
                  name: tool.name,
                  description: tool.description,
                  fields: tool.fields,
                  actionCost: tool.action_cost,
                  essenceCost: tool.essence_cost,
                  readOnly: tool.read_only,
                  longJob: tool.long_job,
                  minimumRarity: tool.minimum_rarity
                    ? RARITY_LABEL[tool.minimum_rarity]
                    : null,
                }))}
              />
              {data.blocked.length > 0 && (
                <Text
                  tone='muted'
                  variant='caption'
                >{`Locked: ${data.blocked.map((tool) => toolTitle(tool.name)).join(', ')}.`}</Text>
              )}
            </div>
          </div>
        )
      )}
    </Section>
  )
}
