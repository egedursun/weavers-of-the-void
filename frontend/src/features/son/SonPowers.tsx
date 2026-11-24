import { Hammer, Lock, Pencil, Sparkles, Trash2 } from 'lucide-react'
import { statValues } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Medallion, Section, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { RowAction } from '@/features/entity/actions/RowAction'
import { wordOf } from '@/features/entity/affairs/labels'
import { type SonPublic } from '@/features/pantheon/api'
import {
  POWER_EFFECT_LABEL,
  STATS,
  useLabels,
} from '@/features/pantheon/labels'

const POWER_LABELS = {
  name: 'Name',
  description: 'What it does',
  effect: 'Effect',
  param_entity_type: 'Bends a kind of thing',
  param_stat: 'Bends a stat',
}

function ForgePower({ view }: { view: SonPublic }) {
  const taken = new Set(view.powers.map((power) => power.slot))
  const slots = Array.from(
    { length: view.power_slots },
    (_, slot) => slot
  ).filter((slot) => !taken.has(slot))
  const free = slots[0]
  if (free === undefined) return null
  return (
    <RowAction
      path='/api/actions/son:power'
      icon={Hammer}
      label='Forge a power'
      fixed={{ son_id: view.son.id, slot: free }}
      hide={['remove']}
      labels={POWER_LABELS}
      multiline={['description']}
      note={`It takes slot ${free + 1}; a power past their unlocked count stays sealed until they rise.`}
    />
  )
}

export function SonPowers({ view }: { view: SonPublic }) {
  const { entityType } = useLabels()
  return (
    <Section
      id='section-son-powers'
      title='Powers'
      level={3}
      actions={<ForgePower view={view} />}
    >
      {view.powers.length === 0 ? (
        <div className='flex min-w-0 items-center gap-2 rounded-md p-3 sealed-well'>
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
                  wordOf(statValues, power.param_stat))
                : power.param_entity_type
                  ? entityType(power.param_entity_type)
                  : null
              return (
                <li
                  key={power.slot}
                  className={cn(
                    'flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3',
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
                  <div className='flex min-w-0 flex-wrap justify-end gap-1'>
                    <RowAction
                      path='/api/actions/son:power'
                      icon={Pencil}
                      label={`Reshape ${power.name}`}
                      iconOnly
                      fixed={{ son_id: view.son.id, slot: power.slot }}
                      hide={['remove']}
                      defaults={{
                        name: power.name,
                        description: power.description,
                        effect: power.effect,
                        param_entity_type: power.param_entity_type ?? null,
                        param_stat: power.param_stat ?? null,
                      }}
                      labels={POWER_LABELS}
                      multiline={['description']}
                    />
                    <RowAction
                      path='/api/actions/son:power'
                      icon={Trash2}
                      label={`Unmake ${power.name}`}
                      iconOnly
                      destructive
                      fixed={{
                        son_id: view.son.id,
                        slot: power.slot,
                        remove: true,
                      }}
                      hide={[
                        'name',
                        'description',
                        'effect',
                        'param_entity_type',
                        'param_stat',
                      ]}
                      confirm={`Unmake ${power.name}? Nothing returns to you; tearing it away by the hand of god gives essence back instead.`}
                    />
                  </div>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
    </Section>
  )
}
