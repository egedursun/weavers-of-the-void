import { useState } from 'react'
import {
  Castle,
  Flag,
  Hourglass,
  Network,
  Route,
  Ship,
  Swords,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, EpochSlider, LoadingBlock } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useWorldState } from '@/features/entity/api/queries'
import { type Named } from '@/features/entity/environment/labels'
import { ChoiceField } from '@/features/wars/military/parts'
import { ThenAndNow } from './TimelineScrubber'
import { useStateAt } from './api'

const PAGE = 40
const LAYERS: Record<string, Named> = {
  polity_territories: { label: 'Borders of realms', icon: Flag },
  settlement_profiles: { label: 'Settlements', icon: Castle },
  routes: { label: 'Routes', icon: Route },
  trade_route_profiles: { label: 'Trade routes', icon: Route },
  armies: { label: 'Armies', icon: Swords },
  army_profiles: { label: 'Armies in the field', icon: Swords },
  vehicle_groups: { label: 'Fleets and convoys', icon: Ship },
  network_nodes: { label: 'Networks', icon: Network },
}

export function AtlasAtMoment() {
  const state = useWorldState()
  const present = state.data?.world?.epoch ?? 1
  const [epoch, setEpoch] = useState<number | null>(null)
  const [layer, setLayer] = useState('polity_territories')
  const [limit, setLimit] = useState(PAGE)
  const chosen = epoch ?? Math.max(1, present - 1)
  const then = useStateAt(
    present > 1 ? { epoch: chosen, nodeId: null, table: layer, limit } : null
  )
  return (
    <div
      data-surface='AtlasAtMoment'
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Hourglass aria-hidden='true' className='size-icon-sm text-primary' />
        <Muted>
          The atlas at an earlier moment: what each layer held then, beside what
          it holds now.
        </Muted>
      </div>
      <ChoiceField
        label='Layer of the atlas'
        value={layer}
        table={LAYERS}
        blocked={
          present > 1 ? null : 'The world has lived only its first epoch'
        }
        onPick={(value) => {
          setLayer(value)
          setLimit(PAGE)
        }}
      />
      <EpochSlider
        label='At the start of'
        value={chosen}
        max={present}
        disabled={present <= 1}
        valueLabel={chosen === present ? 'Now' : `Epoch ${chosen}`}
        onChange={setEpoch}
      />
      {present <= 1 ? (
        <Muted variant='caption'>
          There is no earlier moment to look back to yet.
        </Muted>
      ) : then.isPending ? (
        <LoadingBlock label='Reading the atlas as it was' />
      ) : then.isError ? (
        <EmptyState
          icon={Hourglass}
          size='inline'
          title='The atlas could not be read as it was'
          description={then.error.message}
        />
      ) : (
        <>
          <Muted variant='caption'>
            {`${then.data.total} ${then.data.total === 1 ? 'record' : 'records'} in this layer`}
          </Muted>
          <ThenAndNow
            rows={then.data.rows}
            empty={
              chosen === present
                ? 'This is the atlas as it is now.'
                : `This layer held what it holds now at the start of epoch ${chosen}.`
            }
          />
          {then.data.total > limit && (
            <Button
              variant='outline'
              size='sm'
              onClick={() => setLimit((current) => current + PAGE)}
            >
              <Hourglass aria-hidden='true' />
              Read more of this layer
            </Button>
          )}
        </>
      )}
    </div>
  )
}
