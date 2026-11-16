import { useState } from 'react'
import { Coins, Gem } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { FIELD_GRID, NumberField } from './EntityEconomy'
import { ECONOMY_REFRESH, useWorldMaterials } from './api'
import { LUXURY_METALS, type MaterialKind } from './labels'
import { materialRef, useBusy, whole } from './model'
import { MaterialSelect } from './parts'

const DEFAULT_UNITS = '40'

export function HoardControl({
  communityId,
  worldId,
  readOnlyReason,
}: {
  communityId: number
  worldId: number | null
  readOnlyReason?: string | null
}) {
  const materials = useWorldMaterials(worldId)
  const [metal, setMetal] = useState<string>('kind:gold')
  const [units, setUnits] = useState(DEFAULT_UNITS)
  const pour = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () => {
      const ref = materialRef(metal)
      const substance = (materials.data?.materials ?? []).find(
        (row) =>
          ref.world_material_id !== null &&
          row.world_material_id === ref.world_material_id
      )
      const kind: MaterialKind =
        ref.material ?? substance?.base_kind ?? LUXURY_METALS[0]
      return unwrap(
        api.POST('/api/actions/hoard:inject', {
          body: {
            community_id: communityId,
            metal: kind,
            world_material_id: ref.world_material_id,
            units: whole(units, undefined, 1),
          },
        })
      )
    },
  })
  const busy = useBusy(readOnlyReason, pour.isPending)
  return (
    <div
      data-surface='HoardControl'
      className='@container/hoard flex min-w-0 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Gem} tone='gold' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text weight='semibold'>Pour a hoard into the market</Text>
          <Muted variant='caption'>
            Floods the luxury price index; the market’s coin loses trust if it
            is struck from the same metal.
          </Muted>
        </div>
      </div>
      <div className={cn(FIELD_GRID, '@md/hoard:grid-cols-3')}>
        <MaterialSelect
          label='Hoard of'
          worldId={worldId}
          value={metal}
          blocked={busy}
          only={LUXURY_METALS}
          onPick={setMetal}
        />
        <NumberField
          label='Units'
          aria='Hoard units'
          value={units}
          min={1}
          onChange={setUnits}
        />
        <Button
          size='sm'
          className='justify-self-start'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => pour.mutate(undefined)}
        >
          <Coins />
          Pour the hoard
        </Button>
      </div>
    </div>
  )
}
