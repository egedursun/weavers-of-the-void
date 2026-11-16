import { useState } from 'react'
import {
  Factory,
  Gauge,
  PencilRuler,
  Plus,
  Save,
  Sparkles,
  Trash2,
  Warehouse,
  Wrench,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  AttributeTile,
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  AdjustPanel,
  FIELD_GRID,
  NumberField,
  PartHeader,
} from '@/features/entity/economy/EntityEconomy'
import {
  ECONOMY_REFRESH,
  useWorkshopDesigns,
} from '@/features/entity/economy/api'
import {
  type Named,
  WORKSHOP,
  type WorkshopKind,
} from '@/features/entity/economy/labels'
import { FORM_CARD, useBusy, whole } from '@/features/entity/economy/model'
import {
  ChoiceSelect,
  ConfirmButton,
  HeldBadge,
  NoteField,
  ReleaseButton,
  TextField,
} from '@/features/entity/economy/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { Opener } from './Opener'

type Design = components['schemas']['WorkshopDesignView']
type ValueKey = 'output_pct' | 'capacity_pct' | 'store_pct' | 'quality_bonus'

const PLAIN = 100
const SHARE_MAX = 500
const BONUS_MAX = 100
const WORKSHOP_CHOICES: Record<string, Named> = { ...WORKSHOP }
const VALUES: readonly {
  key: ValueKey
  label: string
  abbr: string
  icon: typeof Factory
  max: number
  hint: string
}[] = [
  {
    key: 'output_pct',
    label: 'Output',
    abbr: 'Output',
    icon: Factory,
    max: SHARE_MAX,
    hint: '100 is a plain workshop; more makes more per batch',
  },
  {
    key: 'capacity_pct',
    label: 'Hands it takes',
    abbr: 'Capacity',
    icon: Gauge,
    max: SHARE_MAX,
    hint: 'How many batches it can run each epoch',
  },
  {
    key: 'store_pct',
    label: 'Room it adds',
    abbr: 'Storage',
    icon: Warehouse,
    max: SHARE_MAX,
    hint: 'Room it adds to the stores, 100 is plain',
  },
  {
    key: 'quality_bonus',
    label: 'Quality bonus',
    abbr: 'Quality',
    icon: Sparkles,
    max: BONUS_MAX,
    hint: 'Added to the quality of all it makes',
  },
]

function valuesOf(design: Design | null): Record<ValueKey, string> {
  return {
    output_pct: String(design?.output_pct ?? PLAIN),
    capacity_pct: String(design?.capacity_pct ?? PLAIN),
    store_pct: String(design?.store_pct ?? PLAIN),
    quality_bonus: String(design?.quality_bonus ?? 0),
  }
}

function clamp(values: Record<ValueKey, string>): Record<string, number> {
  return Object.fromEntries(
    VALUES.map((item) => [item.key, whole(values[item.key], item.max)])
  )
}

function ValueFields({
  values,
  prefix,
  onChange,
}: {
  values: Record<ValueKey, string>
  prefix: string
  onChange: (key: ValueKey, next: string) => void
}) {
  return (
    <div
      className={cn(
        FIELD_GRID,
        'grid-cols-2 @lg/design:grid-cols-4 @lg/form:grid-cols-4'
      )}
    >
      {VALUES.map((item) => (
        <NumberField
          key={item.key}
          label={`${item.label} (0–${item.max})`}
          aria={`${prefix} ${item.label}`}
          value={values[item.key]}
          max={item.max}
          onChange={(next) => onChange(item.key, next)}
        />
      ))}
    </div>
  )
}

function DesignCard({ design }: { design: Design }) {
  const [name, setName] = useState(design.name)
  const [description, setDescription] = useState(design.description ?? '')
  const [values, setValues] = useState(valuesOf(design))
  const [hold, setHold] = useState(design.held)
  const edit = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop_design:edit', {
          body: {
            design_id: design.id,
            values: clamp(values),
            name: name.trim() || null,
            description: description.trim() || null,
            hold,
          },
        })
      ),
  })
  const release = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop_design:release', {
          body: { design_id: design.id },
        })
      ),
  })
  const remove = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop_design:delete', {
          body: { design_id: design.id },
        })
      ),
  })
  const busy = useBusy(
    null,
    edit.isPending,
    release.isPending,
    remove.isPending
  )
  const spec = WORKSHOP[design.base_kind]
  return (
    <li
      data-design={design.id}
      className='@container/design flex h-full min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={spec.icon} tone={spec.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <Text weight='semibold' truncate>
            {design.name}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='outline'>
              <spec.icon />
              {`A ${spec.label.toLowerCase()} design`}
            </Badge>
            <Badge
              size='sm'
              variant={design.workshops > 0 ? 'info' : 'outline'}
            >
              <Wrench />
              {design.workshops === 0
                ? 'No workshop built to it yet'
                : `${design.workshops} ${design.workshops === 1 ? 'workshop' : 'workshops'} built to it`}
            </Badge>
            <HeldBadge held={design.held} />
          </div>
        </div>
      </div>
      {design.description && (
        <Muted variant='caption' truncate={2}>
          {design.description}
        </Muted>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-1.5 @lg/design:grid-cols-4'>
        {VALUES.map((item) => (
          <AttributeTile
            key={item.key}
            icon={item.icon}
            abbr={item.abbr}
            label={item.label}
            value={design[item.key]}
            max={item.max}
            hint={item.hint}
            tone={
              item.key !== 'quality_bonus' && design[item.key] < PLAIN
                ? 'destructive'
                : 'default'
            }
          />
        ))}
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <ReleaseButton
            held={design.held}
            busy={busy}
            onRelease={() => release.mutate(undefined)}
          />
          <ConfirmButton
            icon={Trash2}
            label='Tear up'
            title={`Tear up the design for ${design.name}?`}
            description='Workshops built to it go back to the plain kind.'
            confirm='Tear it up'
            busy={busy}
            onConfirm={() => remove.mutate(undefined)}
          />
        </div>
        <AdjustPanel
          label='Adjust the design'
          title={`Redraw ${design.name}`}
          note='100 is a plain workshop on each share; the quality bonus is added to all it makes.'
          hold={hold}
          onHold={setHold}
        >
          <div className={cn(FIELD_GRID, '@md/design:grid-cols-2')}>
            <TextField
              label={`${design.name} name`}
              value={name}
              onChange={setName}
            />
          </div>
          <ValueFields
            values={values}
            prefix={design.name}
            onChange={(key, next) =>
              setValues((current) => ({ ...current, [key]: next }))
            }
          />
          <NoteField
            label='Description'
            value={description}
            onChange={setDescription}
          />
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate(undefined)}
          >
            <Save />
            Set the design
          </Button>
        </AdjustPanel>
      </div>
    </li>
  )
}

export function DesignForge({
  worldId,
  onDone,
}: {
  worldId: number
  onDone?: () => void
}) {
  const [kind, setKind] = useState<string>('forge')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [values, setValues] = useState(valuesOf(null))
  const create = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop_design:create', {
          body: {
            world_id: worldId,
            base_kind: kind as WorkshopKind,
            name: name.trim(),
            values: clamp(values),
            description: description.trim() || null,
          },
        })
      ),
    onDone: () => {
      setName('')
      setDescription('')
      setValues(valuesOf(null))
      onDone?.()
    },
  })
  const gate = useBusy(null, create.isPending)
  const busy = gate ?? (name.trim() ? null : 'Give the design a name first.')
  return (
    <div className={FORM_CARD}>
      <PartHeader
        icon={PencilRuler}
        title='Draw a new workshop design'
        note='A better or stranger kind of workshop. Peoples of this world build to it once you set it on their workshops.'
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-2')}>
        <ChoiceSelect
          label='Kind of workshop'
          value={kind}
          table={WORKSHOP_CHOICES}
          blocked={gate}
          onPick={setKind}
        />
        <TextField
          label='Design name'
          value={name}
          placeholder='Name the design'
          onChange={setName}
        />
      </div>
      <ValueFields
        values={values}
        prefix='New design'
        onChange={(key, next) =>
          setValues((current) => ({ ...current, [key]: next }))
        }
      />
      <NoteField
        label='Description'
        value={description}
        placeholder='How it is built and what makes it better'
        onChange={setDescription}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => create.mutate(undefined)}
      >
        <Plus />
        Draw it
      </Button>
    </div>
  )
}

export function WorkshopDesigns({ worldId }: { worldId: number }) {
  const view = useWorkshopDesigns(worldId)
  return (
    <div data-surface='WorkshopDesigns' className='flex min-w-0 flex-col gap-4'>
      <PartHeader
        icon={PencilRuler}
        title='Workshop designs'
        note='Designs change how much a workshop makes, how many batches it runs, the room it adds and the quality of its goods.'
      />
      <Opener icon={PencilRuler} label='Draw a new workshop design'>
        {(close) => <DesignForge worldId={worldId} onDone={close} />}
      </Opener>
      {!view.data ? (
        <LoadingBlock label='Loading the designs' />
      ) : view.data.length === 0 ? (
        <EmptyState
          icon={PencilRuler}
          title='No designs in this world yet'
          description='Every workshop is built the plain way until a design is drawn.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-3 @3xl/eco:grid-cols-2'>
          <Paged items={view.data} as='li'>
            {(design) => (
              <DesignCard
                key={`${design.id}-${design.held}-${design.name}-${design.output_pct}-${design.capacity_pct}-${design.store_pct}-${design.quality_bonus}`}
                design={design}
              />
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}
