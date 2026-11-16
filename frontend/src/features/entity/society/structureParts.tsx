import { useState } from 'react'
import {
  Ban,
  Coins,
  Flame,
  Hammer,
  HeartPulse,
  Sparkles,
  Users,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EntityLink, Medallion, MiniStat, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { CLASS_SPEC } from './labels'
import { Pips } from './parts'
import {
  GROUP_SPEC,
  KIND_SPEC,
  STATE_SPEC,
  type StructureView,
} from './structureLabels'
import { raising, standing } from './structureModel'
import { METER_TONE, WORKING, badTone, goodTone } from './tones'

const PERCENT = 100
const LEVEL_MAX = 5
const FUND_STEP = 100
const DAMAGE_STEP = 25

function Factor({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: 'success' | 'warning' | 'destructive' | 'secondary' | 'info'
}) {
  return (
    <Badge size='sm' variant={tone}>
      {`${label} ${value}`}
    </Badge>
  )
}

function factorTone(percent: number): 'success' | 'warning' | 'destructive' {
  if (percent >= PERCENT) return 'success'
  if (percent > 0) return 'warning'
  return 'destructive'
}

export function FunctionBreakdown({ view }: { view: StructureView }) {
  const part = view.breakdown
  if (!standing(view))
    return (
      <Muted variant='caption'>
        {raising(view)
          ? 'It does nothing until its builders finish it.'
          : 'A ruin does nothing.'}
      </Muted>
    )
  return (
    <div
      data-surface='StructureFunction'
      className='flex min-w-0 flex-col gap-2'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Factor label='Base' value={String(part.base)} tone='secondary' />
        <Muted as='span' variant='caption'>
          ×
        </Muted>
        <Factor
          label='Design'
          value={`${part.design_pct}%`}
          tone={part.design_pct >= PERCENT ? 'success' : 'warning'}
        />
        <Muted as='span' variant='caption'>
          ×
        </Muted>
        <Factor
          label='Condition'
          value={`${part.condition_pct}%`}
          tone={factorTone(part.condition_pct)}
        />
        <Muted as='span' variant='caption'>
          ×
        </Muted>
        <Factor
          label='Staff'
          value={`${part.staff_pct}%`}
          tone={factorTone(part.staff_pct)}
        />
        {part.ley_pct > PERCENT && (
          <>
            <Muted as='span' variant='caption'>
              ×
            </Muted>
            <Factor label='Ley line' value={`${part.ley_pct}%`} tone='info' />
          </>
        )}
        <Muted as='span' variant='caption'>
          =
        </Muted>
        <Factor
          label='Working at'
          value={`${part.effect_pct}%`}
          tone={factorTone(part.effect_pct * 2)}
        />
      </div>
      <Muted variant='caption'>
        {part.staff_pct === 0 && view.staff_required > 0
          ? 'No staff, no function: its posts stand empty.'
          : part.condition_pct < PERCENT
            ? `Below condition ${part.threshold} it works only as well as it stands.`
            : 'Whole and manned, it works at full strength.'}
      </Muted>
    </div>
  )
}

export function StructureCard({
  view,
  blocked,
}: {
  view: StructureView
  blocked: string | null
}) {
  const kind = KIND_SPEC[view.kind]
  const state = STATE_SPEC[view.construction_state]
  const finish = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:finish', {
          body: { structure_id: view.id },
        })
      ),
  })
  const fund = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:fund', {
          body: { structure_id: view.id, amount: FUND_STEP },
        })
      ),
  })
  const repair = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:repair', {
          body: { structure_id: view.id },
        })
      ),
  })
  const damage = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:damage', {
          body: { structure_id: view.id, amount: DAMAGE_STEP, cause: '' },
        })
      ),
  })
  const pending =
    finish.isPending || fund.isPending || repair.isPending || damage.isPending
  const busy = blocked ?? (pending ? WORKING : null)
  const build = view.construction
  return (
    <li
      data-surface='StructureCard'
      className='flex h-full min-w-0 flex-col gap-3 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={kind.icon} tone={kind.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            <EntityLink kind='entity' id={String(view.id)}>
              {view.name}
            </EntityLink>
          </Text>
          <Muted as='span' variant='caption' truncate>
            {view.design_name
              ? `${view.design_name} (${kind.label})`
              : kind.label}
          </Muted>
        </div>
        <Badge size='sm' variant='secondary'>
          <state.icon />
          {state.label}
        </Badge>
      </div>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted as='span' variant='caption'>
          {`Level ${view.level} of ${LEVEL_MAX}`}
        </Muted>
        <Pips
          value={view.level}
          max={LEVEL_MAX}
          tone={kind.tone}
          label='Level'
        />
      </div>
      {raising(view) && build ? (
        <>
          <StatBar
            label='Raised'
            icon={Hammer}
            value={build.percent}
            max={PERCENT}
            tone='warning'
          />
          <div className='grid min-w-0 grid-cols-2 gap-1.5'>
            <MiniStat
              icon={Users}
              label='Builders'
              value={formatInteger(build.workers)}
            />
            <MiniStat
              icon={Coins}
              label='Funds'
              value={formatInteger(build.funds)}
              tone='gold'
            />
          </div>
          <div className='mt-auto grid min-w-0 grid-cols-2 gap-1.5'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => fund.mutate(undefined)}
            >
              <Coins />
              {`Fund ${FUND_STEP}`}
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => finish.mutate(undefined)}
            >
              <Sparkles />
              Finish now
            </Button>
          </div>
        </>
      ) : standing(view) ? (
        <>
          <StatBar
            label='Working strength'
            icon={HeartPulse}
            value={view.effect_pct}
            max={PERCENT}
            tone={METER_TONE[goodTone(view.effect_pct)]}
          />
          <StatBar
            label='Condition'
            icon={Wrench}
            value={view.condition}
            max={view.durability || PERCENT}
            tone={METER_TONE[goodTone(view.condition, 80, 40)]}
          />
          <div className='mt-auto grid min-w-0 grid-cols-2 gap-1.5'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || view.condition >= view.durability}
              disabledReason={busy ?? 'It stands whole'}
              onClick={() => repair.mutate(undefined)}
            >
              <Wrench />
              Repair
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => damage.mutate(undefined)}
            >
              <Flame />
              Damage
            </Button>
          </div>
        </>
      ) : (
        <Muted variant='caption'>
          Only a ruin remains; stories are told of it.
        </Muted>
      )}
    </li>
  )
}

export function StaffLine({ view }: { view: StructureView }) {
  if (!view.staff_class || view.staff_required === 0)
    return <Muted variant='caption'>It needs no staff.</Muted>
  const spec = CLASS_SPEC[view.staff_class]
  const tone = goodTone(
    Math.round((view.staff_allocated * PERCENT) / view.staff_required)
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <StatBar
        label={`${spec.label} at their posts`}
        icon={spec.icon}
        value={view.staff_allocated}
        max={view.staff_required}
        tone={METER_TONE[tone]}
      />
      {view.staff_held && (
        <Badge size='sm' variant='default'>
          Staff held by your hand
        </Badge>
      )}
    </div>
  )
}

export function UpkeepLine({ view }: { view: StructureView }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2'>
      <MiniStat
        icon={Coins}
        label='Coin each age'
        value={formatInteger(view.upkeep_coin)}
        tone='gold'
      />
      <MiniStat
        icon={Hammer}
        label={`${view.upkeep_commodity.replaceAll('_', ' ')} each age`}
        value={formatInteger(view.upkeep_goods)}
        tone='warning'
      />
      <MiniStat
        icon={Ban}
        label='Unpaid ages'
        value={formatInteger(view.unpaid_epochs)}
        tone={
          badTone(view.unpaid_epochs * 20) === 'success' ? 'success' : 'danger'
        }
      />
    </div>
  )
}

export function GroupHeader({
  group,
  count,
}: {
  group: StructureView['group']
  count: number
}) {
  const spec = GROUP_SPEC[group]
  return (
    <div className='flex min-w-0 items-center gap-2'>
      <spec.icon aria-hidden='true' className='size-icon-xs text-primary' />
      <Text as='span' weight='medium'>
        {spec.label}
      </Text>
      <Badge size='sm' variant='secondary'>
        {count}
      </Badge>
    </div>
  )
}

export function AmountForm({
  label,
  icon: Icon,
  blocked,
  pending,
  max,
  onSubmit,
}: {
  label: string
  icon: LucideIcon
  blocked: string | null
  pending: boolean
  max: number
  onSubmit: (value: number) => void
}) {
  const [draft, setDraft] = useState('')
  const value = Number(draft)
  const valid =
    draft.trim() !== '' && Number.isInteger(value) && value >= 1 && value <= max
  const reason =
    blocked ??
    (pending ? WORKING : valid ? null : `Give a whole number from 1 to ${max}.`)
  return (
    <form
      className='flex min-w-0 items-center gap-2'
      onSubmit={(event) => {
        event.preventDefault()
        if (reason === null) {
          onSubmit(value)
          setDraft('')
        }
      }}
    >
      <Input
        type='number'
        inputMode='numeric'
        aria-label={label}
        placeholder={label}
        value={draft}
        disabled={blocked !== null}
        onChange={(event) => setDraft(event.target.value)}
      />
      <Button
        type='submit'
        size='sm'
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
      >
        <Icon />
        {label}
      </Button>
    </form>
  )
}
