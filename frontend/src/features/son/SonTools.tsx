import { RotateCcw, Wrench } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { turnCounterValues } from '@/api/generated/schema'
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
import { Section, ToolList, toolTitle, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type SonToolsView, sonKeys, useSonTools } from './api'

const BLOCK_REASON: Record<SonToolsView['blocked'][number]['reason'], string> =
  {
    rarity: 'Rarity too low',
    actor_type: 'Wrong kind of actor',
    civilization_tier: 'Civilization too young',
    world_state: 'The world does not allow it yet',
    unwired: 'Not connected',
  }

export function SonTools({ sonId, name }: { sonId: number; name: string }) {
  const query = useSonTools(sonId)
  const { reason } = useGodGate()
  const reset = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/reset-counters', {
          params: { path: { son_id: sonId } },
        })
      ),
    invalidate: [sonKeys.detail(sonId)],
  })
  const data = query.data
  return (
    <Section
      id='section-tools'
      title='Tools'
      description={`The tools ${name} can use right now, by their rarity and the state of the world, with their live costs and wording.`}
      level={3}
    >
      {query.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : query.isError ? (
        <Muted>{query.error.message}</Muted>
      ) : (
        data && (
          <div className='flex min-w-0 flex-col gap-4'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant='outline'>{RARITY_LABEL[data.rarity]}</Badge>
              <Badge variant='secondary'>
                {data.action_points_left === null
                  ? 'Not acting yet this epoch'
                  : `${plural(data.action_points_left, 'action', 'actions')} left`}
              </Badge>
              <Badge variant='outline'>{`${data.available.length} usable`}</Badge>
            </div>
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Per-epoch counters</Label>
              {data.counters.length === 0 ? (
                <Muted>No limited tool has been used this epoch.</Muted>
              ) : (
                <div className='flex min-w-0 flex-wrap gap-2'>
                  <Paged items={data.counters}>
                    {(counter) => (
                      <Badge key={counter.counter} variant='secondary'>
                        {`${wordOf(turnCounterValues, counter.counter)}: ${counter.value}`}
                      </Badge>
                    )}
                  </Paged>
                </div>
              )}
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <ActionButton
                  label='Reset their counters'
                  icon={RotateCcw}
                  blocked={
                    reason() ??
                    (data.counters.length === 0 ? 'Nothing to reset.' : null)
                  }
                  pending={reset.isPending}
                  confirm={{
                    title: 'Reset their counters?',
                    description: `${name} may use limited tools again this epoch.`,
                  }}
                  onRun={() => reset.mutate()}
                />
              </div>
            </div>
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
              <Collapsible className='flex min-w-0 flex-col gap-2'>
                <CollapsibleTrigger asChild>
                  <Button variant='ghost' size='sm' className='self-start'>
                    <Wrench />
                    {`Locked tools (${data.blocked.length})`}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
                  <Paged items={data.blocked}>
                    {(tool) => (
                      <div
                        key={tool.name}
                        className='flex min-w-0 items-center justify-between gap-2 rounded-md px-2.5 py-1.5 sealed-well'
                      >
                        <Text as='span' truncate>
                          {toolTitle(tool.name)}
                        </Text>
                        <Badge size='sm' variant='outline'>
                          {tool.minimum_rarity
                            ? `${BLOCK_REASON[tool.reason]}: ${RARITY_LABEL[tool.minimum_rarity]}`
                            : BLOCK_REASON[tool.reason]}
                        </Badge>
                      </div>
                    )}
                  </Paged>
                </CollapsibleContent>
              </Collapsible>
            )}
          </div>
        )
      )}
    </Section>
  )
}
