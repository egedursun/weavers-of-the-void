import { type ReactNode, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  Eye,
  EyeOff,
  HeartPulse,
  Lock,
  PersonStanding,
  Plus,
  RotateCcw,
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
import { loreKeys } from '../api/keys'
import { BodyDiagram } from '../body/BodyDiagram'
import {
  ARMOUR_ICON,
  BUILDS,
  CAPACITIES,
  CAUSES,
  CONDITIONS,
  DAMAGE,
  FUNCTIONS,
  HEALER_ICON,
  HEIGHTS,
  INJURIES,
  MATERIALS,
  MEDICINE,
  PLANS,
  READINGS,
  STATES,
  bodyValueLabel,
  named,
  plain,
} from '../body/labels'

type Body = components['schemas']['BodyView']
type Injury = components['schemas']['InjuryView']
type Condition = components['schemas']['ConditionView']
type BodyPlan = components['schemas']['BodyPlan']
type InjuryKind = components['schemas']['InjuryKind']
type DamageType = components['schemas']['DamageType']
type HarmCause = components['schemas']['HarmCause']
type ConditionKind = components['schemas']['ConditionKind']
type MaterialKind = components['schemas']['MaterialKind']
type BodyFunction = components['schemas']['BodyFunction']
type HeightClass = components['schemas']['HeightClass']
type BodyBuild = components['schemas']['BodyBuild']

const PERCENT = 100
const FACTOR_MAX = 200
const FINGER_MAX = 10
const SEVERITIES = ['1', '2', '3', '4', '5']
const BY_BLOW = 'auto'
const DEFAULT_QUALITY = 60
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
          {`${plain(HEIGHTS, body.height_class)}, ${plain(BUILDS, body.build).toLowerCase()} of build; ${body.plan_label}`}
        </Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {body.traits.map((trait) => (
            <Badge key={trait} size='sm' variant='secondary'>
              {named(FUNCTIONS, trait).label}
            </Badge>
          ))}
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
      {body.capacities.map((capacity) => {
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
      })}
    </div>
  )
}

function Functions({ body }: { body: Body }) {
  return (
    <Card title='What the body can do' icon={Activity}>
      {body.functions.map((item) => {
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
      })}
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
  const end = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/body:condition_end', {
          body: { condition_id: id },
        })
      ),
    success: 'The condition is lifted',
  })
  const reason = blocked ?? (end.isPending ? WORKING : null)
  if (body.conditions.length === 0)
    return (
      <Card title='Lives with' icon={Sparkles}>
        <Muted>No lasting condition.</Muted>
      </Card>
    )
  return (
    <Card title='Lives with' icon={Sparkles}>
      <ul className='flex min-w-0 flex-col gap-2'>
        {body.conditions.map((row: Condition) => {
          const spec = named(CONDITIONS, row.kind)
          const source = linkKind(row.source_link)
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
                </div>
                <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Muted variant='caption'>{`Since epoch ${row.since_epoch} · ${plain(CAUSES, row.source)}`}</Muted>
                  {source && row.source_node_id !== null && row.source_name && (
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
        })}
      </ul>
    </Card>
  )
}

function WoundItem({
  row,
  bearerId,
  blocked,
}: {
  row: Injury
  bearerId: number
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
  const kind = named(INJURIES, row.kind)
  const state = STATES[row.state]
  const cause = linkKind(row.cause_link)
  const reason =
    blocked ??
    (heal.isPending || visibility.isPending || unfit.isPending ? WORKING : null)
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
          {!row.visible && (
            <Badge size='sm' variant='outline'>
              Unseen
            </Badge>
          )}
          {row.prosthesis && (
            <Badge size='sm' variant='default'>
              {`${plain(MATERIALS, row.prosthesis.material)} replacement · restores ${row.prosthesis.restored_pct}%`}
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
        {body.injuries.map((row) => (
          <WoundItem
            key={row.id}
            row={row}
            bearerId={body.node_id}
            blocked={blocked}
          />
        ))}
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
      title: 'The body',
      fields: [
        {
          key: 'fingers',
          label: bodyValueLabel('fingers'),
          value: body.fingers,
          min: 0,
          max: FINGER_MAX,
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
  const [kind, setKind] = useState('chronic_illness')
  const [severity, setSeverity] = useState('2')
  const give = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:condition', {
          body: {
            bearer_id: body.node_id,
            kind: kind as ConditionKind,
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
  const [quality, setQuality] = useState(DEFAULT_QUALITY)
  const fit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/body:prosthesis', {
          body: {
            injury_id: Number(injury),
            material: material as MaterialKind,
            quality,
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
  const busy =
    reason() ??
    (release.isPending || plan.isPending || heal.isPending || frame.isPending
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
