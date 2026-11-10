import { type ReactNode, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  Check,
  Hand,
  X,
  Eye,
  EyeOff,
  HeartPulse,
  Lock,
  Minus,
  Pencil,
  PersonStanding,
  Plus,
  RotateCcw,
  Shapes,
  Sparkles,
  Swords,
  Unlock,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  PagedList,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
  type TimelineTone,
} from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  useVariants,
  variantChoices,
} from '@/features/world-rules/VariantForge'
import { RowAction } from '../actions/RowAction'
import { loreKeys } from '../api/keys'
import { BodyDiagram } from '../body/BodyDiagram'
import {
  ARMOUR_ICON,
  BLOOD_ICON,
  BUILDS,
  CAPACITIES,
  CONSCIOUSNESS,
  CAUSES,
  CONDITIONS,
  DAMAGE,
  EXERTION_ICON,
  FUNCTIONS,
  HEALER_ICON,
  HEIGHTS,
  INJURIES,
  MATERIALS,
  MEDICINE,
  NERVES,
  PLANS,
  READINGS,
  STATES,
  TISSUES,
  TREATMENTS,
  bodyValueLabel,
  named,
  plain,
} from '../body/labels'
import { useWorldMaterials } from '../economy/api'

type Body = components['schemas']['BodyView']
type Injury = components['schemas']['InjuryView']
type Condition = components['schemas']['ConditionView']
type Digit = components['schemas']['DigitView']
type Handedness = components['schemas']['Handedness']
type BodyPlan = components['schemas']['BodyPlan']
type InjuryKind = components['schemas']['InjuryKind']
type DamageType = components['schemas']['DamageType']
type HarmCause = components['schemas']['HarmCause']
type ConditionKind = components['schemas']['ConditionKind']
type MaterialKind = components['schemas']['MaterialKind']
type BodyFunction = components['schemas']['BodyFunction']
type HeightClass = components['schemas']['HeightClass']
type BodyBuild = components['schemas']['BodyBuild']
type Consciousness = components['schemas']['Consciousness']
type TreatmentStep = components['schemas']['TreatmentStep']

const PERCENT = 100
const FACTOR_MAX = 200
const TEETH_MAX = 32
const CONSCIOUSNESS_HOLD = 'consciousness'
const SEVERITIES = ['1', '2', '3', '4', '5']
const BY_BLOW = 'auto'
const DEFAULT_QUALITY = 60
const SEVERITY_CAP = 5
const INJURY_HOLD = 'injuries'
const WORKING = 'Working on it.'
const LIFE_STATES = new Set(['permanent', 'healed_scar'])
const OPEN_STATES = new Set(['fresh', 'infected', 'healing'])

function bodyKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'body'] as const
}

function linkKind(value: string | null): DrawerKind | null {
  return value === 'entity' ||
    value === 'son' ||
    value === 'foreign-god' ||
    value === 'creator'
    ? value
    : null
}

function stateTone(state: string): TimelineTone {
  if (state === 'infected' || state === 'lethal') return 'destructive'
  if (state === 'fresh' || state === 'healing') return 'warning'
  if (state === 'healed_scar') return 'success'
  return 'default'
}

function labels(table: Record<string, { label: string }>) {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}

function Card({
  title,
  icon,
  children,
  wide,
}: {
  title: string
  icon: LucideIcon
  children: ReactNode
  wide?: boolean
}) {
  return (
    <div
      className={
        wide
          ? 'flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3 @xl/body:col-span-2'
          : 'flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
      }
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} size='sm' />
        <Label variant='overline'>{title}</Label>
      </div>
      {children}
    </div>
  )
}

function Picker({
  label,
  value,
  table,
  blocked,
  onPick,
}: {
  label: string
  value: string
  table: Record<string, string>
  blocked: string | null
  onPick: (value: string) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(table).map(([key, text]) => (
            <SelectItem key={key} value={key}>
              {text}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function BodyHero({ body }: { body: Body }) {
  const plan = named(PLANS, body.plan)
  const medicine = MEDICINE[body.medicine]
  const reading = body.reading ? READINGS[body.reading] : null
  const missing = body.injuries.some(
    (row) =>
      row.visible &&
      ['severed', 'gouged', 'destroyed'].includes(row.kind) &&
      LIFE_STATES.has(row.state)
  )
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={plan.icon} tone={plan.tone ?? 'gold'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <Text weight='semibold'>{`${plan.label} body`}</Text>
        <Muted variant='caption'>
          {`${plain(HEIGHTS, body.height_class)}, ${plain(BUILDS, body.build).toLowerCase()} of build; ${body.plan_label}${body.covering_label ? `; covered in ${body.covering_label.toLowerCase()}` : ''}`}
        </Muted>
        <div className='flex min-w-0 flex-col gap-2'>
          <PagedList
            items={body.traits}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap items-center gap-1.5'
            itemKey={(trait) => trait}
          >
            {(trait) => (
              <Badge key={trait} size='sm' variant='secondary'>
                {named(FUNCTIONS, trait).label}
              </Badge>
            )}
          </PagedList>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {medicine && body.bearer_kind === 'mortal' && (
              <Badge size='sm' variant='info'>
                {medicine.label}
              </Badge>
            )}
            {reading && (
              <Badge size='sm' variant='default'>
                {`${reading.label} · presence ${body.presence_pct}%`}
              </Badge>
            )}
            {body.wholeness_required && missing && (
              <Badge size='sm' variant='destructive'>
                Barred from rule by their people's law
              </Badge>
            )}
            {body.pain > 0 && (
              <Badge size='sm' variant='warning'>
                {`Pain ${body.pain}%`}
              </Badge>
            )}
            {!body.alive && (
              <Badge size='sm' variant='secondary'>
                Fallen
              </Badge>
            )}
          </div>
        </div>
        {body.healer_id !== null && body.healer_name && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <HEALER_ICON
              aria-hidden='true'
              className='size-icon-xs text-muted-foreground'
            />
            <Muted variant='caption'>Would be tended by</Muted>
            <EntityLink kind='entity' id={String(body.healer_id)} showIcon>
              {body.healer_name}
            </EntityLink>
            {body.healer_skill !== null && (
              <Muted variant='caption'>{`skill ${body.healer_skill}`}</Muted>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Vitals({ body }: { body: Body }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/body:grid-cols-2 @3xl/body:grid-cols-4'>
      {body.hp !== null && (
        <KpiTile
          label='Health'
          value={body.hp_max ? `${body.hp}/${body.hp_max}` : body.hp}
          icon={HeartPulse}
          tone='danger'
          hint='Regained each epoch unless a wound festers'
          meter={{
            value: body.hp,
            max: body.hp_max || body.hp || 1,
            label: 'Health',
          }}
        />
      )}
      <KpiTile
        label={body.locked.includes('blood') ? 'Blood (held)' : 'Blood'}
        value={`${body.blood}%`}
        icon={BLOOD_ICON}
        tone={body.blood < PERCENT / 2 ? 'danger' : 'info'}
        hint='Lost while wounds bleed unbound; regained each epoch once they close. Too little and they faint or bleed out.'
        meter={{ value: body.blood, max: PERCENT, label: 'Blood' }}
      />
      <KpiTile
        label={
          body.locked.includes('exertion') ? 'Exertion (held)' : 'Exertion'
        }
        value={`${body.exertion}%`}
        icon={EXERTION_ICON}
        tone={body.exertion > PERCENT / 2 ? 'warning' : 'success'}
        hint='Builds with every fight, faster in heavy armour; rest wears it off and a worn body fights weaker.'
        meter={{ value: body.exertion, max: PERCENT, label: 'Exertion' }}
      />
      <KpiTile
        label={
          body.locked.includes(CONSCIOUSNESS_HOLD)
            ? 'Consciousness (held)'
            : 'Consciousness'
        }
        value={named(CONSCIOUSNESS, body.consciousness).label}
        icon={named(CONSCIOUSNESS, body.consciousness).icon}
        tone={named(CONSCIOUSNESS, body.consciousness).tone ?? 'gold'}
        hint={CONSCIOUSNESS[body.consciousness]?.hint ?? ''}
      />
      <Paged items={body.capacities}>
        {(capacity) => {
          const spec = named(CAPACITIES, capacity.key)
          const hint = CAPACITIES[capacity.key]?.hint ?? ''
          return (
            <KpiTile
              key={capacity.key}
              label={capacity.locked ? `${spec.label} (held)` : spec.label}
              value={capacity.value}
              icon={spec.icon}
              tone={spec.tone ?? 'gold'}
              change={capacity.factor - PERCENT}
              hint={`${hint} Whole: ${capacity.base}; now ${capacity.factor}% of that.`}
              meter={{
                value: Math.min(capacity.factor, PERCENT),
                max: PERCENT,
                label: spec.label,
              }}
            />
          )
        }}
      </Paged>
    </div>
  )
}

function Functions({ body }: { body: Body }) {
  return (
    <Card title='What the body can do' icon={Activity}>
      <Paged items={body.functions}>
        {(item) => {
          const spec = named(FUNCTIONS, item.key)
          return (
            <StatBar
              key={item.key}
              label={spec.label}
              value={item.level}
              max={PERCENT}
              icon={spec.icon}
              tone={
                item.level < PERCENT / 2
                  ? 'destructive'
                  : item.level < PERCENT
                    ? 'warning'
                    : 'success'
              }
            />
          )
        }}
      </Paged>
    </Card>
  )
}

const LIMBS: { part: string; side: string; label: string }[] = [
  { part: 'fingers', side: 'left', label: 'Left hand' },
  { part: 'fingers', side: 'right', label: 'Right hand' },
  { part: 'toes', side: 'left', label: 'Left foot' },
  { part: 'toes', side: 'right', label: 'Right foot' },
]

function DigitButton({
  digit,
  bearerId,
  blocked,
}: {
  digit: Digit
  bearerId: number
  blocked: string | null
}) {
  const toggle = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:digit', {
          body: { bearer_id: bearerId, digit: digit.key, lost: !digit.lost },
        })
      ),
  })
  const reason = blocked ?? (toggle.isPending ? WORKING : null)
  const name = digit.name.replace(/^./, (first) => first.toUpperCase())
  return (
    <Button
      size='sm'
      variant={digit.lost ? 'ghost' : 'outline'}
      aria-label={
        digit.lost ? `Give back the ${digit.label}` : `Take the ${digit.label}`
      }
      aria-pressed={digit.lost}
      disabled={reason !== null}
      disabledReason={
        reason ??
        `${digit.lost ? 'Give back' : 'Take'} the ${digit.label} · weighs ${digit.weight} of its limb`
      }
      onClick={() => toggle.mutate()}
    >
      {digit.lost ? (
        <X className='text-destructive' />
      ) : (
        <Check className='text-success' />
      )}
      <Text as='span' tone={digit.lost ? 'muted' : undefined}>
        {name}
      </Text>
    </Button>
  )
}

function Digits({ body, blocked }: { body: Body; blocked: string | null }) {
  const parts = new Set(body.parts.map((part) => part.key))
  const limbs = LIMBS.filter((limb) => parts.has(limb.part))
  if (limbs.length === 0) return null
  const lost = body.digits.filter((digit) => digit.lost).length
  return (
    <Card title='Hands and feet' icon={Hand} wide>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='info'>
          {body.handedness === 'both'
            ? 'Deft with both hands'
            : `Leads with the ${body.handedness} hand`}
        </Badge>
        <Badge size='sm' variant={lost > 0 ? 'destructive' : 'success'}>
          {lost > 0 ? `${lost} digits lost` : 'Every digit whole'}
        </Badge>
        <Badge size='sm' variant='secondary'>
          {`${body.teeth} of 32 teeth`}
        </Badge>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/body:grid-cols-2'>
        {limbs.map((limb) => {
          const digits = body.digits.filter(
            (digit) => digit.part === limb.part && digit.side === limb.side
          )
          const leading =
            limb.part === 'fingers' &&
            (body.handedness === 'both' || body.handedness === limb.side)
          return (
            <div
              key={`${limb.part}-${limb.side}`}
              className='flex min-w-0 flex-col gap-2 rounded-md border bg-muted/30 p-2'
            >
              <div className='flex min-w-0 items-center gap-2'>
                <Label variant='overline'>{limb.label}</Label>
                {leading && (
                  <Badge size='sm' variant='default'>
                    Leading
                  </Badge>
                )}
              </div>
              <PagedList
                items={digits}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1.5'
                itemKey={(digit) => digit.key}
              >
                {(digit) => (
                  <DigitButton
                    key={digit.key}
                    digit={digit}
                    bearerId={body.node_id}
                    blocked={blocked}
                  />
                )}
              </PagedList>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

function Armour({ body }: { body: Body }) {
  return (
    <Card title='Armour cover' icon={ARMOUR_ICON}>
      <StatBar
        label='Head'
        value={body.armour.head}
        max={PERCENT}
        tone='info'
      />
      <StatBar
        label='Torso'
        value={body.armour.torso}
        max={PERCENT}
        tone='info'
      />
      <StatBar
        label='Limbs'
        value={body.armour.limbs}
        max={PERCENT}
        tone='info'
      />
      <Muted variant='caption'>
        Helmets come with their people's metallurgy; armour and shields they own
        add the rest. A covered blow loses severity.
      </Muted>
    </Card>
  )
}

function Conditions({ body, blocked }: { body: Body; blocked: string | null }) {
  const variants = useVariants()
  const end = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/body:condition_end', {
          body: { condition_id: id },
        })
      ),
    success: 'The condition is lifted',
  })
  const weigh = useGodAction({
    run: (change: { id: number; severity: number }) =>
      unwrap(
        api.POST('/api/actions/body:condition_edit', {
          body: { condition_id: change.id, severity: change.severity },
        })
      ),
    success: 'The condition weighs differently now',
  })
  const reason = blocked ?? (end.isPending || weigh.isPending ? WORKING : null)
  if (body.conditions.length === 0)
    return (
      <Card title='Lives with' icon={Sparkles}>
        <Muted>No lasting condition.</Muted>
      </Card>
    )
  return (
    <Card title='Lives with' icon={Sparkles}>
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={body.conditions} as='li'>
          {(row: Condition) => {
            const spec = named(CONDITIONS, row.kind)
            const source = linkKind(row.source_link)
            const kinds = (variants.data ?? [])
              .filter(
                (item) => item.family === 'condition' && item.base === row.kind
              )
              .map((item) => ({ value: String(item.id), label: item.name }))
            const madeKind = (variants.data ?? []).find(
              (item) => item.id === row.variant_id
            )
            return (
              <li
                key={row.id}
                className='flex min-w-0 flex-wrap items-center gap-3 rounded-lg border bg-muted/30 p-2'
              >
                <Medallion
                  icon={spec.icon}
                  tone={
                    row.ended_epoch === null ? (spec.tone ?? 'muted') : 'muted'
                  }
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col gap-1'>
                  <div className='flex min-w-0 flex-wrap items-center gap-2'>
                    <Text weight='medium'>{spec.label}</Text>
                    <Badge size='sm' variant='secondary'>
                      {`Severity ${row.severity}/5`}
                    </Badge>
                    {row.ended_epoch !== null && (
                      <Badge size='sm' variant='success'>
                        {`Ended epoch ${row.ended_epoch}`}
                      </Badge>
                    )}
                    {!row.visible && (
                      <Badge size='sm' variant='outline'>
                        Hidden from others
                      </Badge>
                    )}
                    {madeKind && (
                      <Badge size='sm' variant='info'>
                        <Shapes />
                        {madeKind.name}
                      </Badge>
                    )}
                  </div>
                  <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                    <Muted variant='caption'>{`Since epoch ${row.since_epoch} · ${plain(CAUSES, row.source)}`}</Muted>
                    {source &&
                      row.source_node_id !== null &&
                      row.source_name && (
                        <EntityLink
                          kind={source}
                          id={String(row.source_node_id)}
                          showIcon
                        >
                          {row.source_name}
                        </EntityLink>
                      )}
                  </div>
                </div>
                {row.ended_epoch === null && (
                  <div className='flex shrink-0 items-center gap-1'>
                    <Button
                      size='icon'
                      variant='ghost'
                      aria-label='Lighten it'
                      disabled={reason !== null || row.severity <= 1}
                      disabledReason={reason ?? 'It is as light as it can be.'}
                      onClick={() =>
                        weigh.mutate({ id: row.id, severity: row.severity - 1 })
                      }
                    >
                      <Minus />
                    </Button>
                    <Button
                      size='icon'
                      variant='ghost'
                      aria-label='Deepen it'
                      disabled={reason !== null || row.severity >= SEVERITY_CAP}
                      disabledReason={reason ?? 'It is as heavy as it can be.'}
                      onClick={() =>
                        weigh.mutate({ id: row.id, severity: row.severity + 1 })
                      }
                    >
                      <Plus />
                    </Button>
                  </div>
                )}
                {row.ended_epoch === null && kinds.length > 0 && (
                  <RowAction
                    path='/api/actions/variant:assign'
                    icon={Shapes}
                    label={`Give ${spec.label.toLowerCase()} a made kind`}
                    iconOnly
                    fixed={{ family: 'condition', row_id: row.id }}
                    defaults={{ variant_id: row.variant_id ?? null }}
                    labels={{ variant_id: 'Made kind' }}
                    choices={{ variant_id: kinds }}
                  />
                )}
                {row.ended_epoch === null && (
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={reason !== null}
                    disabledReason={reason ?? undefined}
                    onClick={() => end.mutate(row.id)}
                  >
                    <RotateCcw />
                    Lift it
                  </Button>
                )}
              </li>
            )
          }}
        </Paged>
      </ul>
    </Card>
  )
}

function useWorldMaterialChoices(worldId: number | null) {
  const view = useWorldMaterials(worldId)
  return Object.fromEntries(
    (view.data?.materials ?? [])
      .filter((item) => item.world_material_id !== null)
      .map((item) => [String(item.world_material_id), item.label])
  )
}

function ProsthesisRework({
  prosthesis,
  worldId,
  blocked,
}: {
  prosthesis: NonNullable<Injury['prosthesis']>
  worldId: number | null
  blocked: string | null
}) {
  const [quality, setQuality] = useState(prosthesis.quality)
  const [material, setMaterial] = useState<string>(prosthesis.material)
  const [made, setMade] = useState(
    prosthesis.world_material_id === null
      ? ''
      : String(prosthesis.world_material_id)
  )
  const worldMaterials = useWorldMaterialChoices(worldId)
  const rework = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:prosthesis_edit', {
          body: {
            prosthesis_id: prosthesis.id,
            quality,
            material: material as MaterialKind,
            world_material_id: made === '' ? null : Number(made),
          },
        })
      ),
    success: 'The prosthesis is reworked',
  })
  const reason = blocked ?? (rework.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border p-2'>
      <Label variant='overline'>Rework the prosthesis</Label>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/body:grid-cols-3'>
        <Picker
          label='Material'
          value={material}
          table={MATERIALS}
          blocked={reason}
          onPick={setMaterial}
        />
        {Object.keys(worldMaterials).length > 0 && (
          <Picker
            label='Or a material of this world'
            value={made}
            table={worldMaterials}
            blocked={reason}
            onPick={setMade}
          />
        )}
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`rework-${prosthesis.id}`}>
            Quality (0–100)
          </Label>
          <Input
            id={`rework-${prosthesis.id}`}
            type='number'
            min={0}
            max={PERCENT}
            value={quality}
            disabled={reason !== null}
            onChange={(event) =>
              setQuality(
                Math.max(0, Math.min(PERCENT, Number(event.target.value) || 0))
              )
            }
          />
        </div>
      </div>
      <div className='flex justify-end'>
        <Button
          size='sm'
          variant='outline'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => rework.mutate()}
        >
          <Wrench />
          Rework it
        </Button>
      </div>
    </div>
  )
}

function WoundItem({
  row,
  bearerId,
  worldId,
  blocked,
}: {
  row: Injury
  bearerId: number
  worldId: number | null
  blocked: string | null
}) {
  const open = OPEN_STATES.has(row.state)
  const heal = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:heal', {
          body: { bearer_id: bearerId, injury_id: row.id, lasting: !open },
        })
      ),
    success: open ? 'The wound is healed' : 'What was lost is restored',
  })
  const unfit = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/body:prosthesis_remove', {
          body: { prosthesis_id: id },
        })
      ),
    success: 'The prosthesis is taken away',
  })
  const visibility = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:injury', {
          body: { injury_id: row.id, visible: !row.visible },
        })
      ),
    success: row.visible ? 'The mark is hidden' : 'The mark shows again',
  })
  const treat = useGodAction({
    run: (step: TreatmentStep) =>
      unwrap(
        api.POST('/api/actions/body:treat', {
          body: { injury_id: row.id, step },
        })
      ),
    success: (_result, step: TreatmentStep) =>
      `${named(TREATMENTS, step).label}: done`,
  })
  const kind = named(INJURIES, row.kind)
  const state = STATES[row.state]
  const cause = linkKind(row.cause_link)
  const reason =
    blocked ??
    (heal.isPending ||
    visibility.isPending ||
    unfit.isPending ||
    treat.isPending
      ? WORKING
      : null)
  return (
    <TimelineItem
      icon={kind.icon}
      tone={stateTone(row.state)}
      title={`${kind.label} · ${row.part_label}`}
      timestamp={
        row.year !== null
          ? `Epoch ${row.epoch}, year ${row.year}`
          : `Epoch ${row.epoch}`
      }
      framed
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {state && (
            <Badge size='sm' variant={state.badge}>
              {row.state === 'infected' && row.infected_epochs > 0
                ? `${state.label} ${row.infected_epochs}`
                : state.label}
            </Badge>
          )}
          <Badge size='sm' variant='secondary'>
            {`Severity ${row.severity}/5`}
          </Badge>
          <Badge size='sm' variant='secondary'>
            {plain(DAMAGE, row.damage_type)}
          </Badge>
          <Badge size='sm' variant='outline'>
            {plain(CAUSES, row.cause_kind)}
          </Badge>
          {row.healed_epoch !== null && (
            <Badge size='sm' variant='success'>
              {`Healed in epoch ${row.healed_epoch}`}
            </Badge>
          )}
          {!row.visible && (
            <Badge size='sm' variant='outline'>
              Unseen
            </Badge>
          )}
          {row.tissue && (
            <Badge size='sm' variant='secondary'>
              {`Reached the ${(row.tissue_label ?? named(TISSUES, row.tissue).label).toLowerCase()}`}
            </Badge>
          )}
          {row.nerve !== 'none' && (
            <Badge size='sm' variant='destructive'>
              {named(NERVES, row.nerve).label}
            </Badge>
          )}
          {row.bleeding > 0 && (
            <Badge size='sm' variant='destructive'>
              <BLOOD_ICON />
              {`Bleeding ${row.bleeding} a epoch`}
            </Badge>
          )}
          {row.misdiagnosed && (
            <Badge size='sm' variant='warning'>
              Misread by the healer
            </Badge>
          )}
          {row.prosthesis && (
            <Badge size='sm' variant='default'>
              {`${plain(MATERIALS, row.prosthesis.material)} replacement · restores ${row.prosthesis.restored_pct}%${row.prosthesis.maker_name ? ` · made by ${row.prosthesis.maker_name}` : ''}`}
            </Badge>
          )}
        </div>
        {row.function_loss > 0 && (
          <StatBar
            label='Use lost'
            value={row.function_loss}
            max={PERCENT}
            tone='destructive'
          />
        )}
        {(row.treatments.length > 0 || row.wanted.length > 0) && (
          <div className='flex min-w-0 flex-col gap-2'>
            <PagedList
              items={row.treatments}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap items-center gap-1.5'
              itemKey={(step) => step}
            >
              {(step) => {
                const look = named(TREATMENTS, step)
                return (
                  <Badge key={step} size='sm' variant='success'>
                    <look.icon />
                    {look.label}
                  </Badge>
                )
              }}
            </PagedList>
            <PagedList
              items={row.wanted}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap items-center gap-1.5'
              itemKey={(step) => step}
            >
              {(step) => {
                const look = named(TREATMENTS, step)
                return (
                  <Button
                    key={step}
                    size='sm'
                    variant='ghost'
                    disabled={reason !== null}
                    disabledReason={reason ?? undefined}
                    onClick={() => treat.mutate(step)}
                  >
                    <look.icon />
                    {look.label}
                  </Button>
                )
              }}
            </PagedList>
          </div>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {cause && row.cause_node_id !== null && row.cause_name && (
            <>
              <Muted variant='caption'>By</Muted>
              <EntityLink kind={cause} id={String(row.cause_node_id)} showIcon>
                {row.cause_name}
              </EntityLink>
            </>
          )}
          {row.event_entity_id !== null && row.event_name && (
            <>
              <Muted variant='caption'>in</Muted>
              <EntityLink
                kind='entity'
                id={String(row.event_entity_id)}
                showIcon
              >
                {row.event_name}
              </EntityLink>
            </>
          )}
          {row.treated_by_node_id !== null && row.treated_by_name && (
            <>
              <Muted variant='caption'>tended by</Muted>
              <EntityLink
                kind='entity'
                id={String(row.treated_by_node_id)}
                showIcon
              >
                {row.treated_by_name}
              </EntityLink>
            </>
          )}
          {row.prosthesis?.item_entity_id && row.prosthesis.item_name && (
            <>
              <Muted variant='caption'>wears</Muted>
              <EntityLink
                kind='entity'
                id={String(row.prosthesis.item_entity_id)}
                showIcon
              >
                {row.prosthesis.item_name}
              </EntityLink>
            </>
          )}
        </div>
        {row.state !== 'lethal' && (
          <div className='flex min-w-0 flex-wrap gap-2'>
            {(open || row.function_loss > 0) && (
              <Button
                size='sm'
                variant='outline'
                disabled={reason !== null}
                disabledReason={reason ?? undefined}
                onClick={() => heal.mutate()}
              >
                <HeartPulse />
                {open ? 'Heal it' : 'Restore it'}
              </Button>
            )}
            <Button
              size='sm'
              variant='ghost'
              disabled={reason !== null}
              disabledReason={reason ?? undefined}
              onClick={() => visibility.mutate()}
            >
              {row.visible ? <EyeOff /> : <Eye />}
              {row.visible ? 'Hide the mark' : 'Show the mark'}
            </Button>
            <RowAction
              path='/api/actions/body:injury'
              icon={Pencil}
              label='Reshape the wound'
              iconOnly
              fixed={{ injury_id: row.id }}
              defaults={{
                state: row.state,
                severity: row.severity,
                function_loss: row.function_loss,
                visible: row.visible,
                kind: row.kind,
                damage_type: row.damage_type,
                cause: row.cause_kind,
                infected_epochs: row.infected_epochs,
                tissue: row.tissue,
                bleeding: row.bleeding,
                nerve: row.nerve,
                treatments: row.treatments,
                misdiagnosed: row.misdiagnosed,
              }}
              hide={['part']}
              labels={{
                function_loss: 'Use lost (%)',
                infected_epochs: 'Epochs festering',
                tissue: 'Deepest tissue reached',
                bleeding: 'Bleeding each epoch',
                nerve: 'Nerve damage',
                treatments: 'Treatments given',
                misdiagnosed: 'Misread by the healer',
              }}
              choices={{
                tissue: Object.entries(TISSUES).map(([value, item]) => ({
                  value,
                  label: item.label,
                })),
                nerve: Object.entries(NERVES).map(([value, item]) => ({
                  value,
                  label: item.label,
                })),
                treatments: Object.entries(TREATMENTS).map(([value, item]) => ({
                  value,
                  label: item.label,
                })),
              }}
            />
            {row.prosthesis && (
              <Button
                size='sm'
                variant='ghost'
                disabled={reason !== null}
                disabledReason={reason ?? undefined}
                onClick={() =>
                  row.prosthesis && unfit.mutate(row.prosthesis.id)
                }
              >
                <Wrench />
                Take off the prosthesis
              </Button>
            )}
          </div>
        )}
        {row.prosthesis && reason === null && (
          <ProsthesisRework
            prosthesis={row.prosthesis}
            worldId={worldId}
            blocked={blocked}
          />
        )}
      </div>
    </TimelineItem>
  )
}

function Wounds({ body, blocked }: { body: Body; blocked: string | null }) {
  if (body.injuries.length === 0)
    return (
      <Card title='Wounds' icon={Swords} wide>
        <Muted>Never wounded.</Muted>
      </Card>
    )
  return (
    <Card title='Wounds' icon={Swords} wide>
      <Timeline label='Wounds'>
        <Paged items={body.injuries} as='li'>
          {(row) => (
            <WoundItem
              key={row.id}
              row={row}
              bearerId={body.node_id}
              worldId={body.world_id ?? null}
              blocked={blocked}
            />
          )}
        </Paged>
      </Timeline>
    </Card>
  )
}

function bodyGroups(body: Body): AdjustGroup[] {
  return [
    {
      title: 'Capacities (% of a whole body)',
      fields: body.capacities.map((capacity) => ({
        key: capacity.key,
        label: named(CAPACITIES, capacity.key).label,
        value: capacity.factor,
        min: 0,
        max: FACTOR_MAX,
      })),
    },
    {
      title: 'Armour and pain',
      fields: [
        {
          key: 'armour_head',
          label: bodyValueLabel('armour_head'),
          value: body.armour.head,
          min: 0,
          max: PERCENT,
        },
        {
          key: 'armour_torso',
          label: bodyValueLabel('armour_torso'),
          value: body.armour.torso,
          min: 0,
          max: PERCENT,
        },
        {
          key: 'armour_limbs',
          label: bodyValueLabel('armour_limbs'),
          value: body.armour.limbs,
          min: 0,
          max: PERCENT,
        },
        {
          key: 'pain',
          label: bodyValueLabel('pain'),
          value: body.pain,
          min: 0,
          max: PERCENT,
        },
      ],
    },
    {
      title: 'Blood and breath',
      fields: [
        {
          key: 'blood',
          label: bodyValueLabel('blood'),
          value: body.blood,
          min: 0,
          max: PERCENT,
        },
        {
          key: 'exertion',
          label: bodyValueLabel('exertion'),
          value: body.exertion,
          min: 0,
          max: PERCENT,
        },
      ],
    },
    {
      title: 'The body',
      fields: [
        {
          key: 'teeth',
          label: bodyValueLabel('teeth'),
          value: body.teeth,
          min: 0,
          max: TEETH_MAX,
        },
        ...(body.hp_max !== null
          ? [
              {
                key: 'hp_max',
                label: bodyValueLabel('hp_max'),
                value: body.hp_max,
                min: 0,
              },
            ]
          : []),
      ],
    },
  ]
}

function StrikeForm({ body, blocked }: { body: Body; blocked: string | null }) {
  const parts = Object.fromEntries(
    body.parts.map((part) => [part.key, part.label])
  )
  const [part, setPart] = useState(body.parts[0]?.key ?? '')
  const [kind, setKind] = useState(BY_BLOW)
  const [damage, setDamage] = useState(BY_BLOW)
  const [cause, setCause] = useState('player')
  const [severity, setSeverity] = useState('3')
  const [lethal, setLethal] = useState(false)
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:maim', {
          body: {
            bearer_id: body.node_id,
            part,
            kind: kind === BY_BLOW ? null : (kind as InjuryKind),
            damage_type: damage === BY_BLOW ? null : (damage as DamageType),
            cause: cause as HarmCause,
            severity: Number(severity),
            lethal,
          },
        })
      ),
  })
  const reason = blocked ?? (strike.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <Text weight='semibold'>Wound a part</Text>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/body:grid-cols-2 @3xl/body:grid-cols-5'>
        <Picker
          label='Part'
          value={part}
          table={parts}
          blocked={reason}
          onPick={setPart}
        />
        <Picker
          label='Wound'
          value={kind}
          table={{ [BY_BLOW]: 'As the blow falls', ...labels(INJURIES) }}
          blocked={reason}
          onPick={setKind}
        />
        <Picker
          label='Weapon'
          value={damage}
          table={{ [BY_BLOW]: 'By the cause', ...DAMAGE }}
          blocked={reason}
          onPick={setDamage}
        />
        <Picker
          label='Cause'
          value={cause}
          table={CAUSES}
          blocked={reason}
          onPick={setCause}
        />
        <Picker
          label='Severity'
          value={severity}
          table={Object.fromEntries(
            SEVERITIES.map((item) => [item, `${item} of 5`])
          )}
          blocked={reason}
          onPick={setSeverity}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <label className='flex items-center gap-2'>
          <Switch
            checked={lethal}
            onCheckedChange={setLethal}
            aria-label='The blow may kill'
          />
          <Text as='span'>The blow may kill</Text>
        </label>
        <Button
          size='sm'
          disabled={reason !== null || !part}
          disabledReason={reason ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Swords />
          Strike
        </Button>
      </div>
    </div>
  )
}

function ConditionForm({
  body,
  blocked,
}: {
  body: Body
  blocked: string | null
}) {
  const variants = useVariants()
  const [variant, setVariant] = useState('')
  const [kind, setKind] = useState('chronic_illness')
  const [severity, setSeverity] = useState('2')
  const give = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:condition', {
          body: {
            bearer_id: body.node_id,
            kind: kind as ConditionKind,
            variant_id: variant === '' ? null : Number(variant),
            severity: Number(severity),
          },
        })
      ),
  })
  const reason = blocked ?? (give.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <Text weight='semibold'>Give a lasting condition</Text>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/body:grid-cols-2'>
        <Picker
          label='Condition'
          value={kind}
          table={labels(CONDITIONS)}
          blocked={reason}
          onPick={setKind}
        />
        <Picker
          label='Severity'
          value={severity}
          table={Object.fromEntries(
            SEVERITIES.map((item) => [item, `${item} of 5`])
          )}
          blocked={reason}
          onPick={setSeverity}
        />
        {Object.keys(variantChoices(variants.data, 'condition', kind)).length >
          0 && (
          <Picker
            label='Of a kind made in this world'
            value={variant}
            table={variantChoices(variants.data, 'condition', kind)}
            blocked={reason}
            onPick={setVariant}
          />
        )}
      </div>
      <div className='flex justify-end'>
        <Button
          size='sm'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => give.mutate()}
        >
          <Plus />
          Give it
        </Button>
      </div>
    </div>
  )
}

function ProsthesisForm({
  body,
  blocked,
}: {
  body: Body
  blocked: string | null
}) {
  const lost = body.injuries.filter(
    (row) => row.function_loss > 0 && LIFE_STATES.has(row.state)
  )
  const choices = Object.fromEntries(
    lost.map((row) => [
      String(row.id),
      `${row.part_label} (${named(INJURIES, row.kind).label.toLowerCase()})`,
    ])
  )
  const [injury, setInjury] = useState(lost[0] ? String(lost[0].id) : '')
  const [material, setMaterial] = useState('wood')
  const [made, setMade] = useState('')
  const [quality, setQuality] = useState(DEFAULT_QUALITY)
  const worldMaterials = useWorldMaterialChoices(body.world_id ?? null)
  const fit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:prosthesis', {
          body: {
            injury_id: Number(injury),
            material: material as MaterialKind,
            quality,
            world_material_id: made === '' ? null : Number(made),
          },
        })
      ),
  })
  const reason = blocked ?? (fit.isPending ? WORKING : null)
  if (lost.length === 0 || body.bearer_kind !== 'mortal') return null
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <Text weight='semibold'>Fit a prosthesis</Text>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/body:grid-cols-3'>
        <Picker
          label='For'
          value={injury || Object.keys(choices)[0] || ''}
          table={choices}
          blocked={reason}
          onPick={setInjury}
        />
        <Picker
          label='Material'
          value={material}
          table={MATERIALS}
          blocked={reason}
          onPick={setMaterial}
        />
        {Object.keys(worldMaterials).length > 0 && (
          <Picker
            label='Or a material of this world'
            value={made}
            table={worldMaterials}
            blocked={reason}
            onPick={setMade}
          />
        )}
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`quality-${body.node_id}`}>
            Quality (0–100)
          </Label>
          <Input
            id={`quality-${body.node_id}`}
            type='number'
            min={0}
            max={PERCENT}
            value={quality}
            disabled={reason !== null}
            onChange={(event) =>
              setQuality(
                Math.max(0, Math.min(PERCENT, Number(event.target.value) || 0))
              )
            }
          />
        </div>
      </div>
      <div className='flex justify-end'>
        <Button
          size='sm'
          disabled={reason !== null || !injury}
          disabledReason={reason ?? undefined}
          onClick={() => fit.mutate()}
        >
          <Wrench />
          Fit it
        </Button>
      </div>
    </div>
  )
}

function BodyControls({ body }: { body: Body }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const set = ({ key, value }: { key: string; value: number }) =>
    unwrap(
      api.POST('/api/actions/body:set', {
        body: { bearer_id: body.node_id, field: key, value, lock: hold },
      })
    )
  const release = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/body:unlock', {
          body: { bearer_id: body.node_id, field },
        })
      ),
    success: (_result, field: string) =>
      `${bodyValueLabel(field)} follows the body again`,
  })
  const plan = useGodAction({
    run: (value: string) =>
      unwrap(
        api.POST('/api/actions/body:plan', {
          body: {
            bearer_id: body.node_id,
            plan: value as BodyPlan,
            traits: body.traits as BodyFunction[],
          },
        })
      ),
    success: 'The body is reshaped',
  })
  const frame = useGodAction({
    run: (change: { height?: string; build?: string }) =>
      unwrap(
        api.POST('/api/actions/body:frame', {
          body: {
            bearer_id: body.node_id,
            height_class: (change.height ?? body.height_class) as HeightClass,
            build: (change.build ?? body.build) as BodyBuild,
          },
        })
      ),
    success: 'The frame is changed',
  })
  const heal = useGodAction({
    run: (lasting: boolean) =>
      unwrap(
        api.POST('/api/actions/body:heal', {
          body: { bearer_id: body.node_id, lasting },
        })
      ),
  })
  const holdWounds = useGodAction({
    run: (held: boolean) =>
      unwrap(
        api.POST('/api/actions/body:injury_hold', {
          body: { bearer_id: body.node_id, hold: held },
        })
      ),
  })
  const wake = useGodAction({
    run: (value: string) =>
      unwrap(
        api.POST('/api/actions/body:consciousness', {
          body: {
            bearer_id: body.node_id,
            consciousness: value as Consciousness,
            lock: hold,
          },
        })
      ),
  })
  const lead = useGodAction({
    run: (value: string) =>
      unwrap(
        api.POST('/api/actions/body:handedness', {
          body: { bearer_id: body.node_id, handedness: value as Handedness },
        })
      ),
  })
  const woundsHeld = body.locked.includes(INJURY_HOLD)
  const busy =
    reason() ??
    (release.isPending ||
    plan.isPending ||
    heal.isPending ||
    frame.isPending ||
    wake.isPending
      ? WORKING
      : null)
  const wounded = body.injuries.some((row) => OPEN_STATES.has(row.state))
  const harmed = body.injuries.some(
    (row) => row.function_loss > 0 && row.state !== 'lethal'
  )
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-lg border border-dashed bg-muted/20 p-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>Shape this body</Text>
          <Muted variant='caption'>
            Wound, heal, mark or remake this body. A held capacity stops
            following the wounds until you release it. Every change goes into
            the ledger and can be undone.
          </Muted>
        </div>
        <label className='flex shrink-0 items-center gap-2'>
          <Switch
            checked={hold}
            onCheckedChange={setHold}
            aria-label='Hold what I set'
          />
          <Text as='span'>Hold what I set</Text>
        </label>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          variant={woundsHeld ? 'outline' : 'ghost'}
          disabled={busy !== null || holdWounds.isPending}
          disabledReason={busy ?? undefined}
          onClick={() => holdWounds.mutate(!woundsHeld)}
        >
          {woundsHeld ? <Unlock /> : <Lock />}
          {woundsHeld
            ? 'Let the wounds heal or fester again'
            : 'Hold the wounds as they are'}
        </Button>
      </div>
      {body.locked.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Lock aria-hidden='true' className='size-icon-xs text-primary' />
          {body.locked.map((key) => (
            <Button
              key={key}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(key)}
            >
              <Unlock />
              {`Release ${bodyValueLabel(key).toLowerCase()}`}
            </Button>
          ))}
        </div>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/body:grid-cols-2 @3xl/body:grid-cols-3'>
        <Picker
          label='Body plan'
          value={body.plan}
          table={labels(PLANS)}
          blocked={busy}
          onPick={(value) => plan.mutate(value)}
        />
        <Picker
          label='Height'
          value={body.height_class}
          table={HEIGHTS}
          blocked={busy}
          onPick={(value) => frame.mutate({ height: value })}
        />
        <Picker
          label='Build'
          value={body.build}
          table={BUILDS}
          blocked={busy}
          onPick={(value) => frame.mutate({ build: value })}
        />
        <Picker
          label='Leading hand'
          value={body.handedness}
          table={{ right: 'Right hand', left: 'Left hand', both: 'Both alike' }}
          blocked={busy}
          onPick={(value) => lead.mutate(value)}
        />
        <Picker
          label='Consciousness'
          value={body.consciousness}
          table={labels(CONSCIOUSNESS)}
          blocked={busy}
          onPick={(value) => wake.mutate(value)}
        />
        <div className='flex min-w-0 flex-col justify-end gap-2 @3xl/body:col-span-2'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || !wounded}
              disabledReason={busy ?? (wounded ? undefined : 'No open wound.')}
              onClick={() => heal.mutate(false)}
            >
              <HeartPulse />
              Heal the open wounds
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || !harmed}
              disabledReason={
                busy ?? (harmed ? undefined : 'Nothing to restore.')
              }
              onClick={() => heal.mutate(true)}
            >
              <Sparkles />
              Restore everything lost
            </Button>
          </div>
        </div>
      </div>
      {body.bearer_kind !== 'species' && (
        <>
          <StrikeForm body={body} blocked={busy} />
          <ProsthesisForm body={body} blocked={busy} />
          <ConditionForm body={body} blocked={busy} />
          <AdjustStats
            id={`body-${body.node_id}`}
            groups={bodyGroups(body)}
            note='Capacities are shares of what a whole body with these stats could do; 100 is whole.'
            run={set}
          />
        </>
      )}
    </div>
  )
}

export function BodySection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const view = useQuery({
    queryKey: bodyKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/bodies/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
  const body = view.data
  return (
    <Section
      id='section-body'
      title='Body'
      description='Their body as the world has shaped it: every wound and where it fell, what heals and what is lost for good, and what they can still do.'
      icon={PersonStanding}
    >
      {!body ? (
        <EmptyState
          icon={PersonStanding}
          title='No body yet'
          description='The next epoch gives this bearer a body.'
        />
      ) : (
        <div className='@container/body flex min-w-0 flex-col gap-4'>
          <BodyHero body={body} />
          {body.bearer_kind !== 'species' && <Vitals body={body} />}
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/body:grid-cols-2'>
            <Card title='The body' icon={PersonStanding} wide>
              <BodyDiagram parts={body.parts} plan={body.plan} />
            </Card>
            {body.bearer_kind !== 'species' && (
              <>
                <Functions body={body} />
                <Armour body={body} />
                <Digits body={body} blocked={reason()} />
                <Conditions body={body} blocked={reason()} />
                {body.patients_healed + body.patients_lost > 0 && (
                  <Card title='As a healer' icon={HEALER_ICON}>
                    <StatBar
                      label='Patients healed'
                      value={body.patients_healed}
                      max={Math.max(
                        1,
                        body.patients_healed + body.patients_lost
                      )}
                      tone='success'
                    />
                    <StatBar
                      label='Patients lost'
                      value={body.patients_lost}
                      max={Math.max(
                        1,
                        body.patients_healed + body.patients_lost
                      )}
                      tone='destructive'
                    />
                  </Card>
                )}
                <Wounds body={body} blocked={reason()} />
              </>
            )}
          </div>
          <BodyControls body={body} />
        </div>
      )}
    </Section>
  )
}
