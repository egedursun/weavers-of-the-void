import { useState } from 'react'
import {
  Coins,
  Gem,
  Lock,
  Scale,
  ShoppingBasket,
  TriangleAlert,
  UtensilsCrossed,
  Wheat,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  ChangeChip,
  EmptyState,
  KpiTile,
  Medallion,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { COMMODITY, type CommodityKind } from '../economy/labels'
import { useSocietyDepth } from './depthApi'
import {
  EFFECT_ORDER,
  EFFECT_SPEC,
  type SocietyDepth,
  standingLabel,
} from './depthLabels'
import { CLASS_ORDER, CLASS_SPEC, type SocialClass, type Spec } from './labels'
import {
  AdjustPanel,
  EditorGroup,
  HeldStrip,
  IconPicker,
  NumberEditor,
  Panel,
} from './parts'
import { METER_TONE, TONE_COLOR, WORKING, badTone, goodTone } from './tones'

type Standing = SocietyDepth['classes'][number]
type Need = SocietyDepth['needs'][number]

const PERCENT = 100
const LUXURY_MAX = 1000
const WEALTH_MAX = 1000000000
const LORENZ = 100
const SEPARATOR = ':'

function weighted(rows: Standing[], value: (row: Standing) => number): number {
  const whole = rows.reduce((total, row) => total + row.share, 0)
  if (whole <= 0) return PERCENT
  return Math.round(
    rows.reduce((total, row) => total + value(row) * row.share, 0) / whole
  )
}

function commoditySpec(kind: string): Spec {
  const found = COMMODITY[kind as CommodityKind]
  return found
    ? { label: found.label, icon: found.icon, tone: 'muted' }
    : { label: kind, icon: ShoppingBasket, tone: 'muted' }
}

function metPct(need: Need): number {
  return need.wanted > 0 ? Math.round((need.got / need.wanted) * PERCENT) : 100
}

function NeedChip({ need }: { need: Need }) {
  const spec = commoditySpec(need.commodity)
  const met = metPct(need)
  const tone = goodTone(met, 90, 50)
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0} className='inline-flex min-w-0'>
          <Badge
            size='sm'
            variant={
              tone === 'success'
                ? 'success'
                : tone === 'danger'
                  ? 'destructive'
                  : 'warning'
            }
          >
            <spec.icon />
            {`${spec.label} ${met}%`}
            {need.held_pct !== null && <Lock />}
          </Badge>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        {`${formatInteger(need.got)} of ${formatInteger(need.wanted)} wanted; ${EFFECT_SPEC[need.effect].hint ?? ''}`}
      </TooltipContent>
    </Tooltip>
  )
}

function ClassBasket({
  row,
  needs,
  staples,
}: {
  row: Standing
  needs: Need[]
  staples: string[]
}) {
  const spec = CLASS_SPEC[row.social_class]
  const short = needs.filter(
    (need) =>
      metPct(need) < PERCENT &&
      (need.effect !== 'hunger' || staples.includes(need.commodity))
  )
  return (
    <div className='flex h-full min-w-0 flex-col gap-2.5 rounded-lg border bg-muted/30 p-2.5'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {spec.label}
          </Text>
          <Muted as='span' variant='caption'>
            {`${row.share.toFixed(1)}% of the people`}
          </Muted>
        </div>
        {row.locked.length > 0 && (
          <Badge size='sm'>
            <Lock />
            Held
          </Badge>
        )}
      </div>
      <StatBar
        label='Fed'
        icon={Wheat}
        value={row.fed_pct}
        max={PERCENT}
        tone={METER_TONE[goodTone(row.fed_pct, 90, 50)]}
      />
      <StatBar
        label='Needs met'
        icon={ShoppingBasket}
        value={row.needs_met_pct}
        max={PERCENT}
        tone={METER_TONE[goodTone(row.needs_met_pct, 80, 40)]}
      />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {row.luxury_pct >= 150 && (
          <Badge size='sm' variant='default'>
            <Gem />
            {`Luxury ${row.luxury_pct}%`}
          </Badge>
        )}
        {short.length === 0 ? (
          <Muted variant='caption'>Nothing they need goes short.</Muted>
        ) : (
          short.map((need) => <NeedChip key={need.commodity} need={need} />)
        )}
      </div>
    </div>
  )
}

function HoldNeed({
  view,
  blocked,
}: {
  view: SocietyDepth
  blocked: string | null
}) {
  const [socialClass, setSocialClass] = useState<string>('farmer')
  const [commodity, setCommodity] = useState<string>('medicine')
  const [pct, setPct] = useState('100')
  const run = useGodAction({
    run: (held: number | null) =>
      unwrap(
        api.POST('/api/actions/needs:hold', {
          body: {
            community_id: view.entity_id,
            social_class: socialClass as SocialClass,
            commodity: commodity as CommodityKind,
            held_pct: held,
          },
        })
      ),
  })
  const release = useGodAction({
    run: (key: string) => {
      const [held, kind] = key.split(SEPARATOR)
      return unwrap(
        api.POST('/api/actions/needs:hold', {
          body: {
            community_id: view.entity_id,
            social_class: held as SocialClass,
            commodity: kind as CommodityKind,
            held_pct: null,
          },
        })
      )
    },
    success: 'The need is met as the stores allow again',
  })
  const busy = blocked ?? (run.isPending || release.isPending ? WORKING : null)
  const parsed = Number(pct)
  const invalid = !Number.isInteger(parsed) || parsed < 0 || parsed > PERCENT
  const commodities = Object.fromEntries(
    Object.keys(COMMODITY).map((key) => [key, commoditySpec(key)])
  )
  const heldKeys = view.needs
    .filter((need) => need.held_pct !== null)
    .map((need) => `${need.social_class}${SEPARATOR}${need.commodity}`)
  return (
    <EditorGroup title='Who goes short' icon={ShoppingBasket} pairs>
      <div className='col-span-full'>
        <HeldStrip
          keys={heldKeys}
          labelOf={(key) => {
            const [held, kind] = key.split(SEPARATOR)
            return `${CLASS_SPEC[held as SocialClass].label} ${commoditySpec(kind).label}`
          }}
          blocked={busy}
          onRelease={(keys) => keys.forEach((key) => release.mutate(key))}
        />
      </div>
      <IconPicker
        label='Class'
        value={socialClass}
        table={CLASS_SPEC}
        blocked={busy}
        onPick={setSocialClass}
      />
      <IconPicker
        label='Good'
        value={commodity}
        table={commodities}
        blocked={busy}
        onPick={setCommodity}
      />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`need-pct-${view.entity_id}`}>
          Share of the want met
        </FieldLabel>
        <Input
          id={`need-pct-${view.entity_id}`}
          type='number'
          min={0}
          max={PERCENT}
          value={pct}
          disabled={busy !== null}
          onChange={(event) => setPct(event.target.value)}
        />
      </div>
      <div className='flex min-w-0 items-end'>
        <Button
          size='sm'
          className='w-full'
          disabled={busy !== null || invalid}
          disabledReason={busy ?? 'Give a share from 0 to 100.'}
          onClick={() => run.mutate(parsed)}
        >
          <Lock />
          Hold this need
        </Button>
      </div>
    </EditorGroup>
  )
}

function StandingControls({
  view,
  blocked,
}: {
  view: SocietyDepth
  blocked: string | null
}) {
  const present = view.classes.filter((row) => row.share > 0)
  const [socialClass, setSocialClass] = useState<string>(
    present[0]?.social_class ?? 'farmer'
  )
  const row = view.classes.find((item) => item.social_class === socialClass)
  const edit = useGodAction({
    run: ({ key, value }: { key: string; value: number }) =>
      unwrap(
        api.POST('/api/actions/class:standing', {
          body: {
            community_id: view.entity_id,
            social_class: socialClass as SocialClass,
            values: { [key]: value },
            release: [],
          },
        })
      ),
    success: (_result, change) => `${standingLabel(change.key)} held`,
  })
  const release = useGodAction({
    run: (keys: string[]) =>
      unwrap(
        api.POST('/api/actions/class:standing', {
          body: {
            community_id: view.entity_id,
            social_class: socialClass as SocialClass,
            values: {},
            release: keys,
          },
        })
      ),
    success: 'They fare as the world decides again',
  })
  const busy = blocked ?? (release.isPending ? WORKING : null)
  const classes = Object.fromEntries(
    present.map((item) => [item.social_class, CLASS_SPEC[item.social_class]])
  )
  if (!row) return null
  const fields = [
    { key: 'fed_pct', icon: Wheat, max: PERCENT, value: row.fed_pct },
    {
      key: 'needs_met_pct',
      icon: ShoppingBasket,
      max: PERCENT,
      value: row.needs_met_pct,
    },
    { key: 'luxury_pct', icon: Gem, max: LUXURY_MAX, value: row.luxury_pct },
  ]
  return (
    <EditorGroup title='How a class fares' icon={Scale}>
      <div className='col-span-full flex min-w-0 flex-col gap-3'>
        <IconPicker
          label='Class'
          value={socialClass}
          table={classes}
          blocked={blocked}
          onPick={setSocialClass}
        />
        <HeldStrip
          keys={row.locked.filter((key) => key !== 'wealth')}
          labelOf={standingLabel}
          blocked={busy}
          onRelease={(keys) => release.mutate(keys)}
        />
      </div>
      {fields.map((field) => (
        <NumberEditor
          key={`${socialClass}-${field.key}-${field.value}`}
          id={`standing-${view.entity_id}-${socialClass}`}
          field={{
            key: field.key,
            label: standingLabel(field.key),
            icon: field.icon,
            value: field.value,
            min: 0,
            max: field.max,
            unit: '%',
          }}
          held={row.locked.includes(field.key)}
          blocked={blocked}
          pending={edit.isPending && edit.variables?.key === field.key}
          onSet={(value) => edit.mutate({ key: field.key, value })}
        />
      ))}
    </EditorGroup>
  )
}

export function NeedsSection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useSocietyDepth(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  const present = (data?.classes ?? []).filter((row) => row.share > 0)
  const effects = EFFECT_ORDER.map((effect) => ({
    effect,
    short: data?.effects.find((item) => item.effect === effect)?.short_pct,
  })).filter(
    (item): item is { effect: (typeof EFFECT_ORDER)[number]; short: number } =>
      item.short !== undefined
  )
  const worst = [...effects].sort((left, right) => right.short - left.short)[0]
  return (
    <Section
      id='section-needs'
      title='Needs and shortfalls'
      description='What each class wants and gets of every good, and what each missing good does to them.'
      icon={ShoppingBasket}
    >
      {view.isPending && <Muted>Weighing the stores…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The stores could not be weighed'
          description={view.error.message}
        />
      )}
      {data && present.length === 0 && (
        <EmptyState
          icon={ShoppingBasket}
          title='Not weighed yet'
          description='The needs of each class are weighed at the end of the next epoch.'
        />
      )}
      {data && present.length > 0 && (
        <div
          data-surface='NeedsBasket'
          className='@container/needs flex min-w-0 flex-col gap-4'
        >
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/needs:grid-cols-4'>
            <KpiTile
              label='Fed'
              value={`${weighted(present, (row) => row.fed_pct)}%`}
              icon={Wheat}
              tone={goodTone(
                weighted(present, (row) => row.fed_pct),
                90,
                50
              )}
              hint='Share of the people who ate their fill'
              meter={{
                value: weighted(present, (row) => row.fed_pct),
                max: PERCENT,
                label: 'Fed',
              }}
            />
            <KpiTile
              label='Needs met'
              value={`${weighted(present, (row) => row.needs_met_pct)}%`}
              icon={ShoppingBasket}
              tone={goodTone(weighted(present, (row) => row.needs_met_pct))}
              hint='Goods beyond food, weighed by what each class needs'
            />
            <KpiTile
              label='Worst want'
              value={
                worst && worst.short > 0
                  ? EFFECT_SPEC[worst.effect].label
                  : 'None'
              }
              icon={
                worst && worst.short > 0
                  ? EFFECT_SPEC[worst.effect].icon
                  : UtensilsCrossed
              }
              tone={worst && worst.short > 0 ? badTone(worst.short) : 'success'}
              hint={
                worst && worst.short > 0
                  ? `${worst.short}% short`
                  : 'Every want is met'
              }
            />
            <KpiTile
              label='Cuisine'
              value={
                data.staples.length > 0
                  ? data.staples
                      .map((kind) => commoditySpec(kind).label)
                      .join(', ')
                  : 'Anything'
              }
              icon={
                data.staples[0]
                  ? commoditySpec(data.staples[0]).icon
                  : UtensilsCrossed
              }
              tone='verdigris'
              hint='Staples eaten first and wanted most at market'
            />
          </div>
          <Panel
            title='What goes short'
            icon={TriangleAlert}
            tone={worst && worst.short > 0 ? badTone(worst.short) : 'success'}
            hint='Each missing good has its own effect'
          >
            <div className='grid min-w-0 grid-cols-1 gap-3 @xl/needs:grid-cols-3'>
              {effects.map(({ effect, short }) => {
                const spec = EFFECT_SPEC[effect]
                return (
                  <Tooltip key={effect}>
                    <TooltipTrigger asChild>
                      <div tabIndex={0} className='min-w-0'>
                        <StatBar
                          label={spec.label}
                          icon={spec.icon}
                          value={short}
                          max={PERCENT}
                          tone={METER_TONE[badTone(short)]}
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>{spec.hint}</TooltipContent>
                  </Tooltip>
                )
              })}
            </div>
          </Panel>
          <Panel
            title="Each class's basket"
            icon={ShoppingBasket}
            hint='The richest are served first when goods run short'
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 @md/needs:grid-cols-2 @3xl/needs:grid-cols-3'>
              {CLASS_ORDER.map((socialClass) =>
                present.find((row) => row.social_class === socialClass)
              )
                .filter((row): row is Standing => row !== undefined)
                .map((row) => (
                  <ClassBasket
                    key={row.social_class}
                    row={row}
                    needs={data.needs.filter(
                      (need) => need.social_class === row.social_class
                    )}
                    staples={data.staples}
                  />
                ))}
            </div>
          </Panel>
          <AdjustPanel
            title='Feed or starve them'
            note='Hold how much of a good a class receives, or how fed, provided and pampered it is. What you hold is kept against the stores until you release it; every change can be undone from the ledger.'
          >
            <HoldNeed view={data} blocked={blocked} />
            <StandingControls view={data} blocked={blocked} />
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

function Lorenz({ rows }: { rows: Standing[] }) {
  const ordered = [...rows].sort(
    (left, right) =>
      left.wealth / Math.max(left.share, 0.01) -
      right.wealth / Math.max(right.share, 0.01)
  )
  const people = ordered.reduce((total, row) => total + row.share, 0) || 1
  const riches = ordered.reduce((total, row) => total + row.wealth, 0) || 1
  let x = 0
  let y = 0
  const points = ['0,100']
  for (const row of ordered) {
    x += (row.share / people) * LORENZ
    y += (row.wealth / riches) * LORENZ
    points.push(`${x.toFixed(1)},${(LORENZ - y).toFixed(1)}`)
  }
  return (
    <svg
      viewBox={`0 0 ${LORENZ} ${LORENZ}`}
      className='aspect-square w-full max-w-60 min-w-0'
      role='img'
      aria-label='How wealth is shared: the further the curve from the line, the greater the inequality'
    >
      <rect
        x={0}
        y={0}
        width={LORENZ}
        height={LORENZ}
        rx={4}
        className='fill-muted/40'
      />
      <line
        x1={0}
        y1={LORENZ}
        x2={LORENZ}
        y2={0}
        stroke={TONE_COLOR.muted}
        strokeDasharray='3 3'
      />
      <polyline
        points={points.join(' ')}
        fill='none'
        stroke={TONE_COLOR.gold}
        strokeWidth={2.5}
      />
    </svg>
  )
}

function WealthControls({
  view,
  blocked,
}: {
  view: SocietyDepth
  blocked: string | null
}) {
  const edit = useGodAction({
    run: ({
      socialClass,
      wealth,
    }: {
      socialClass: SocialClass
      wealth: number
    }) =>
      unwrap(
        api.POST('/api/actions/class:standing', {
          body: {
            community_id: view.entity_id,
            social_class: socialClass,
            values: { wealth },
            release: [],
          },
        })
      ),
    success: 'Wealth held',
  })
  const release = useGodAction({
    run: (socialClass: SocialClass) =>
      unwrap(
        api.POST('/api/actions/class:standing', {
          body: {
            community_id: view.entity_id,
            social_class: socialClass,
            values: {},
            release: ['wealth'],
          },
        })
      ),
    success: 'Their wealth follows the world again',
  })
  const busy = blocked ?? (release.isPending ? WORKING : null)
  const present = view.classes.filter((row) => row.share > 0)
  const held = present
    .filter((row) => row.locked.includes('wealth'))
    .map((row) => row.social_class)
  return (
    <EditorGroup title='Wealth of each class' icon={Coins}>
      <div className='col-span-full'>
        <HeldStrip
          keys={held}
          labelOf={(key) => `${CLASS_SPEC[key as SocialClass].label} wealth`}
          blocked={busy}
          onRelease={(keys) =>
            keys.forEach((key) => release.mutate(key as SocialClass))
          }
        />
      </div>
      {present.map((row) => (
        <NumberEditor
          key={`${row.social_class}-${row.wealth}`}
          id={`wealth-${view.entity_id}`}
          field={{
            key: row.social_class,
            label: CLASS_SPEC[row.social_class].label,
            icon: CLASS_SPEC[row.social_class].icon,
            value: row.wealth,
            min: 0,
            max: WEALTH_MAX,
          }}
          held={row.locked.includes('wealth')}
          blocked={blocked}
          pending={
            edit.isPending && edit.variables?.socialClass === row.social_class
          }
          onSet={(wealth) =>
            edit.mutate({ socialClass: row.social_class, wealth })
          }
        />
      ))}
    </EditorGroup>
  )
}

export function ClassWealthSection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useSocietyDepth(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  const present = (data?.classes ?? []).filter((row) => row.share > 0)
  if (!data || present.length === 0) return null
  const ranked = [...present].sort(
    (left, right) => right.per_head - left.per_head
  )
  const richest = ranked[0]
  const poorest = ranked[ranked.length - 1]
  const top = Math.max(1, richest.per_head)
  const total = present.reduce((sum, row) => sum + row.wealth, 0)
  return (
    <Section
      id='section-class-wealth'
      title='Wealth and inequality'
      description='What each class owns, how its wealth grows or shrinks, and how unevenly it is shared. Inequality breeds crime and revolt unless the culture prizes hierarchy; bitter classes fill their factions.'
      icon={Scale}
    >
      <div
        data-surface='ClassWealth'
        className='@container/wealth flex min-w-0 flex-col gap-4'
      >
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/wealth:grid-cols-4'>
          <KpiTile
            label='Inequality'
            value={data.gini}
            icon={Scale}
            tone={badTone(data.gini, 50, 25)}
            hint='Gini over the wealth of the classes, 0 even to 100 one class holds all'
            meter={{ value: data.gini, max: PERCENT, label: 'Gini' }}
          />
          <KpiTile
            label='Wealth'
            value={formatInteger(total)}
            icon={Coins}
            tone='gold'
            hint='What all the classes own together'
          />
          <KpiTile
            label='Richest a head'
            value={formatInteger(richest.per_head)}
            icon={CLASS_SPEC[richest.social_class].icon}
            tone='gold'
            hint={CLASS_SPEC[richest.social_class].label}
          />
          <KpiTile
            label='Poorest a head'
            value={formatInteger(poorest.per_head)}
            icon={CLASS_SPEC[poorest.social_class].icon}
            tone='warning'
            hint={CLASS_SPEC[poorest.social_class].label}
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-3 @2xl/wealth:grid-cols-3'>
          <Panel
            title='How it is shared'
            icon={Scale}
            hint='Gold is the people; the dashed line is perfect equality'
          >
            <div className='flex min-w-0 justify-center'>
              <Lorenz rows={present} />
            </div>
          </Panel>
          <div className='min-w-0 @2xl/wealth:col-span-2'>
            <Panel
              title='Wealth a head'
              icon={Coins}
              hint='The change is what each class gained or lost this epoch'
            >
              <div className='flex min-w-0 flex-col gap-3'>
                {ranked.map((row) => {
                  const spec = CLASS_SPEC[row.social_class]
                  return (
                    <div
                      key={row.social_class}
                      className='flex min-w-0 items-center gap-2.5'
                    >
                      <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                      <div className='min-w-0 flex-1'>
                        <StatBar
                          label={spec.label}
                          value={row.per_head}
                          max={top}
                          showMax={false}
                          tone={METER_TONE[spec.tone ?? 'muted']}
                        />
                      </div>
                      {row.income !== 0 && <ChangeChip value={row.income} />}
                      {row.locked.includes('wealth') && (
                        <Badge size='sm'>
                          <Lock />
                          Held
                        </Badge>
                      )}
                    </div>
                  )
                })}
              </div>
            </Panel>
          </div>
        </div>
        <AdjustPanel
          title='Enrich or impoverish'
          note='Set and hold the wealth of a class. The richest are served first when goods run short, so wealth decides who goes hungry; every change can be undone from the ledger.'
        >
          <WealthControls view={data} blocked={blocked} />
        </AdjustPanel>
      </div>
    </Section>
  )
}
