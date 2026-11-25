import { useState } from 'react'
import {
  Flame,
  Hourglass,
  MapPinned,
  Shield,
  Swords,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Held } from '@/features/collective/parts'
import { Chip, ForgeCard, Meter, RecordRow } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type CyclesView, useCycleAction } from './api'
import { clamp, SPAN, useRow } from './model'
import { NodeChips } from './parts'

type Solidarity = NonNullable<CyclesView['solidarity']>
type Frontier = components['schemas']['FrontierView']

const SOLIDARY = 'Only a people or a realm holds together this way'
const FORGED = 66
const SOFT = 33

function tone(value: number) {
  return value >= FORGED ? 'success' : value < SOFT ? 'destructive' : 'warning'
}

function SolidarityCard({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: Solidarity
  blocked: string | null
}) {
  const action = useRow(
    'asabiyya:edit',
    'asabiyya:delete',
    { holder_id: holderId },
    blocked
  )
  return (
    <Held
      icon={row.value >= FORGED ? TrendingUp : TrendingDown}
      tone={
        row.value >= FORGED
          ? 'success'
          : row.value < SOFT
            ? 'danger'
            : 'warning'
      }
      title={`Solidarity ${row.value}`}
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Let it grow anew'
      editTitle='Set the solidarity'
      note='Frontiers with peoples of far other values and a shared struggle forge solidarity; generations of ease and the intrigue of elites wear it away. It lifts cohesion, levies, morale and the will to resist assimilation.'
      fields={[
        {
          key: 'value',
          label: 'Solidarity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'frontier', label: 'Frontier lands', kind: 'number', min: 0 },
        {
          key: 'luxury_generations',
          label: 'Generations of ease',
          kind: 'number',
          min: 0,
        },
        {
          key: 'conflict',
          label: 'Shared struggle',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Solidarity'
        value={row.value}
        max={SPAN}
        tone={tone(row.value)}
        icon={Shield}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-3'>
          <KpiTile
            label='Frontier lands'
            value={row.frontier}
            icon={MapPinned}
            tone='verdigris'
          />
          <KpiTile
            label='Generations of ease'
            value={row.luxury_generations}
            icon={Hourglass}
            tone='muted'
          />
          <KpiTile
            label='Shared struggle'
            value={row.conflict}
            icon={Swords}
            tone='danger'
          />
        </div>
      </div>
    </Held>
  )
}

function SolidarityForge({
  holderId,
  isSolidary,
  blocked,
}: {
  holderId: number
  isSolidary: boolean
  blocked: string | null
}) {
  const [value, setValue] = useState('60')
  const [conflict, setConflict] = useState('0')
  const setting = useCycleAction(
    'asabiyya:set',
    (_: void) => ({
      holder_id: holderId,
      value: clamp(value),
      conflict: clamp(conflict),
    }),
    'Their solidarity is set'
  )
  const busy = why(isSolidary ? blocked : SOLIDARY, setting.isPending)
  return (
    <ForgeCard
      icon={Shield}
      tone='success'
      title='Set their solidarity'
      note='Forge them into one, or let them go soft.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Flame />
          Set it
        </Button>
      }
    >
      <NumberField
        label='Solidarity'
        value={value}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setValue}
      />
      <NumberField
        label='Shared struggle'
        value={conflict}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setConflict}
      />
    </ForgeCard>
  )
}

export function SolidarityPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: CyclesView
  blocked: string | null
}) {
  const isSolidary = kind === 'people' || kind === 'polity'
  return (
    <div data-surface='SolidarityPanel' className='flex min-w-0 flex-col gap-4'>
      {data.solidarity ? (
        <SolidarityCard
          holderId={nodeId}
          row={data.solidarity}
          blocked={blocked}
        />
      ) : (
        <Muted variant='caption'>
          {isSolidary
            ? 'Their solidarity is read at the next epoch.'
            : SOLIDARY}
        </Muted>
      )}
      <SolidarityForge
        holderId={nodeId}
        isSolidary={isSolidary}
        blocked={blocked}
      />
    </div>
  )
}

export function FrontierMap({ frontiers }: { frontiers: Frontier[] }) {
  return (
    <div
      data-surface='FrontierMap'
      id='cycles-frontier-map'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label variant='overline'>{`Solidarity and frontiers (${frontiers.length})`}</Label>
      {frontiers.length === 0 ? (
        <Muted variant='caption'>
          No people or realm has been read yet; open the map's solidarity layer
          after the next epoch.
        </Muted>
      ) : (
        <PagedList
          items={frontiers}
          initial={6}
          noun={['holder', 'holders']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(item) => item.holder.id}
        >
          {(item) => (
            <RecordRow
              icon={item.value >= FORGED ? TrendingUp : TrendingDown}
              tone={
                item.value >= FORGED
                  ? 'success'
                  : item.value < SOFT
                    ? 'danger'
                    : 'warning'
              }
              title={<Ref node={item.holder} />}
              caption={`${item.frontier} frontier lands · struggle ${item.conflict}`}
            >
              <Meter
                label='Solidarity'
                value={item.value}
                max={SPAN}
                tone={tone(item.value)}
                icon={Shield}
              />
              <NodeChips
                nodes={item.regions}
                empty='No lands of its own'
                icon={MapPinned}
              />
              {item.frontier > 0 && (
                <Chip icon={Swords}>On a meta-ethnic frontier</Chip>
              )}
            </RecordRow>
          )}
        </PagedList>
      )}
    </div>
  )
}
