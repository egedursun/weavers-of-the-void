import {
  Crown,
  Ghost,
  Landmark,
  Library,
  Users,
  UsersRound,
} from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { MiniStat } from '@/components/domain'
import { Label, Muted, Stat } from '@/components/typography'
import { useWorldPulse } from './api'

const PERCENT = 100

export function WorldPulse({ worldId }: { worldId: number }) {
  const pulse = useWorldPulse(worldId)
  if (!pulse.data) return null
  const data = pulse.data
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Label variant='overline'>World balance</Label>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={Users}
          tone='info'
          label='Communities'
          value={data.communities}
        />
        <MiniStat
          icon={Ghost}
          tone={data.godless > 0 ? 'warning' : 'muted'}
          label='Godless'
          value={data.godless}
        />
        <MiniStat
          icon={Landmark}
          tone='verdigris'
          label='Factions'
          value={data.factions}
        />
        <MiniStat
          icon={UsersRound}
          tone='gold'
          label='Cults'
          value={data.cults}
        />
        <MiniStat
          icon={Crown}
          tone='gold'
          label='Sons here'
          value={data.sons}
          hint={
            data.son_share !== null
              ? `Its fair share is ${data.son_share} sons`
              : undefined
          }
        />
        <MiniStat
          icon={Library}
          label='Named mortals'
          value={data.named_mortals}
        />
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Muted variant='caption'>
            Records born this epoch against the quota
          </Muted>
          <Stat value={data.this_epoch} unit={`/ ${data.quota}`} />
        </div>
        <Progress
          size='sm'
          tone={data.this_epoch < data.quota ? 'warning' : 'success'}
          value={
            data.quota > 0
              ? Math.min(PERCENT, (data.this_epoch / data.quota) * PERCENT)
              : PERCENT
          }
          aria-label='Record quota this epoch'
        />
        <Muted variant='caption'>
          {`${data.engine_records} records born over the last ${data.window} epochs, ${data.per_epoch} an epoch on average`}
        </Muted>
      </div>
    </div>
  )
}
