import { useState } from 'react'
import { Crown, Play } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  Paged,
  Portrait,
  Section,
} from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { type WorldState } from '@/features/overview/api'
import { mediaUrl } from '@/features/pantheon/media'
import { useSonTurn } from './api'

type SonTurnControlProps = {
  state: WorldState
}

function blockedReason(state: WorldState): string | null {
  if (!state.llm_enabled)
    return 'A son thinks with the language model, which is turned off'
  if (state.epoch_running) return 'An epoch is running'
  if (state.read_only) return 'A guest world is read-only'
  return null
}

export function SonTurnControl({ state }: SonTurnControlProps) {
  const turn = useSonTurn()
  const sons = state.sons.filter((item) => item.son.status === 'active')
  const waiting = new Set(state.pending_son_ids)
  const [chosen, setChosen] = useState<string>('')
  const selected =
    chosen ||
    String(
      sons.find((item) => waiting.has(item.son.id))?.son.id ??
        sons[0]?.son.id ??
        ''
    )
  const reason = blockedReason(state)
  return (
    <Section
      title='A single son turn'
      description='Let one son act now, outside the epoch. That turn counts as their action for this epoch.'
      surface='card'
    >
      {sons.length === 0 ? (
        <EmptyState
          size='compact'
          icon={Crown}
          title='No son can act'
          description='Summon a son, or wake a sleeping one, to let them take a turn.'
        />
      ) : (
        <>
          <ul
            aria-label='Choose a son'
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
          >
            <Paged items={sons} as='li'>
              {(item) => {
                const active = String(item.son.id) === selected
                const pending = waiting.has(item.son.id)
                return (
                  <li key={item.son.id} className='min-w-0'>
                    <Button
                      variant='outline'
                      size='lg'
                      aria-pressed={active}
                      onClick={() => setChosen(String(item.son.id))}
                      className={cn(
                        'w-full justify-start text-start',
                        active && 'border-primary bg-primary/10'
                      )}
                    >
                      <Portrait
                        name={item.son.name}
                        src={mediaUrl(item.cover)}
                        size='sm'
                        rarity={item.son.rarity}
                      />
                      <span className='flex min-w-0 flex-1 flex-col'>
                        <Text as='span' weight='medium' truncate>
                          {item.son.name}
                        </Text>
                        <Label truncate>
                          {pending ? 'Waiting' : 'Has acted'}
                        </Label>
                      </span>
                    </Button>
                  </li>
                )
              }}
            </Paged>
          </ul>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              disabled={reason !== null || !selected || turn.isPending}
              disabledReason={
                reason ??
                (turn.isPending ? 'The turn is starting' : 'Choose a son')
              }
              onClick={() =>
                turn.mutate(Number(selected), {
                  onSuccess: () => toast.success('The son takes their turn'),
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              <Play />
              Run their turn
            </Button>
            {selected && (
              <EntityLink kind='son' id={selected} showIcon>
                Open their page
              </EntityLink>
            )}
          </div>
        </>
      )}
    </Section>
  )
}
