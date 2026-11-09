import { useState } from 'react'
import { ShieldCheck, Trash2, Zap } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList } from '@/components/domain'
import {
  Chip,
  ForgeCard,
  RecordEditor,
  RecordPick,
  RecordRow,
} from '@/features/cosmography/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { type ImpactRecord, physicsKeys, usePhysicsAction } from './api'
import { IMPACT_BODIES, IMPACT_OUTCOMES } from './labels'
import { WorldPicker } from './parts'

type Edit = {
  impact: number
  values?: Record<string, number | string | null>
  release?: string[]
}
type Call = { world: number; region: number | null; size: number | null }

export function ImpactsPanel({
  worldId,
  impacts,
  epoch,
}: {
  worldId: number | null
  impacts: readonly ImpactRecord[]
  epoch: number
}) {
  const [world, setWorld] = useState('')
  const [region, setRegion] = useState<number | null>(null)
  const [size, setSize] = useState('')
  const target = worldId ?? (world === '' ? null : Number(world))
  const refresh = target !== null ? [physicsKeys.world(target)] : []
  const call = usePhysicsAction(
    'impact:call',
    (vars: Call) => ({
      world_id: vars.world,
      region_id: vars.region,
      size: vars.size,
    }),
    'A body falls toward the world',
    refresh
  )
  const deflect = usePhysicsAction(
    'impact:deflect',
    (impact: number) => ({ impact_id: impact }),
    'The body is turned aside',
    refresh
  )
  const edit = usePhysicsAction(
    'impact:edit',
    (vars: Edit) => ({
      impact_id: vars.impact,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The impact is reshaped',
    refresh
  )
  const remove = usePhysicsAction(
    'impact:delete',
    (impact: number) => ({ impact_id: impact }),
    'The impact is struck from the record',
    refresh
  )
  const busy =
    call.isPending || deflect.isPending || edit.isPending || remove.isPending
      ? 'Working'
      : null
  const coming = impacts.filter((row) => row.outcome === 'pending').length
  return (
    <section id='section-impacts' className='flex min-w-0 flex-col gap-3'>
      {impacts.length === 0 ? (
        <EmptyState
          icon={Zap}
          size='inline'
          title='No body has fallen'
          description='Fields, comets and rogue worlds send them now and then; you can call one down below.'
        />
      ) : (
        <PagedList
          items={[...impacts]}
          initial={6}
          noun={['impact', 'impacts']}
          className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
          itemKey={(row) => String(row.id)}
        >
          {(row) => (
            <RecordRow
              icon={IMPACT_BODIES[row.body].icon}
              tone={IMPACT_OUTCOMES[row.outcome].tone}
              title={`${IMPACT_BODIES[row.body].label} · size ${row.size}`}
              caption={
                <>
                  {row.world && (
                    <EntityLink kind='world' id={String(row.world.id)}>
                      {row.world.name}
                    </EntityLink>
                  )}
                  {row.region && ` · ${row.region.name}`}
                  {row.outcome === 'pending'
                    ? ` · strikes in ${Math.max(0, row.due_epoch - epoch)} epochs${row.warned_epoch !== null ? ', foreseen' : ''}`
                    : ` · ${IMPACT_OUTCOMES[row.outcome].label.toLowerCase()} at epoch ${row.due_epoch}`}
                </>
              }
              aside={
                <div className='flex shrink-0 flex-wrap gap-1'>
                  {row.outcome === 'pending' && (
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() => deflect.mutate(row.id)}
                    >
                      <ShieldCheck />
                      Turn aside
                    </Button>
                  )}
                  <Button
                    size='sm'
                    variant='ghost'
                    aria-label='Strike it from the record'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => remove.mutate(row.id)}
                  >
                    <Trash2 />
                  </Button>
                </div>
              }
            >
              <div className='flex min-w-0 flex-wrap gap-1'>
                <Chip icon={IMPACT_OUTCOMES[row.outcome].icon}>
                  {IMPACT_OUTCOMES[row.outcome].label}
                </Chip>
                {row.crater && (
                  <Chip>
                    <EntityLink kind='entity' id={String(row.crater.id)}>
                      {row.crater.name}
                    </EntityLink>
                  </Chip>
                )}
                {row.winter_epochs > 0 && (
                  <Chip>{`Impact winter: ${row.winter_epochs} epochs`}</Chip>
                )}
              </div>
              <RecordEditor
                title='Size, time and winter'
                note='A held value is kept against the engine.'
                fields={[
                  {
                    key: 'size',
                    label: 'Size',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'due_epoch',
                    label: 'Strikes at epoch',
                    kind: 'number',
                    min: 1,
                  },
                  {
                    key: 'winter_epochs',
                    label: 'Winter epochs',
                    kind: 'number',
                    min: 0,
                  },
                ]}
                locked={row.locked}
                busy={busy}
                onSave={(values) => edit.mutate({ impact: row.id, values })}
                onRelease={(release) =>
                  edit.mutate({ impact: row.id, release })
                }
              />
            </RecordRow>
          )}
        </PagedList>
      )}
      <ForgeCard
        icon={Zap}
        tone='danger'
        title='Call a body down'
        note='It strikes next epoch unless turned aside: it ruins the region, leaves a crater and can bring a winter over the world.'
        columns={worldId === null ? 3 : 2}
        meta={
          <Chip icon={Zap}>{`${plural(coming, 'body', 'bodies')} coming`}</Chip>
        }
        action={
          <Button
            size='sm'
            variant='destructive'
            disabled={busy !== null || target === null}
            disabledReason={
              busy ?? (target === null ? 'Choose a world first' : undefined)
            }
            onClick={() =>
              target !== null &&
              call.mutate({
                world: target,
                region,
                size: size === '' ? null : Number(size),
              })
            }
          >
            <Zap />
            Call it down
          </Button>
        }
      >
        {worldId === null && (
          <WorldPicker value={world} onPick={setWorld} busy={busy} />
        )}
        <RecordPick
          label='Region'
          types={['region']}
          value={region}
          onChange={setRegion}
          worldId={target ?? undefined}
        />
        <NumberField
          label='Size'
          value={size}
          min={1}
          max={100}
          disabled={busy !== null}
          onChange={setSize}
        />
      </ForgeCard>
    </section>
  )
}
