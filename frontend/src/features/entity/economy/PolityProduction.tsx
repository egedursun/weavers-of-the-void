import {
  ArrowRight,
  Ban,
  CircleCheck,
  CirclePause,
  Factory,
  Landmark,
  Package,
  Store,
  TriangleAlert,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  type KpiTone,
  Medallion,
  MiniStat,
  Section,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { GoodChip, PartHeader } from './EntityEconomy'
import {
  COMMODITY,
  type CommodityKind,
  MATERIAL_LABEL,
  WORKSHOP,
  type WorkshopKind,
  qualityTier,
} from './labels'
import { usePolityProduction } from './routeApi'

type Production = components['schemas']['PolityProductionView']
type Step = components['schemas']['PolityChainStepView']
type Member = components['schemas']['MemberOutputView']

type StepState = 'making' | 'short' | 'idle'

const STATE: Record<
  StepState,
  {
    label: string
    icon: typeof CircleCheck
    tone: KpiTone
    variant: 'success' | 'destructive' | 'warning'
    border: string
  }
> = {
  making: {
    label: 'Producing',
    icon: CircleCheck,
    tone: 'success',
    variant: 'success',
    border: '',
  },
  short: {
    label: 'Bottleneck',
    icon: Ban,
    tone: 'danger',
    variant: 'destructive',
    border: 'border-destructive/40 bg-destructive/5',
  },
  idle: {
    label: 'Idle',
    icon: CirclePause,
    tone: 'warning',
    variant: 'warning',
    border: 'border-warning/40 bg-warning/5',
  },
}

function stateOf(step: Step): StepState {
  if (step.bottleneck) return 'short'
  return step.made > 0 ? 'making' : 'idle'
}

function MemberNames({ ids, members }: { ids: number[]; members: Member[] }) {
  const named = members.filter((member) => ids.includes(member.community_id))
  return (
    <span className='inline-flex min-w-0 flex-wrap gap-x-1.5'>
      <Paged items={named}>
        {(member) => (
          <EntityLink
            key={member.community_id}
            kind='entity'
            id={String(member.community_id)}
          >
            {member.name}
          </EntityLink>
        )}
      </Paged>
    </span>
  )
}

function ChainLink({ step, members }: { step: Step; members: Member[] }) {
  const state = stateOf(step)
  const look = STATE[state]
  const where = step.workshop ? WORKSHOP[step.workshop as WorkshopKind] : null
  const out = COMMODITY[step.output as CommodityKind]
  const tier = qualityTier(step.quality)
  return (
    <li
      data-step={step.key}
      data-state={state}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        look.border
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={where?.icon ?? Factory}
          tone={state === 'making' ? (where?.tone ?? 'gold') : look.tone}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {step.label}
          </Text>
          <Muted variant='caption'>
            {where
              ? `${where.label} in ${step.able_ids.length} of ${plural(members.length, 'member', 'members')}`
              : 'By hand at home'}
          </Muted>
        </div>
        <Badge variant={look.variant}>
          <look.icon />
          {look.label}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {Object.entries(step.inputs).map(([kind, qty]) => (
          <GoodChip
            key={kind}
            kind={kind as CommodityKind}
            quantity={qty}
            tone={step.bottleneck === kind ? 'destructive' : 'outline'}
          />
        ))}
        <ArrowRight
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
        <GoodChip
          kind={step.output as CommodityKind}
          quantity={step.output_qty}
          tone='info'
        />
      </div>
      {state !== 'idle' && (
        <div className='flex min-w-0 flex-col gap-1.5 border-t pt-2.5'>
          {step.made > 0 && (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant='success' className='gap-1.5'>
                <out.icon />
                <span className='tabular-nums'>{`+${formatInteger(step.made)}`}</span>
                {`${out.label.toLowerCase()}${step.material ? ` of ${MATERIAL_LABEL[step.material].toLowerCase()}` : ''}`}
              </Badge>
              <Badge variant='outline'>{`${tier.label}, quality ${step.quality}`}</Badge>
              <Muted variant='caption'>
                {'Made in '}
                <MemberNames ids={step.running_ids} members={members} />
              </Muted>
            </div>
          )}
          {step.bottleneck && (
            <Text variant='caption' tone='destructive'>
              {`Short of ${COMMODITY[step.bottleneck as CommodityKind].label.toLowerCase()} in `}
              <MemberNames ids={step.starved_ids} members={members} />
            </Text>
          )}
        </div>
      )}
    </li>
  )
}

function MemberRow({ member }: { member: Member }) {
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <Medallion
        icon={member.bottlenecks > 0 ? TriangleAlert : Store}
        tone={member.bottlenecks > 0 ? 'warning' : 'gold'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        <EntityLink kind='entity' id={String(member.community_id)}>
          {member.name}
        </EntityLink>
        <Muted variant='caption'>
          {member.epoch === null
            ? 'Has made nothing yet'
            : `${plural(member.workshops, 'workshop', 'workshops')}, last worked in epoch ${member.epoch}`}
        </Muted>
      </div>
      <Badge variant='outline' className='gap-1.5'>
        <Package />
        <span className='tabular-nums'>{formatInteger(member.made)}</span>
        made
      </Badge>
      {member.bottlenecks > 0 && (
        <Badge variant='destructive'>
          <Ban />
          {`${member.bottlenecks} short`}
        </Badge>
      )}
    </li>
  )
}

function Summary({ view }: { view: Production }) {
  const steps = view.chain.filter(
    (step) => step.made > 0 || step.bottleneck || step.able_ids.length > 0
  )
  const count = (state: StepState) =>
    steps.filter((step) => stateOf(step) === state).length
  const made = view.chain.reduce((sum, step) => sum + step.made, 0)
  return (
    <div className='grid min-w-0 grid-cols-2 gap-2 @xl/realm-econ:grid-cols-4'>
      <MiniStat
        icon={CircleCheck}
        tone='success'
        label='Steps producing'
        value={count('making')}
      />
      <MiniStat
        icon={Ban}
        tone={count('short') > 0 ? 'danger' : 'muted'}
        label='Bottlenecks'
        value={count('short')}
      />
      <MiniStat
        icon={Landmark}
        tone='info'
        label='Member communities'
        value={view.members.length}
      />
      <MiniStat
        icon={Package}
        tone='gold'
        label='Goods made'
        value={formatInteger(made)}
      />
    </div>
  )
}

export function PolityProduction({ polityId }: { polityId: number }) {
  const view = usePolityProduction(polityId)
  return (
    <Section
      id='section-polity-production'
      title='The realm at work'
      description="Every member's workshops and production gathered into one chain: what the realm makes, where it is starved, and who makes it."
      icon={Factory}
    >
      {view.isPending && <LoadingBlock label='Gathering the realm’s work' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title="The realm's work could not be read"
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='PolityProduction'
          className='@container/realm-econ flex min-w-0 flex-col gap-5'
        >
          <Summary view={view.data} />
          {view.data.members.length === 0 ? (
            <EmptyState
              icon={Landmark}
              title='No member communities'
              description='Peoples and settlements that join the realm bring their workshops with them.'
            />
          ) : (
            <>
              <PartHeader
                icon={Factory}
                title='Production chain of the realm'
                note='Bottlenecks first, then what is made, then steps no member works yet.'
              />
              <ul className='grid min-w-0 grid-cols-1 gap-2 @3xl/realm-econ:grid-cols-2'>
                {[...view.data.chain]
                  .filter(
                    (step) =>
                      step.made > 0 ||
                      step.bottleneck ||
                      step.able_ids.length > 0
                  )
                  .sort((a, b) => {
                    const order: Record<StepState, number> = {
                      short: 0,
                      making: 1,
                      idle: 2,
                    }
                    return order[stateOf(a)] - order[stateOf(b)]
                  })
                  .map((step) => (
                    <ChainLink
                      key={step.key}
                      step={step}
                      members={view.data.members}
                    />
                  ))}
              </ul>
              <PartHeader
                icon={Store}
                title='Members'
                note='What each member made last and how often a missing good stopped it.'
              />
              <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/realm-econ:grid-cols-2'>
                <Paged items={view.data.members} as='li'>
                  {(member) => (
                    <MemberRow key={member.community_id} member={member} />
                  )}
                </Paged>
              </ul>
              {view.data.stocks.length > 0 && (
                <>
                  <PartHeader
                    icon={Package}
                    title='Stores of the realm'
                    note='All members together, with the average quality of each good.'
                  />
                  <div className='flex min-w-0 flex-wrap gap-1.5'>
                    <Paged items={view.data.stocks}>
                      {(stock) => (
                        <GoodChip
                          key={stock.commodity}
                          kind={stock.commodity}
                          quantity={stock.quantity}
                          suffix={`, quality ${stock.quality}`}
                        />
                      )}
                    </Paged>
                  </div>
                </>
              )}
              {Object.keys(view.data.workshops).length > 0 && (
                <div className='flex min-w-0 flex-wrap gap-1.5'>
                  <Paged items={Object.entries(view.data.workshops)}>
                    {([kind, level]) => {
                      const spec = WORKSHOP[kind as WorkshopKind]
                      return (
                        <Badge key={kind} variant='outline'>
                          <spec.icon />
                          {`${spec.label} ${level}`}
                        </Badge>
                      )
                    }}
                  </Paged>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </Section>
  )
}
