import { Lock, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Medallion, Section, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type SonPublic } from '@/features/pantheon/api'
import {
  POWER_EFFECT_LABEL,
  STATS,
  humanize,
  useLabels,
} from '@/features/pantheon/labels'

export function SonPowers({ view }: { view: SonPublic }) {
  const { entityType } = useLabels()
  return (
    <Section title='Powers' level={3}>
      {view.powers.length === 0 ? (
        <div className='flex min-w-0 items-center gap-2 rounded-lg border border-dashed p-3'>
          <Lock
            aria-hidden='true'
            className='size-icon-sm text-muted-foreground'
          />
          <Muted>
            No power has awakened yet; powers awaken as they rise in level.
          </Muted>
        </div>
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
          <Paged items={view.powers} as='li'>
            {(power, index) => {
              const locked = index >= view.unlocked_powers
              const parameter = power.param_stat
                ? (STATS.find((stat) => stat.key === power.param_stat)?.label ??
                  humanize(power.param_stat))
                : power.param_entity_type
                  ? entityType(power.param_entity_type)
                  : null
              return (
                <li
                  key={power.slot}
                  className={cn(
                    'flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3',
                    locked && 'border-dashed opacity-70'
                  )}
                >
                  <div className='flex min-w-0 items-center gap-2.5'>
                    <Medallion
                      icon={locked ? Lock : Sparkles}
                      tone={locked ? 'muted' : 'gold'}
                      size='sm'
                    />
                    <Text weight='semibold' truncate className='flex-1'>
                      {power.name}
                    </Text>
                  </div>
                  <div className='flex min-w-0 flex-wrap gap-1.5'>
                    <Badge size='sm' variant={locked ? 'outline' : 'default'}>
                      {POWER_EFFECT_LABEL[power.effect]}
                    </Badge>
                    {parameter && (
                      <Badge size='sm' variant='outline'>
                        {parameter}
                      </Badge>
                    )}
                    {locked && (
                      <Badge size='sm' variant='outline'>
                        <Lock />
                        Locked
                      </Badge>
                    )}
                  </div>
                  <Muted variant='caption'>{power.description}</Muted>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
    </Section>
  )
}
