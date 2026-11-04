import { useState } from 'react'
import {
  BookOpen,
  BrickWall,
  Castle,
  Check,
  Coins,
  Compass,
  DoorOpen,
  Landmark,
  Magnet,
  Package,
  Pencil,
  Plus,
  ScrollText,
  Shield,
  Sparkles,
  Star,
  Trash2,
  Warehouse,
  Wheat,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  Medallion,
  MiniStat,
  type KpiTone,
} from '@/components/domain'
import { Muted, Stat, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  DESIGN_FIELDS,
  DESIGN_LIMIT,
  type DesignKey,
  signed,
} from './cityFields'
import { DISTRICT_SPEC, type DistrictKind, fieldLabel } from './labels'
import { EditorTile, IconPicker, Panel } from './parts'
import { WORKING } from './tones'

type Plan = components['schemas']['SettlementPlanView']
type Design = components['schemas']['DistrictDesignView']
function Breakdown({
  title,
  icon,
  tone,
  total,
  rows,
}: {
  title: string
  icon: LucideIcon
  tone: KpiTone
  total: string
  rows: { icon: LucideIcon; label: string; value: string; hint?: string }[]
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <Text as='span' weight='medium' truncate className='flex-1'>
          {title}
        </Text>
        <Stat value={total} />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-1.5 @md/city:grid-cols-2'>
        {rows.map((row) => (
          <MiniStat
            key={row.label}
            icon={row.icon}
            label={row.label}
            value={row.value}
            tone={tone}
            hint={row.hint}
          />
        ))}
      </div>
    </div>
  )
}

export function CityWorkings({ plan }: { plan: Plan }) {
  const admin = plan.admin
  const effects = plan.district_effects
  const held = plan.locked.includes('admin_capacity')
  const quarters = DESIGN_FIELDS.filter(
    (item) =>
      !['housing', 'food_store', 'goods_store'].includes(item.key) &&
      effects[item.key] !== 0
  )
  return (
    <Panel
      title='How the city runs'
      icon={Landmark}
      tone='verdigris'
      hint='Where its reach, stores, defences and draw come from'
      wide
    >
      <div
        data-surface='CityWorkings'
        className='grid min-w-0 grid-cols-1 gap-3 @xl/city:grid-cols-2'
      >
        <Breakdown
          title='Administrative reach'
          icon={ScrollText}
          tone='verdigris'
          total={`${plan.admin_capacity}%`}
          rows={[
            { icon: Landmark, label: 'Custom', value: `${admin.base}%` },
            { icon: BookOpen, label: 'Literacy', value: `+${admin.literacy}%` },
            { icon: Pencil, label: 'Scribes', value: `+${admin.scribes}%` },
            { icon: ScrollText, label: 'Writing', value: `+${admin.writing}%` },
            { icon: Castle, label: 'Palace', value: `+${admin.palace}%` },
            {
              icon: Check,
              label: held ? 'Held by you' : 'Reckoned',
              value: `${admin.total}%`,
              hint: held
                ? 'You hold the reach; the reckoning shows what it would be'
                : 'Taxes are gathered at this reach',
            },
          ]}
        />
        <Breakdown
          title='Defences'
          icon={BrickWall}
          tone='info'
          total={`+${plan.defences.wall_pct + plan.defences.tower_pct}%`}
          rows={[
            {
              icon: BrickWall,
              label: 'Walls',
              value: `+${plan.defences.wall_pct}%`,
              hint: 'Height and stone',
            },
            {
              icon: Castle,
              label: 'Towers',
              value: `+${plan.defences.tower_pct}%`,
            },
            {
              icon: Shield,
              label: 'Battering taken',
              value: `${plan.defences.batter_pct}%`,
              hint: 'Of what engines and mines would do to plain walls',
            },
            {
              icon: DoorOpen,
              label: 'Gates weaken',
              value: `+${plan.defences.gate_weakness_pct}%`,
              hint: 'Each gate past the first is a weak point',
            },
          ]}
        />
        <Breakdown
          title='Food stores'
          icon={Wheat}
          tone='success'
          total={formatInteger(plan.food_storage.total)}
          rows={[
            {
              icon: Wheat,
              label: 'Farmland and markets',
              value: formatInteger(plan.food_storage.districts),
            },
            {
              icon: Warehouse,
              label: 'Granary workshops',
              value: formatInteger(plan.food_storage.workshops),
            },
            {
              icon: Package,
              label: 'Buildings and holds',
              value: formatInteger(plan.food_storage.other),
            },
          ]}
        />
        <Breakdown
          title='Goods stores'
          icon={Warehouse}
          tone='gold'
          total={formatInteger(plan.goods_storage.total)}
          rows={[
            {
              icon: Package,
              label: 'Markets and craft',
              value: formatInteger(plan.goods_storage.districts),
            },
            {
              icon: Warehouse,
              label: 'Warehouse workshops',
              value: formatInteger(plan.goods_storage.workshops),
            },
            {
              icon: Package,
              label: 'Buildings and holds',
              value: formatInteger(plan.goods_storage.other),
            },
          ]}
        />
        <Breakdown
          title='Prestige draws'
          icon={Star}
          tone='gold'
          total={`${plan.prestige}`}
          rows={[
            {
              icon: Magnet,
              label: 'Migrants',
              value: `+${plan.prestige_pull_pct}%`,
            },
            {
              icon: Coins,
              label: 'Investment',
              value: `+${plan.prestige_investment_pct}%`,
            },
          ]}
        />
        <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
          <div className='flex min-w-0 items-center gap-2.5'>
            <Medallion icon={Compass} tone='verdigris' size='sm' />
            <Text as='span' weight='medium' truncate>
              What its quarters give
            </Text>
          </div>
          {quarters.length === 0 ? (
            <Muted variant='caption'>
              No quarter adds order, piety, policing or trade yet.
            </Muted>
          ) : (
            <div className='grid min-w-0 grid-cols-1 gap-1.5 @md/city:grid-cols-2'>
              {quarters.map((item) => (
                <MiniStat
                  key={item.key}
                  icon={item.icon}
                  label={fieldLabel(item.key)}
                  value={
                    item.unit === '%'
                      ? `${signed(effects[item.key])}%`
                      : signed(effects[item.key])
                  }
                  tone={
                    item.signed && effects[item.key] < 0 ? 'danger' : item.tone
                  }
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </Panel>
  )
}

function overrides(design: Design): DesignKey[] {
  return DESIGN_FIELDS.map((item) => item.key).filter(
    (key) =>
      design.parameters[key] !== null && design.parameters[key] !== undefined
  )
}

type DraftValues = Partial<Record<DesignKey, string>>

function parseDraft(values: DraftValues): {
  parsed: Record<string, number | null>
  problem: string | null
} {
  const parsed: Record<string, number | null> = {}
  for (const item of DESIGN_FIELDS) {
    const raw = (values[item.key] ?? '').trim()
    if (raw === '') {
      parsed[item.key] = null
      continue
    }
    const value = Number(raw)
    const [low, high] = DESIGN_LIMIT[item.key]
    if (!Number.isInteger(value) || value < low || value > high)
      return {
        parsed,
        problem: `${fieldLabel(item.key)} runs from ${low} to ${formatInteger(high)}.`,
      }
    parsed[item.key] = value
  }
  return { parsed, problem: null }
}

function useDesignDraft(
  design: Design | null,
  plan: Plan,
  blocked: string | null
) {
  const [name, setName] = useState(design?.name ?? '')
  const [about, setAbout] = useState(design?.description ?? '')
  const [base, setBase] = useState<string>(design?.base_kind ?? 'market')
  const [values, setValues] = useState<DraftValues>(() =>
    Object.fromEntries(
      DESIGN_FIELDS.map((item) => {
        const value = design?.parameters[item.key]
        return [
          item.key,
          value === null || value === undefined ? '' : String(value),
        ]
      })
    )
  )
  const { parsed, problem } = parseDraft(values)
  const defaults = plan.kind_defaults[base as DistrictKind] ?? {}
  const tag = design?.id ?? 'new'
  const fields = (
    <>
      <EditorTile
        icon={Pencil}
        tone='gold'
        label='Name'
        htmlFor={`design-name-${tag}`}
        hint='What the cities will call it'
        held={false}
      >
        <Input
          id={`design-name-${tag}`}
          value={name}
          maxLength={80}
          disabled={blocked !== null}
          onChange={(event) => setName(event.target.value)}
        />
      </EditorTile>
      <IconPicker
        label='Built on'
        value={base}
        table={DISTRICT_SPEC}
        blocked={blocked}
        onPick={setBase}
      />
      <EditorTile
        icon={ScrollText}
        tone='muted'
        label='What it is'
        htmlFor={`design-about-${tag}`}
        hint='A line for the chronicle'
        held={false}
      >
        <Textarea
          id={`design-about-${tag}`}
          value={about}
          maxLength={2000}
          rows={2}
          disabled={blocked !== null}
          onChange={(event) => setAbout(event.target.value)}
        />
      </EditorTile>
      {DESIGN_FIELDS.map((item) => {
        const fallback = defaults[item.key] ?? 0
        const id = `design-${tag}-${item.key}`
        return (
          <EditorTile
            key={item.key}
            icon={item.icon}
            tone={(values[item.key] ?? '') === '' ? 'muted' : item.tone}
            label={`${fieldLabel(item.key)} per level`}
            htmlFor={id}
            hint={`Blank keeps the base ${formatInteger(fallback)} ${item.unit}`}
            held={false}
          >
            <Input
              id={id}
              type='number'
              inputMode='numeric'
              placeholder={String(fallback)}
              value={values[item.key] ?? ''}
              disabled={blocked !== null}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  [item.key]: event.target.value,
                }))
              }
            />
          </EditorTile>
        )
      })}
    </>
  )
  return { name, about, base, parsed, problem, fields }
}

export function DesignEditor({
  design,
  plan,
  blocked,
  onClose,
}: {
  design: Design | null
  plan: Plan
  blocked: string | null
  onClose?: () => void
}) {
  const draft = useDesignDraft(design, plan, blocked)
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:design', {
          body: {
            world_id: plan.world_id ?? 0,
            name: draft.name.trim(),
            base_kind: draft.base as DistrictKind,
            description: draft.about.trim() || null,
            values: Object.fromEntries(
              Object.entries(draft.parsed).filter(
                (entry): entry is [string, number] => entry[1] !== null
              )
            ),
          },
        })
      ),
    onDone: () => onClose?.(),
  })
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:design_edit', {
          body: {
            design_id: design?.id ?? 0,
            name: draft.name.trim(),
            base_kind: draft.base as DistrictKind,
            description: draft.about.trim() || null,
            values: draft.parsed,
          },
        })
      ),
    onDone: () => onClose?.(),
  })
  const reason =
    blocked ??
    (plan.world_id === null ? 'The city stands in no world' : null) ??
    (draft.name.trim() === '' ? 'Give the design a name.' : null) ??
    draft.problem ??
    (create.isPending || save.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/city:grid-cols-2 @3xl/city:grid-cols-3'>
        {draft.fields}
      </div>
      <div className='flex min-w-0 flex-wrap justify-end gap-2'>
        {onClose && design !== null && (
          <Button size='sm' variant='ghost' onClick={onClose}>
            Cancel
          </Button>
        )}
        <Button
          size='sm'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() =>
            design === null ? create.mutate(undefined) : save.mutate(undefined)
          }
        >
          {design === null ? <Plus /> : <Check />}
          {design === null ? 'Design it' : 'Save the design'}
        </Button>
      </div>
    </div>
  )
}

function DesignCard({
  design,
  plan,
  blocked,
}: {
  design: Design
  plan: Plan
  blocked: string | null
}) {
  const [editing, setEditing] = useState(false)
  const spec = DISTRICT_SPEC[design.base_kind]
  const changed = overrides(design)
  const built = plan.districts.filter((item) => item.design_id === design.id)
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:design_delete', {
          body: { design_id: design.id },
        })
      ),
  })
  const busy = blocked ?? (remove.isPending ? WORKING : null)
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {design.name}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`A kind of ${spec.label.toLowerCase()} · devised in epoch ${design.created_epoch}`}
          </Muted>
        </div>
        {built.length > 0 && (
          <Badge size='sm' variant='secondary'>
            <Landmark />
            {`Built here ×${built.length}`}
          </Badge>
        )}
      </div>
      {design.description && (
        <Muted variant='caption'>{design.description}</Muted>
      )}
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {changed.length === 0 ? (
          <Badge size='sm' variant='outline'>
            Same as its base
          </Badge>
        ) : (
          changed.map((key) => {
            const item = DESIGN_FIELDS.find((field) => field.key === key)
            const Icon = item?.icon ?? Sparkles
            const value = design.parameters[key] ?? 0
            return (
              <Badge key={key} size='sm' variant='outline'>
                <Icon />
                {`${fieldLabel(key)} ${formatInteger(value)} (base ${formatInteger(design.defaults[key] ?? 0)})`}
              </Badge>
            )
          })
        )}
      </div>
      {editing ? (
        <DesignEditor
          design={design}
          plan={plan}
          blocked={blocked}
          onClose={() => setEditing(false)}
        />
      ) : (
        <div className='flex min-w-0 justify-end gap-1.5'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setEditing(true)}
          >
            <Pencil />
            Rework
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate(undefined)}
          >
            <Trash2 />
            Strike
          </Button>
        </div>
      )}
    </li>
  )
}

export function DistrictDesigns({
  plan,
  blocked,
}: {
  plan: Plan
  blocked: string | null
}) {
  return (
    <Panel
      title='District designs'
      icon={Compass}
      tone='gold'
      hint='Kinds of district devised for this world, each on a base kind'
      aside={
        <Badge size='sm' variant='secondary'>
          {`${plan.designs.length} designs`}
        </Badge>
      }
      wide
    >
      {plan.designs.length === 0 ? (
        <EmptyState
          icon={Compass}
          title='No designs yet'
          description='Devise one from the city controls; every city of the world may then raise it.'
        />
      ) : (
        <ul
          data-surface='DistrictDesigns'
          className='grid min-w-0 grid-cols-1 gap-3 @xl/city:grid-cols-2'
        >
          {plan.designs.map((design) => (
            <DesignCard
              key={design.id}
              design={design}
              plan={plan}
              blocked={blocked}
            />
          ))}
        </ul>
      )}
    </Panel>
  )
}
