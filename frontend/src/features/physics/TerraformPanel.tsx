import { useState } from 'react'
import { Hammer, Pickaxe, Square } from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList } from '@/components/domain'
import {
  Chip,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { type TerraformRecord, physicsKeys, usePhysicsAction } from './api'
import { TERRAFORM_AIMS, table } from './labels'
import { WorldPicker } from './parts'

type Edit = {
  project: number
  values?: EditValues
  release?: string[]
}
type Start = {
  world: number
  aim: string
  step: number | null
  epochs: number | null
}

export function TerraformPanel({
  worldId,
  projects,
}: {
  worldId: number | null
  projects: readonly TerraformRecord[]
}) {
  const [aim, setAim] = useState('')
  const [step, setStep] = useState('')
  const [epochs, setEpochs] = useState('')
  const [world, setWorld] = useState('')
  const target = worldId ?? (world === '' ? null : Number(world))
  const refresh = target !== null ? [physicsKeys.world(target)] : []
  const start = usePhysicsAction(
    'terraform:start',
    (vars: Start) => ({
      world_id: vars.world,
      aim: vars.aim as ActionBody<'terraform:start'>['aim'],
      step: vars.step,
      epochs: vars.epochs,
    }),
    'The world begins to change',
    refresh
  )
  const edit = usePhysicsAction(
    'terraform:edit',
    (vars: Edit) => ({
      project_id: vars.project,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The work is reshaped',
    refresh
  )
  const stop = usePhysicsAction(
    'terraform:stop',
    (project: number) => ({ project_id: project }),
    'The work is stopped',
    refresh
  )
  const busy =
    start.isPending || edit.isPending || stop.isPending ? 'Working' : null
  const missing =
    target === null
      ? 'Choose a world first'
      : aim === ''
        ? 'Choose what to change first'
        : null
  return (
    <section id='section-terraform' className='flex min-w-0 flex-col gap-3'>
      {projects.length === 0 ? (
        <EmptyState
          icon={Pickaxe}
          size='inline'
          title='No world is being reshaped'
          description='Begin a work below; it moves the world a little each epoch.'
        />
      ) : (
        <PagedList
          items={[...projects]}
          initial={6}
          noun={['work', 'works']}
          className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
          itemKey={(row) => String(row.id)}
        >
          {(row) => (
            <RecordRow
              icon={TERRAFORM_AIMS[row.aim].icon}
              tone={TERRAFORM_AIMS[row.aim].tone}
              title={TERRAFORM_AIMS[row.aim].label}
              caption={
                <>
                  {row.world && (
                    <EntityLink kind='world' id={String(row.world.id)}>
                      {row.world.name}
                    </EntityLink>
                  )}
                  {` · ${row.step} a step, ${plural(row.epochs_left, 'epoch', 'epochs')} left${row.by ? ` · by ${row.by.name}` : ''}`}
                </>
              }
              aside={
                <Button
                  size='sm'
                  variant='ghost'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => stop.mutate(row.id)}
                >
                  <Square />
                  Stop
                </Button>
              }
            >
              <RecordEditor
                title='Pace and length'
                note='How far the world moves each epoch and how long the work runs.'
                fields={[
                  {
                    key: 'step',
                    label: 'Step',
                    kind: 'number',
                    min: 1,
                    max: 100,
                  },
                  {
                    key: 'epochs_left',
                    label: 'Epochs left',
                    kind: 'number',
                    min: 0,
                  },
                  {
                    key: 'aim',
                    label: 'What it works toward',
                    kind: 'pick',
                    table: table(TERRAFORM_AIMS),
                  },
                ]}
                locked={row.locked}
                busy={busy}
                onSave={(values) => edit.mutate({ project: row.id, values })}
                onRelease={(release) =>
                  edit.mutate({ project: row.id, release })
                }
              />
            </RecordRow>
          )}
        </PagedList>
      )}
      <ForgeCard
        icon={Hammer}
        tone='verdigris'
        title='Reshape a world'
        note='Its air, warmth, water or face change a little each epoch; native life of another chemistry suffers.'
        columns={worldId === null ? 4 : 3}
        meta={
          <Chip
            icon={Pickaxe}
          >{`${plural(projects.length, 'work')} under way`}</Chip>
        }
        action={
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() =>
              target !== null &&
              start.mutate({
                world: target,
                aim,
                step: step === '' ? null : Number(step),
                epochs: epochs === '' ? null : Number(epochs),
              })
            }
          >
            <Hammer />
            Begin the work
          </Button>
        }
      >
        {worldId === null && (
          <WorldPicker value={world} onPick={setWorld} busy={busy} />
        )}
        <MindPicker
          label='What to change'
          value={aim}
          table={table(TERRAFORM_AIMS)}
          blocked={busy}
          onPick={setAim}
        />
        <NumberField
          label='Step'
          value={step}
          min={1}
          max={100}
          disabled={busy !== null}
          onChange={setStep}
        />
        <NumberField
          label='Epochs'
          value={epochs}
          min={1}
          disabled={busy !== null}
          onChange={setEpochs}
        />
      </ForgeCard>
    </section>
  )
}
