import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Dna,
  Gem,
  Lock,
  RefreshCw,
  Shield,
  Swords,
  TriangleAlert,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  aversionValues,
  awakeningTriggerValues,
  habitatValues,
  materialKindValues,
  temperamentValues,
  tissueMaterialValues,
} from '@/api/generated/schema'
import { type ActProp } from '@/api/mutation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  MiniStat,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { PERCENT, busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import {
  AVERSION,
  AWAKENING,
  BITE,
  HABITAT,
  TEMPERAMENT_KIND,
  TISSUE,
} from './anatomyLabels'
import { anatomyKeys, useWildAction } from './api'
import { MATERIAL, type Named, named, titled } from './labels'
import { Card, Group, NumberField, Tile, TileGrid } from './parts'

const NONE = 'none'
const BITES = Object.keys(BITE)

function tableOf(
  values: readonly string[],
  table: Record<string, Named>,
  empty?: string
): Record<string, string> {
  return {
    ...(empty ? { [NONE]: empty } : {}),
    ...Object.fromEntries(values.map((key) => [key, named(table, key).label])),
  }
}

function useAnatomy(nodeId: number) {
  return useQuery({
    queryKey: anatomyKeys.node(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/anatomy', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

function Counter({
  label,
  value,
  min,
  blocked,
  onSave,
  act,
}: {
  label: string
  value: number
  min: number
  blocked: string | null
  onSave: (next: number) => void
  act?: ActProp
}) {
  const [draft, setDraft] = useState(String(value))
  const parsed = Number(draft)
  const problem = !Number.isInteger(parsed)
    ? 'Write a whole number'
    : parsed < min
      ? `It cannot be less than ${min}`
      : parsed === value
        ? 'This is the present value'
        : null
  return (
    <div className='flex min-w-0 items-end gap-2'>
      <div className='min-w-0 flex-1'>
        <NumberField
          label={label}
          value={draft}
          min={min}
          disabled={blocked !== null}
          onChange={setDraft}
        />
      </div>
      <Button
        act={act}
        size='sm'
        variant='outline'
        disabled={(blocked ?? problem) !== null}
        disabledReason={blocked ?? problem ?? undefined}
        onClick={() => onSave(parsed)}
      >
        Set
      </Button>
    </div>
  )
}

export function AnatomyCard({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const view = useAnatomy(nodeId)
  const edit = useWildAction(
    'anatomy:edit',
    (vars: { values: EditValues; release?: string[] }) => ({
      node_id: nodeId,
      values: vars.values,
      release: vars.release ?? [],
    })
  )
  const reroll = useWildAction('anatomy:reroll', (_: void) => ({
    node_id: nodeId,
  }))
  const busy = busyOf(blocked, edit.isPending || reroll.isPending)
  const row = view.data
  const set = (key: string, value: string | number | null) =>
    edit.mutate({ values: { [key]: value === NONE ? null : value } })
  return (
    <Card
      title='Body and nature'
      icon={Dna}
      tone='verdigris'
      hint='Its generated body, attacks, temper and what draws or repels it'
      wide
    >
      {view.isPending && <LoadingBlock label='Reading its body' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its body could not be read'
          description={view.error.message}
        />
      )}
      {view.data === null && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Muted variant='caption'>
            The world shapes its body in the next epoch, or you can shape it
            now.
          </Muted>
          <Button
            act={reroll}
            size='sm'
            variant='outline'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => reroll.mutate(undefined)}
          >
            <RefreshCw />
            Shape its body
          </Button>
        </div>
      )}
      {row && (
        <div
          data-surface='CreatureAnatomy'
          className='flex min-w-0 flex-col gap-3'
        >
          <div className='grid min-w-0 grid-cols-2 gap-2 @md/wild:grid-cols-4'>
            <MiniStat icon={Dna} label='Limbs' value={row.limbs} tone='info' />
            <MiniStat icon={Dna} label='Heads' value={row.heads} tone='gold' />
            <MiniStat
              icon={Dna}
              label='Wings'
              value={row.wings}
              tone='verdigris'
            />
            <MiniStat icon={Dna} label='Tails' value={row.tails} tone='muted' />
          </div>
          <Muted variant='caption'>{`Its body took this shape in epoch ${row.generated_epoch}.`}</Muted>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <KpiTile
              label='Armour from its body'
              value={`${row.armour_pct}%`}
              icon={Shield}
              tone='info'
              meter={{
                value: row.armour_pct,
                max: PERCENT,
                label: 'Armour from its body',
              }}
              hint='How much of each wound its skin turns aside; its skin and bones are the outer and inner layers a blade must pass'
            />
            <KpiTile
              label='Harm it adds to its raids'
              value={`+${row.harm_pct}%`}
              icon={Swords}
              tone='danger'
              hint='From its attacks, its heads, its limbs and the tissue it is made of; it also counts against heroes'
            />
          </div>
          <TileGrid>
            <Tile spec={named(TISSUE, row.skin)} caption='Skin' />
            <Tile spec={named(TISSUE, row.bone)} caption='Bones' />
            <Tile spec={named(HABITAT, row.habitat)} caption='Lives in' />
            <Tile
              spec={named(TEMPERAMENT_KIND, row.temperament)}
              caption={TEMPERAMENT_KIND[row.temperament]?.hint ?? 'Temperament'}
            />
            {row.bite && <Tile spec={named(BITE, row.bite)} caption='Bite' />}
            {row.hoards && (
              <Tile
                spec={{
                  label: MATERIAL[row.hoards] ?? titled(row.hoards),
                  icon: Gem,
                  tone: 'gold',
                }}
                caption='Hoards'
              />
            )}
            {row.hates && (
              <Tile spec={named(AVERSION, row.hates)} caption='Shuns' />
            )}
            {row.awakening && (
              <Tile
                spec={named(AWAKENING, row.awakening)}
                caption={AWAKENING[row.awakening]?.hint ?? 'Wakes to'}
              />
            )}
          </TileGrid>
          {row.locked.length > 0 && (
            <Badge size='sm' variant='outline' className='self-start'>
              <Lock aria-hidden='true' />
              {`Held: ${row.locked.join(', ').replaceAll('_', ' ')}`}
            </Badge>
          )}
          <Group title='Shape its body' icon={Dna} wide>
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/wild:grid-cols-2 @3xl/wild:grid-cols-4'>
              {(['limbs', 'heads', 'wings', 'tails'] as const).map((key) => (
                <Counter
                  act={edit}
                  key={`${key}-${row[key]}`}
                  label={key[0].toUpperCase() + key.slice(1)}
                  value={row[key]}
                  min={key === 'heads' ? 1 : 0}
                  blocked={busy}
                  onSave={(next) => set(key, next)}
                />
              ))}
            </div>
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/wild:grid-cols-2 @3xl/wild:grid-cols-3'>
              <MindPicker
                act={edit}
                label='Skin'
                value={row.skin}
                table={tableOf(tissueMaterialValues, TISSUE)}
                blocked={busy}
                onPick={(value) => set('skin', value)}
              />
              <MindPicker
                act={edit}
                label='Bones'
                value={row.bone}
                table={tableOf(tissueMaterialValues, TISSUE)}
                blocked={busy}
                onPick={(value) => set('bone', value)}
              />
              <MindPicker
                act={edit}
                label='Lives in'
                value={row.habitat}
                table={tableOf(habitatValues, HABITAT)}
                blocked={busy}
                onPick={(value) => set('habitat', value)}
              />
              <MindPicker
                act={edit}
                label='Temperament'
                value={row.temperament}
                table={tableOf(temperamentValues, TEMPERAMENT_KIND)}
                blocked={busy}
                onPick={(value) => set('temperament', value)}
              />
              <MindPicker
                act={edit}
                label='Bite'
                value={row.bite ?? NONE}
                table={tableOf(BITES, BITE, 'An ordinary bite')}
                blocked={busy}
                onPick={(value) => set('bite', value)}
              />
              <MindPicker
                act={edit}
                label='Hoards'
                value={row.hoards ?? NONE}
                table={{
                  [NONE]: 'Nothing above all else',
                  ...Object.fromEntries(
                    materialKindValues.map((key) => [
                      key,
                      MATERIAL[key] ?? titled(key),
                    ])
                  ),
                }}
                blocked={busy}
                onPick={(value) => set('hoards', value)}
              />
              <MindPicker
                act={edit}
                label='Shuns'
                value={row.hates ?? NONE}
                table={tableOf(aversionValues, AVERSION, 'Nothing')}
                blocked={busy}
                onPick={(value) => set('hates', value)}
              />
              <MindPicker
                act={edit}
                label='Wakes to'
                value={row.awakening ?? NONE}
                table={tableOf(
                  awakeningTriggerValues,
                  AWAKENING,
                  'Its own time'
                )}
                blocked={busy}
                onPick={(value) => set('awakening', value)}
              />
            </div>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                act={reroll}
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => reroll.mutate(undefined)}
              >
                <RefreshCw />
                Let the world shape it anew
              </Button>
              {row.locked.length > 0 && (
                <Button
                  act={edit}
                  size='sm'
                  variant='ghost'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() =>
                    edit.mutate({ values: {}, release: [...row.locked] })
                  }
                >
                  <Lock />
                  Release what you hold
                </Button>
              )}
            </div>
          </Group>
        </div>
      )}
    </Card>
  )
}
