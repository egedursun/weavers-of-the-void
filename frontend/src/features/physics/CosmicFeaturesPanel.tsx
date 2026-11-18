import { useState } from 'react'
import { Gem, Plus, Trash2 } from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  PagedList,
  FieldTile,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { useCosmography } from '@/features/cosmography/api'
import {
  Chip,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { type FeatureRecord, usePhysicsAction } from './api'
import { FEATURE_KINDS, table } from './labels'
import { WorldPicker } from './parts'

type Edit = {
  feature: number
  values?: EditValues
  release?: string[]
}
type Draft = {
  kind: string
  name: string
  star: string
  galaxy: string
  world: string
  worldB: string
}

const STAR_FEATURES = new Set([
  'asteroid_field',
  'periodic_comet',
  'gravity_well',
  'wandering_star',
])

function needs(draft: Draft): string | null {
  if (draft.kind === '') return 'Choose a kind first'
  if (draft.kind === 'wormhole')
    return draft.world === '' || draft.worldB === ''
      ? 'Choose the two worlds it joins'
      : draft.world === draft.worldB
        ? 'A wormhole joins two different worlds'
        : null
  if (STAR_FEATURES.has(draft.kind) && draft.star === '')
    return 'Choose its star first'
  if (draft.kind === 'rogue_world' && draft.star === '' && draft.galaxy === '')
    return 'Choose the star or the galaxy it drifts through'
  return null
}

export function CosmicFeaturesPanel({
  features,
  starId = null,
}: {
  features: readonly FeatureRecord[]
  starId?: number | null
}) {
  const heavens = useCosmography()
  const blank: Draft = {
    kind: '',
    name: '',
    star: starId === null ? '' : String(starId),
    galaxy: '',
    world: '',
    worldB: '',
  }
  const [draft, setDraft] = useState<Draft>(blank)
  const create = usePhysicsAction(
    'cosmic_feature:create',
    (vars: Draft) => ({
      kind: vars.kind as ActionBody<'cosmic_feature:create'>['kind'],
      name: vars.name,
      star_id: vars.star === '' ? null : Number(vars.star),
      galaxy_id: vars.galaxy === '' ? null : Number(vars.galaxy),
      world_id: vars.world === '' ? null : Number(vars.world),
      world_b_id: vars.worldB === '' ? null : Number(vars.worldB),
    }),
    'The feature takes its place'
  )
  const edit = usePhysicsAction(
    'cosmic_feature:edit',
    (vars: Edit) => ({
      feature_id: vars.feature,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The feature is reshaped'
  )
  const remove = usePhysicsAction(
    'cosmic_feature:delete',
    (feature: number) => ({ feature_id: feature }),
    'The feature is unmade'
  )
  const busy =
    create.isPending || edit.isPending || remove.isPending ? 'Working' : null
  const missing = needs(draft)
  const stars = Object.fromEntries(
    (heavens.data?.stars ?? []).map((row) => [String(row.id), row.name])
  )
  const galaxies = Object.fromEntries(
    (heavens.data?.galaxies ?? []).map((row) => [String(row.id), row.name])
  )
  return (
    <section
      id='section-cosmic-features'
      className='flex min-w-0 flex-col gap-3'
    >
      {features.length === 0 ? (
        <EmptyState
          icon={Gem}
          size='inline'
          title='No field, wormhole, comet or rogue world here'
          description='Set one in the heavens below.'
        />
      ) : (
        <PagedList
          items={[...features]}
          initial={6}
          noun={['feature', 'features']}
          className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
          itemKey={(row) => String(row.id)}
        >
          {(row) => (
            <RecordRow
              icon={FEATURE_KINDS[row.kind].icon}
              tone={FEATURE_KINDS[row.kind].tone}
              title={row.name}
              caption={
                <>
                  {FEATURE_KINDS[row.kind].label}
                  {row.star && (
                    <>
                      {' · '}
                      <EntityLink kind='star' id={String(row.star.id)}>
                        {row.star.name}
                      </EntityLink>
                    </>
                  )}
                  {row.world && ` · ${row.world.name}`}
                  {row.world_b && ` to ${row.world_b.name}`}
                  {row.next_return_epoch !== null &&
                    ` · returns at epoch ${row.next_return_epoch}`}
                  {row.ended_epoch !== null &&
                    ` · gone since epoch ${row.ended_epoch}`}
                </>
              }
              aside={
                <Button
                  size='sm'
                  variant='ghost'
                  aria-label='Unmake it'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => remove.mutate(row.id)}
                >
                  <Trash2 />
                </Button>
              }
            >
              <div className='grid min-w-0 grid-cols-1 gap-1.5 sm:grid-cols-2'>
                {row.kind === 'asteroid_field' && (
                  <Meter
                    label='Ore it holds'
                    value={row.richness}
                    tone='warning'
                  />
                )}
                {row.kind === 'asteroid_field' && (
                  <Meter
                    label='Pirates it hides'
                    value={row.pirates}
                    tone='destructive'
                  />
                )}
                {row.kind === 'wormhole' && (
                  <Meter
                    label='Instability'
                    value={row.instability}
                    tone='destructive'
                  />
                )}
                <Meter label='Density' value={row.density} tone='muted' />
              </div>
              {row.description && (
                <Muted variant='caption'>{row.description}</Muted>
              )}
              <RecordEditor
                title='Its nature'
                note={FEATURE_KINDS[row.kind].hint}
                fields={[
                  { key: 'name', label: 'Name', kind: 'text' },
                  {
                    key: 'density',
                    label: 'Density',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'richness',
                    label: 'Ore',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'pirates',
                    label: 'Pirates',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'instability',
                    label: 'Instability',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'radius',
                    label: 'Reach (orbits)',
                    kind: 'decimal',
                    min: 0,
                  },
                  {
                    key: 'period_epochs',
                    label: 'Period (epochs)',
                    kind: 'number',
                    min: 0,
                  },
                  {
                    key: 'next_return_epoch',
                    label: 'Next return (epoch)',
                    kind: 'number',
                    min: 1,
                  },
                  {
                    key: 'radiation',
                    label: 'Radiation',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'travel',
                    label: 'Epochs it adds to routes past it',
                    kind: 'number',
                    min: -100,
                    max: 100,
                  },
                  {
                    key: 'omen_weight',
                    label: 'Weight as an omen',
                    kind: 'number',
                    min: 0,
                    max: 100,
                  },
                  {
                    key: 'x',
                    label: 'Place across its galaxy',
                    kind: 'decimal',
                  },
                  {
                    key: 'y',
                    label: 'Place along its galaxy',
                    kind: 'decimal',
                  },
                  { key: 'star_id', label: 'Star', kind: 'pick', table: stars },
                  {
                    key: 'galaxy_id',
                    label: 'Galaxy',
                    kind: 'pick',
                    table: galaxies,
                  },
                  {
                    key: 'ended_epoch',
                    label: 'Gone since epoch',
                    kind: 'number',
                    min: 1,
                  },
                  {
                    key: 'description',
                    label: 'What is told of it',
                    kind: 'text',
                    long: true,
                  },
                ]}
                locked={row.locked}
                busy={busy}
                onSave={(values) =>
                  edit.mutate({
                    feature: row.id,
                    values,
                  })
                }
                onRelease={(release) =>
                  edit.mutate({ feature: row.id, release })
                }
              />
            </RecordRow>
          )}
        </PagedList>
      )}
      <ForgeCard
        icon={Plus}
        tone='gold'
        title='Set a feature in the heavens'
        note={
          draft.kind === ''
            ? 'Asteroid fields, wormholes, comets, rogue worlds and the wells of black holes.'
            : FEATURE_KINDS[draft.kind as keyof typeof FEATURE_KINDS].hint
        }
        columns={
          draft.kind === 'wormhole' || draft.kind === 'rogue_world' ? 4 : 3
        }
        meta={
          <Chip icon={Gem}>{`${plural(features.length, 'feature')} here`}</Chip>
        }
        action={
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => {
              create.mutate(draft)
              setDraft(blank)
            }}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <MindPicker
          label='Kind'
          value={draft.kind}
          table={table(FEATURE_KINDS)}
          blocked={busy}
          onPick={(kind) => setDraft((previous) => ({ ...previous, kind }))}
        />
        <FieldTile id='feature-name' label='Name'>
          <Input
            id='feature-name'
            value={draft.name}
            disabled={busy !== null}
            onChange={(event) =>
              setDraft((previous) => ({
                ...previous,
                name: event.target.value,
              }))
            }
          />
        </FieldTile>
        {draft.kind === 'wormhole' ? (
          <>
            <WorldPicker
              label='First world'
              value={draft.world}
              busy={busy}
              onPick={(world) =>
                setDraft((previous) => ({ ...previous, world }))
              }
            />
            <WorldPicker
              label='Second world'
              value={draft.worldB}
              busy={busy}
              onPick={(worldB) =>
                setDraft((previous) => ({ ...previous, worldB }))
              }
            />
          </>
        ) : (
          starId === null && (
            <MindPicker
              label='Star'
              value={draft.star}
              table={stars}
              blocked={busy}
              onPick={(star) => setDraft((previous) => ({ ...previous, star }))}
            />
          )
        )}
        {draft.kind === 'rogue_world' && draft.star === '' && (
          <MindPicker
            label='Galaxy it drifts through'
            value={draft.galaxy}
            table={galaxies}
            blocked={busy}
            onPick={(galaxy) =>
              setDraft((previous) => ({ ...previous, galaxy }))
            }
          />
        )}
      </ForgeCard>
    </section>
  )
}
