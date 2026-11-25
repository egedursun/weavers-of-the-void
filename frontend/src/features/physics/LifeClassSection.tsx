import { Leaf, Users } from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { lifeEnvironmentValues as environmentValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList } from '@/components/domain'
import { Label } from '@/components/typography'
import {
  Chip,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { BIOCHEMISTRY } from '@/features/entity/wilds/labels'
import { physicsKeys, usePhysicsAction, useWorldPhysics } from './api'
import { COMPLEXITY, ENVIRONMENTS, table } from './labels'
import { QuerySection } from './parts'

type Edit = {
  values?: NonNullable<ActionBody<'life_class:edit'>['values']>
  release?: string[]
}

export function LifeClassSection({ worldId }: { worldId: number }) {
  const query = useWorldPhysics(worldId)
  const edit = usePhysicsAction(
    'life_class:edit',
    (vars: Edit) => ({
      world_id: worldId,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The life of the world is reshaped',
    [physicsKeys.world(worldId)]
  )
  const busy = edit.isPending ? 'Working' : null
  return (
    <QuerySection
      id='section-life-class'
      title='Its life'
      description='How complex its life has grown, where it lives and on what chemistry; creatures arise only on complex worlds and peoples only on sapient ones.'
      icon={Leaf}
      tone='success'
      query={query}
    >
      {(view) => {
        const life = view.life
        if (life === null)
          return (
            <EmptyState
              icon={Leaf}
              size='inline'
              title='Its life is not yet known'
              description='The heavens read it at the next epoch.'
            />
          )
        const places = new Set<string>(life.environments)
        return (
          <div className='flex min-w-0 flex-col gap-3'>
            <div className='flex min-w-0 flex-wrap gap-1'>
              <Chip icon={COMPLEXITY[life.complexity].icon}>
                {COMPLEXITY[life.complexity].label}
              </Chip>
              {life.biochemistries.map((key) => (
                <Chip key={key} icon={BIOCHEMISTRY[key]?.icon}>
                  {BIOCHEMISTRY[key]?.label ?? key}
                </Chip>
              ))}
            </div>
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label>Where it lives</Label>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                {environmentValues.map((key) => {
                  const spec = ENVIRONMENTS[key]
                  return (
                    <Button
                      act={edit}
                      key={key}
                      size='sm'
                      variant={places.has(key) ? 'default' : 'outline'}
                      aria-pressed={places.has(key)}
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        edit.mutate({
                          values: {
                            environments: places.has(key)
                              ? life.environments.filter((item) => item !== key)
                              : [...life.environments, key],
                          },
                        })
                      }
                    >
                      <spec.icon />
                      {spec.label}
                    </Button>
                  )
                })}
              </div>
            </div>
            <RecordEditor
              act={edit}
              title='Complexity'
              note='Life grows one step more complex now and then on a temperate, healthy world; set it here to hasten or undo that.'
              fields={[
                {
                  key: 'complexity',
                  label: 'Complexity',
                  kind: 'pick',
                  table: table(COMPLEXITY),
                },
              ]}
              locked={life.locked}
              busy={busy}
              onSave={(values) => edit.mutate({ values })}
              onRelease={(release) => edit.mutate({ release })}
            />
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label>How well its peoples can live here</Label>
              {view.fits.length === 0 ? (
                <EmptyState
                  icon={Users}
                  size='inline'
                  title='No people lives here'
                  description='Peoples who come here will fare by its air, gravity and chemistry.'
                />
              ) : (
                <PagedList
                  items={view.fits}
                  initial={6}
                  noun={['people', 'peoples']}
                  className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
                  itemKey={(row) => String(row.people.id)}
                >
                  {(row) => (
                    <RecordRow
                      icon={Users}
                      tone={
                        row.fit >= 75
                          ? 'success'
                          : row.fit >= 40
                            ? 'warning'
                            : 'danger'
                      }
                      title={
                        <EntityLink kind='entity' id={String(row.people.id)}>
                          {row.people.name}
                        </EntityLink>
                      }
                    >
                      <Meter
                        label='Habitability'
                        value={row.fit}
                        tone={
                          row.fit >= 75
                            ? 'success'
                            : row.fit >= 40
                              ? 'warning'
                              : 'destructive'
                        }
                      />
                    </RecordRow>
                  )}
                </PagedList>
              )}
            </div>
          </div>
        )
      }}
    </QuerySection>
  )
}
