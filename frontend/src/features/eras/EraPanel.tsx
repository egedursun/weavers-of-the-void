import { FlaskConical, Gauge } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { Facts } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type ErasNodeView, useEraAction } from './api'
import { BARRED_ICON, CHANNELS, ERAS } from './labels'
import { signed } from './model'

export function EraPanel({
  data,
  blocked,
}: {
  data: ErasNodeView
  blocked: string | null
}) {
  const era = ERAS[data.era]
  const start = ERAS[data.starting_era]
  const known = data.techniques.filter((row) => row.held).length
  const running = useEraAction(
    'eras:run',
    (_: void) => ({}),
    'Every era and programme is read'
  )
  const BarredIcon = BARRED_ICON
  return (
    <div data-surface='EraPanel' className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
        <KpiTile
          label='Era reached'
          value={era.label}
          icon={era.icon}
          tone={era.tone}
          hint={era.hint}
        />
        <KpiTile
          label='Era the world began in'
          value={start.label}
          icon={start.icon}
          tone={start.tone}
          hint={start.hint}
        />
        <KpiTile
          label='Era techniques known'
          value={`${known} of ${data.techniques.length}`}
          icon={FlaskConical}
          tone='gold'
          meter={{
            value: known,
            max: Math.max(1, data.techniques.length),
            label: 'Era techniques known',
          }}
        />
      </div>
      <Facts
        items={[
          ['Seen from', <Ref key='node' node={data.node} empty='nothing' />],
          ['Realm', <Ref key='realm' node={data.realm} empty='no realm' />],
          [
            'Knowledge kept by',
            <Ref key='keeper' node={data.keeper} empty='no town or people' />,
          ],
        ]}
      />
      {data.no_gunpowder && (
        <div className='flex min-w-0 items-center gap-2'>
          <Badge size='sm' variant='warning'>
            <BarredIcon aria-hidden='true' />
            Powder does not burn here
          </Badge>
          <Muted variant='caption'>
            A law of nature on this world keeps gunpowder, firearms and cannon
            from working, whatever is known.
          </Muted>
        </div>
      )}
      <Bars
        chart='chart-tech-eras'
        title='What the known techniques change'
        legend={[
          { text: 'Gain', variant: 'success' },
          { text: 'Harm', variant: 'warning' },
        ]}
        rows={data.channels.map((row) => {
          const channel = CHANNELS[row.channel]
          const harmful = [
            'pollution',
            'doom',
            'rites',
            'secularisation',
          ].includes(row.channel)
          return {
            key: row.channel,
            caption: `${channel.label}: ${signed(row.value, channel.unit)}`,
            segments: [
              {
                value: row.value,
                fill: harmful ? 'fill-warning' : 'fill-success',
              },
            ],
          }
        })}
        noun={['effect', 'effects']}
        empty='No era technique is known here yet, so nothing is changed.'
      />
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <StepButton
          act={running}
          icon={Gauge}
          label='Read every era now'
          busy={why(blocked, running.isPending)}
          onClick={() => running.mutate()}
        />
      </div>
    </div>
  )
}
