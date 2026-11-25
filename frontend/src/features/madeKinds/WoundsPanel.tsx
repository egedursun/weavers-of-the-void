import { useId, useState } from 'react'
import { Eye, Footprints, HeartPulse, Swords, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { KpiTile, FieldTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { NumberField } from '@/features/entity/realm/parts'
import { type ThingKinds, useLever } from './api'
import { numberProblem } from './model'

const FORCE_MAX = 10

export function WoundsPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  blocked: string | null
}) {
  const being = data.being
  const reasonId = useId()
  const [force, setForce] = useState('1')
  const [reason, setReason] = useState('')
  const strike = useLever(
    'cosmic_wound:strike',
    (_: void) => ({
      being_id: nodeId,
      force: Number(force),
      ...(reason.trim() ? { reason: reason.trim() } : {}),
    }),
    'The blow lands'
  )
  if (!being) return null
  const busy = why(
    blocked ?? (being.held ? 'This being is held against change' : null),
    strike.isPending
  )
  const badForce = numberProblem(force, 1, FORCE_MAX)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted variant='caption'>
        Only a cosmic or outer being bears wounds of this kind; its body grows
        the first time it is struck, and its might, roaming and sight fall with
        what it suffers until it heals or falls.
      </Muted>
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-2'>
          <KpiTile
            label='Health'
            value={
              being.hp !== null && being.hp_max !== null
                ? `${being.hp} of ${being.hp_max}`
                : 'whole'
            }
            icon={HeartPulse}
            tone={
              being.hp !== null && being.hp_max !== null
                ? being.hp < being.hp_max / 2
                  ? 'danger'
                  : being.hp < being.hp_max
                    ? 'warning'
                    : 'success'
                : 'success'
            }
            meter={
              being.hp !== null && being.hp_max
                ? { value: being.hp, max: being.hp_max, label: 'Health' }
                : undefined
            }
          />
          <KpiTile
            label='Might it can bring'
            value={
              being.effective_might !== null && being.might !== null
                ? `${being.effective_might} of ${being.might}`
                : 'not a cosmic being'
            }
            icon={Swords}
            tone='warning'
            meter={
              being.effective_might !== null
                ? {
                    value: being.effective_might,
                    max: SPAN,
                    label: 'Might it can bring',
                  }
                : undefined
            }
          />
          <KpiTile
            label='Vitality'
            value={being.vital ?? 'unharmed'}
            icon={HeartPulse}
            tone='danger'
            meter={
              being.vital !== null
                ? { value: being.vital, max: SPAN, label: 'Vitality' }
                : undefined
            }
          />
          <KpiTile
            label='Mobility'
            value={being.mobility ?? 'unharmed'}
            icon={Footprints}
            tone='info'
            meter={
              being.mobility !== null
                ? { value: being.mobility, max: SPAN, label: 'Mobility' }
                : undefined
            }
          />
          <KpiTile
            label='Sight'
            value={being.sight ?? 'unharmed'}
            icon={Eye}
            tone='verdigris'
            meter={
              being.sight !== null
                ? { value: being.sight, max: SPAN, label: 'Sight' }
                : undefined
            }
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Badge size='sm' variant={being.roams ? 'success' : 'destructive'}>
          <Footprints />
          {being.roams ? 'Can roam' : 'Too hurt to roam'}
        </Badge>
        <Badge size='sm' variant={being.sees ? 'success' : 'destructive'}>
          <Eye />
          {being.sees ? 'Can find worlds' : 'Too hurt to find worlds'}
        </Badge>
        <Badge size='sm' variant={being.wounds ? 'warning' : 'outline'}>
          <HeartPulse />
          {being.wounds === 1 ? '1 open wound' : `${being.wounds} open wounds`}
        </Badge>
        <Badge size='sm' variant='outline'>
          {being.grown ? 'Its body has grown' : 'No body grown yet'}
        </Badge>
      </div>
      <div className='@container/form min-w-0'>
        <div className='grid min-w-0 grid-cols-1 items-end gap-2 @lg/form:grid-cols-3'>
          <NumberField
            label='Force of the blow'
            icon={Zap}
            value={force}
            min={1}
            max={FORCE_MAX}
            blocked={busy}
            onChange={setForce}
          />
          <FieldTile id={reasonId} label='Why it falls'>
            <Input
              id={reasonId}
              value={reason}
              maxLength={200}
              placeholder='Optional'
              disabled={busy !== null}
              onChange={(event) => setReason(event.target.value)}
            />
          </FieldTile>
          <Button
            act={strike}
            size='sm'
            variant='destructive'
            disabled={(busy ?? badForce) !== null}
            disabledReason={busy ?? badForce ?? undefined}
            onClick={() => strike.mutate()}
          >
            <Zap />
            Strike it
          </Button>
        </div>
      </div>
    </div>
  )
}
