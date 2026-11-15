import { useState } from 'react'
import { ArrowDownRight, ArrowUpRight, Eraser, Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Paged,
  PagedList,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type CommodityKind,
  type CreditState,
  type Finance,
  type FinanceHoard,
  type FinanceIndicator,
  type FinancePolicy,
  type SpeculationStatus,
  type TradePolicyKind,
  useFinance,
} from '../finance/api'
import {
  ACCESS_ICON,
  COIN_ICON,
  CREDIT_ICON,
  CREDIT_TONE,
  FINANCE_ICON,
  HOARD_ICON,
  HOARD_TONE,
  INDICATOR_ICON,
  POLICIES,
} from '../finance/labels'
import { named } from '../mind/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { CLASS_SPEC } from '../society/labels'

const SPAN = 100
const WORKING = 'Working on it.'
const EVERY = 'every'
const REALMS = ['polity', 'settlement', 'people']
const MARKETS = ['settlement', 'people']
const STATUSES: Record<string, string> = {
  hoarding: 'Hoarding',
  sold: 'Sold',
  bust: 'Bust',
}

type Props = { view: Finance; blocked: string | null; hold: boolean }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function RemoveButton({
  label,
  busy,
  onClick,
}: {
  label: string
  busy: string | null
  onClick: () => void
}) {
  return (
    <Button
      size='icon-sm'
      variant='ghost'
      aria-label={label}
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={onClick}
    >
      <X />
    </Button>
  )
}

function CreditCard({ view, blocked, hold }: Props) {
  const credit = view.credit
  const open = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/credit:set', {
          body: { subject_id: view.node_id, rating: 50, hold },
        })
      ),
  })
  const wipe = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/credit:remove', {
          body: { subject_id: view.node_id },
        })
      ),
  })
  const state = useGodAction({
    run: (value: CreditState) =>
      unwrap(
        api.POST('/api/actions/credit:set', {
          body: { subject_id: view.node_id, state: value, hold },
        })
      ),
  })
  const busy = why(blocked, open.isPending, wipe.isPending, state.isPending)
  return (
    <MindCard
      title='Credit'
      icon={CREDIT_ICON}
      hint='Lenders rate a borrower by what it repaid, what it holds and how steady it is; the rating sets its interest, and a default brings restructuring and perhaps war.'
    >
      {credit === null ? (
        <>
          <Muted variant='caption'>No lender has judged this one yet.</Muted>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => open.mutate()}
          >
            <Plus />
            Open a record of credit
          </Button>
        </>
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-3'>
            <KpiTile
              label='Rating'
              value={credit.rating}
              icon={CREDIT_ICON}
              tone={CREDIT_TONE[credit.state] ?? 'muted'}
              meter={{
                value: credit.rating,
                max: SPAN,
                label: 'Credit rating',
              }}
            />
            <KpiTile
              label='Interest'
              value={`${credit.interest_pct}%`}
              icon={COIN_ICON}
              tone='gold'
            />
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Badge
              variant={credit.state === 'default' ? 'destructive' : 'outline'}
            >
              {credit.state_label}
            </Badge>
            <Badge variant='outline'>{`Reserves ${credit.reserves}`}</Badge>
            <Badge variant='outline'>{`${plural(credit.defaults, 'default', 'defaults')}`}</Badge>
            {credit.restructured_until !== null && (
              <Badge variant='secondary'>{`Restructuring until epoch ${credit.restructured_until}`}</Badge>
            )}
            {credit.held.length > 0 && <Badge variant='secondary'>Held</Badge>}
          </div>
          <ItemRow
            icon={CREDIT_ICON}
            tone={CREDIT_TONE[credit.state] ?? 'muted'}
            title='Set the credit by hand'
            meta='Standing, rating, interest, reserves, defaults and restructuring'
            editLabel='the credit'
            editor={
              <>
                <MindPicker
                  label='Standing with lenders'
                  value={credit.state}
                  table={table(view.credit_states)}
                  blocked={busy}
                  onPick={(value) => state.mutate(value as CreditState)}
                />
                <AdjustStats
                  id={`credit-${view.node_id}`}
                  inline
                  groups={[
                    {
                      title: 'Credit',
                      fields: [
                        {
                          key: 'rating',
                          label: 'Rating',
                          value: credit.rating,
                          min: 0,
                          max: SPAN,
                        },
                        {
                          key: 'interest_pct',
                          label: 'Interest',
                          value: credit.interest_pct,
                          min: 0,
                          max: SPAN,
                        },
                        {
                          key: 'reserves',
                          label: 'Gold and silver reserves',
                          value: credit.reserves,
                          min: 0,
                        },
                        {
                          key: 'defaults',
                          label: 'Defaults',
                          value: credit.defaults,
                          min: 0,
                        },
                        {
                          key: 'restructured_until',
                          label: 'Restructuring until epoch',
                          value: credit.restructured_until ?? 0,
                          min: 0,
                        },
                      ],
                    },
                  ]}
                  run={({ key, value }) =>
                    unwrap(
                      api.POST('/api/actions/credit:set', {
                        body: { subject_id: view.node_id, [key]: value, hold },
                      })
                    )
                  }
                />
              </>
            }
          />
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => wipe.mutate()}
          >
            <Eraser />
            Wipe the record
          </Button>
        </>
      )}
    </MindCard>
  )
}

function PolicyRow({
  row,
  blocked,
  hold,
}: {
  row: FinancePolicy
  blocked: string | null
  hold: boolean
}) {
  const spec = named(POLICIES, row.kind)
  const lift = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/trade_policy:remove', {
          body: { policy_id: row.id },
        })
      ),
  })
  const busy = why(blocked, lift.isPending)
  return (
    <ItemRow
      icon={spec.icon}
      tone={spec.tone}
      title={`${row.kind_label} on ${row.commodity_label.toLowerCase()}`}
      meta={`${row.issuer?.name ?? 'Someone'}${row.partner ? ` against ${row.partner.name}` : ''} · since epoch ${row.since_epoch}${row.reason ? ` · ${row.reason}` : ''}`}
      badges={
        <>
          {row.kind !== 'embargo' && (
            <Badge variant='outline'>{`${row.rate_pct}%`}</Badge>
          )}
          {row.held && <Badge variant='secondary'>Held</Badge>}
        </>
      }
      actions={
        <RemoveButton
          label='Lift the policy'
          busy={busy}
          onClick={() => lift.mutate()}
        />
      }
      editLabel={row.kind === 'embargo' ? undefined : 'its rate'}
      editor={
        row.kind === 'embargo' ? undefined : (
          <AdjustStats
            id={`policy-${row.id}`}
            inline
            groups={[
              {
                title: 'Rate',
                fields: [
                  {
                    key: 'rate_pct',
                    label: 'Rate',
                    value: row.rate_pct,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/trade_policy:set', {
                  body: {
                    issuer_id: row.issuer?.id ?? 0,
                    kind: row.kind,
                    commodity: row.commodity,
                    partner_id: row.partner?.id ?? null,
                    rate_pct: value,
                    hold,
                  },
                })
              )
            }
          />
        )
      }
    />
  )
}

function PoliciesCard({ view, blocked, hold }: Props) {
  const [kind, setKind] = useState<string>('tariff')
  const [good, setGood] = useState<string>(EVERY)
  const [partner, setPartner] = useState<number | null>(null)
  const issuer = view.realm?.id ?? view.node_id
  const lay = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/trade_policy:set', {
          body: {
            issuer_id: issuer,
            kind: kind as TradePolicyKind,
            commodity: good === EVERY ? null : (good as CommodityKind),
            partner_id: partner,
            rate_pct: 20,
            hold,
          },
        })
      ),
  })
  const busy = why(blocked, lay.isPending)
  const missing =
    kind === 'embargo' && good === EVERY && partner === null
      ? 'An embargo needs a partner or a good.'
      : null
  return (
    <MindCard
      title='Tariffs, subsidies and embargoes'
      icon={FINANCE_ICON}
      hint={`Policies laid by ${view.realm ? view.realm.name : 'this one'} or aimed at it. Tariffs fill the treasury and shield makers, subsidies drain it, embargoes stop trade and breed smugglers.`}
      wide
    >
      {view.policies.length === 0 ? (
        <Muted variant='caption'>
          No tariff, subsidy or embargo touches this one.
        </Muted>
      ) : (
        <Paged items={view.policies} initial={4} noun={['policy', 'policies']}>
          {(row) => (
            <PolicyRow key={row.id} row={row} blocked={blocked} hold={hold} />
          )}
        </Paged>
      )}
      <AddBar
        title={`Lay a policy for ${view.realm?.name ?? view.name}`}
        action={
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => lay.mutate()}
          >
            <FINANCE_ICON />
            Lay it
          </Button>
        }
      >
        <MindPicker
          label='Kind of policy'
          value={kind}
          table={table(view.policy_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <MindPicker
          label='Good'
          value={good}
          table={{ [EVERY]: 'Every good', ...table(view.commodities) }}
          blocked={busy}
          onPick={setGood}
        />
        <NodePicker
          label='Aimed at'
          types={REALMS}
          value={partner}
          onChange={setPartner}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

function HoardRow({
  row,
  blocked,
  hold,
}: {
  row: FinanceHoard
  blocked: string | null
  hold: boolean
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/speculation:remove', {
          body: { speculation_id: row.id },
        })
      ),
  })
  const status = useGodAction({
    run: (value: SpeculationStatus) =>
      unwrap(
        api.POST('/api/actions/speculation:edit', {
          body: { speculation_id: row.id, status: value, hold },
        })
      ),
  })
  const busy = why(blocked, strike.isPending, status.isPending)
  return (
    <ItemRow
      icon={HOARD_ICON}
      tone={HOARD_TONE[row.status] ?? 'muted'}
      title={`${row.units} ${row.commodity_label.toLowerCase()}`}
      meta={`${row.merchant?.name ?? 'Someone'} in ${row.market?.name ?? 'a market'} · bought at ${row.price} in epoch ${row.opened_epoch}${row.settled_epoch !== null ? ` · settled in epoch ${row.settled_epoch}` : ''}`}
      badges={
        <>
          <Badge variant={row.status === 'bust' ? 'destructive' : 'outline'}>
            {row.status_label}
          </Badge>
          {row.status !== 'hoarding' && (
            <Badge
              variant={row.gain >= 0 ? 'outline' : 'destructive'}
            >{`${row.gain >= 0 ? 'Gain' : 'Loss'} ${Math.abs(row.gain)}`}</Badge>
          )}
          {row.held && <Badge variant='secondary'>Held</Badge>}
        </>
      }
      actions={
        <RemoveButton
          label='Strike the hoard'
          busy={busy}
          onClick={() => strike.mutate()}
        />
      }
      editLabel='the hoard'
      editor={
        <>
          <MindPicker
            label='Status'
            value={row.status}
            table={STATUSES}
            blocked={busy}
            onPick={(value) => status.mutate(value as SpeculationStatus)}
          />
          <AdjustStats
            id={`hoard-${row.id}`}
            inline
            groups={[
              {
                title: 'Hoard',
                fields: [
                  { key: 'units', label: 'Units', value: row.units, min: 0 },
                  {
                    key: 'price',
                    label: 'Bought at',
                    value: row.price,
                    min: 0,
                  },
                  { key: 'gain', label: 'Gain', value: row.gain, min: -100000 },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/speculation:edit', {
                  body: { speculation_id: row.id, [key]: value, hold },
                })
              )
            }
          />
        </>
      }
    />
  )
}

function HoardsCard({ view, blocked, hold }: Props) {
  const [good, setGood] = useState<string>('grain')
  const [place, setPlace] = useState<number | null>(null)
  const open = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/speculation:open', {
          body: {
            merchant_id: view.node_id,
            market_id: place ?? view.node_id,
            commodity: good as CommodityKind,
            units: 20,
            price: 0,
          },
        })
      ),
  })
  const busy = why(blocked, open.isPending)
  return (
    <MindCard
      title='Speculation and hoards'
      icon={HOARD_ICON}
      hint='Greedy merchants buy up rising goods and hold them back; in famine they hoard food. A boom enriches them, a bust ruins them.'
      wide
    >
      {view.hoards.length === 0 ? (
        <Muted variant='caption'>No hoards held by or in this one.</Muted>
      ) : (
        <Paged items={view.hoards} initial={4} noun={['hoard', 'hoards']}>
          {(row) => (
            <HoardRow key={row.id} row={row} blocked={blocked} hold={hold} />
          )}
        </Paged>
      )}
      <AddBar
        title='Take goods off a market into a hoard held by this one'
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => open.mutate()}
          >
            <HOARD_ICON />
            Hoard twenty
          </Button>
        }
      >
        <MindPicker
          label='Good'
          value={good}
          table={table(view.commodities)}
          blocked={busy}
          onPick={setGood}
        />
        <NodePicker
          label='Market'
          types={MARKETS}
          value={place}
          onChange={setPlace}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

function IndicatorRow({
  row,
  previous,
  blocked,
}: {
  row: FinanceIndicator
  previous: FinanceIndicator | undefined
  blocked: string | null
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/indicator:remove', {
          body: { indicator_id: row.id },
        })
      ),
  })
  const busy = why(blocked, strike.isPending)
  const rising = previous === undefined || row.output >= previous.output
  return (
    <ItemRow
      icon={rising ? ArrowUpRight : ArrowDownRight}
      tone={rising ? 'success' : 'danger'}
      title={`Epoch ${row.epoch}: output ${row.output}`}
      meta={`prices ${row.price_index} · trade ${row.trade_balance >= 0 ? '+' : ''}${row.trade_balance} · treasury ${row.treasury} · debt ${row.debt_ratio}% · idle ${row.unemployment}% · access ${row.market_access}% · smuggled ${row.black_market}`}
      badges={
        row.held.length > 0 ? (
          <Badge variant='secondary'>Rewritten</Badge>
        ) : undefined
      }
      actions={
        <RemoveButton
          label='Strike the record'
          busy={busy}
          onClick={() => strike.mutate()}
        />
      }
      editLabel='the figures'
      editor={
        <AdjustStats
          id={`indicator-${row.id}`}
          inline
          groups={[
            {
              title: 'Figures',
              fields: [
                { key: 'output', label: 'Output', value: row.output, min: 0 },
                {
                  key: 'price_index',
                  label: 'Price index',
                  value: row.price_index,
                  min: 0,
                },
                {
                  key: 'trade_balance',
                  label: 'Trade balance',
                  value: row.trade_balance,
                  min: -100000,
                },
                {
                  key: 'treasury',
                  label: 'Treasury',
                  value: row.treasury,
                  min: -100000,
                },
                {
                  key: 'debt_ratio',
                  label: 'Debt ratio',
                  value: row.debt_ratio,
                  min: 0,
                },
                {
                  key: 'unemployment',
                  label: 'Idle hands',
                  value: row.unemployment,
                  min: 0,
                  max: SPAN,
                },
                {
                  key: 'market_access',
                  label: 'Market access',
                  value: row.market_access,
                  min: 0,
                  max: SPAN,
                },
                {
                  key: 'black_market',
                  label: 'Smuggled',
                  value: row.black_market,
                  min: 0,
                },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/indicator:edit', {
                body: { indicator_id: row.id, [key]: value },
              })
            )
          }
        />
      }
    >
      {row.living.length > 0 && (
        <PagedList
          items={row.living}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap gap-1'
          itemKey={(item) => item.key}
        >
          {(item) => (
            <Badge
              key={item.key}
              variant='outline'
            >{`${CLASS_SPEC[item.key].label} ${item.value}`}</Badge>
          )}
        </PagedList>
      )}
    </ItemRow>
  )
}

function IndicatorsCard({ view, blocked }: Props) {
  const latest = view.indicators[0]
  return (
    <MindCard
      title='The state of the economy'
      icon={INDICATOR_ICON}
      hint='Kept every epoch for realms and worlds: what they make, what things cost, how trade runs, what they owe, how many stand idle and how each class lives.'
      wide
    >
      {latest === undefined ? (
        <Muted variant='caption'>
          Kept for realms and worlds; none recorded for this one yet.
        </Muted>
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-3 @3xl/mind:grid-cols-4'>
            <KpiTile
              label='Output'
              value={latest.output}
              icon={INDICATOR_ICON}
              tone='gold'
            />
            <KpiTile
              label='Price index'
              value={latest.price_index}
              icon={COIN_ICON}
              tone={latest.price_index > 130 ? 'warning' : 'info'}
            />
            <KpiTile
              label='Trade balance'
              value={latest.trade_balance}
              icon={FINANCE_ICON}
              tone={latest.trade_balance >= 0 ? 'success' : 'danger'}
            />
            <KpiTile
              label='Idle hands'
              value={`${latest.unemployment}%`}
              icon={ACCESS_ICON}
              tone={latest.unemployment > 20 ? 'danger' : 'muted'}
              meter={{
                value: latest.unemployment,
                max: SPAN,
                label: 'Idle hands',
              }}
            />
          </div>
          <Paged items={view.indicators} initial={4} noun={['epoch', 'epochs']}>
            {(row, index) => (
              <IndicatorRow
                key={row.id}
                row={row}
                previous={view.indicators[index + 1]}
                blocked={blocked}
              />
            )}
          </Paged>
        </>
      )}
    </MindCard>
  )
}

function AccessCard({ view, hold }: Props) {
  return (
    <MindCard
      title='Market access'
      icon={ACCESS_ICON}
      hint='The share of what this place makes that its roads and routes carry to market, and what smugglers slipped in this epoch.'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Muted variant='caption'>Reaches market</Muted>
          <Text
            variant='caption'
            weight='semibold'
          >{`${view.market_access ?? 0}%`}</Text>
        </div>
        <Progress
          value={view.market_access ?? 0}
          size='sm'
          tone='success'
          aria-label={`Market access ${view.market_access ?? 0}`}
        />
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Badge
            variant={(view.black_market ?? 0) > 0 ? 'destructive' : 'outline'}
          >{`${plural(view.black_market ?? 0, 'load', 'loads')} smuggled in`}</Badge>
        </div>
      </div>
      <ItemRow
        icon={ACCESS_ICON}
        tone='verdigris'
        title='Set access by hand'
        meta='What reaches market and what was smuggled in'
        editLabel='market access'
        editor={
          <AdjustStats
            id={`access-${view.node_id}`}
            inline
            groups={[
              {
                title: 'Access',
                fields: [
                  {
                    key: 'market_access',
                    label: 'Market access',
                    value: view.market_access ?? 0,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'black_market',
                    label: 'Smuggled',
                    value: view.black_market ?? 0,
                    min: 0,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/industry:set', {
                  body: { community_id: view.node_id, [key]: value, hold },
                })
              )
            }
          />
        }
      />
    </MindCard>
  )
}

export function FinanceSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useFinance(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-finance'
        title='Trade, credit and markets'
        icon={FINANCE_ICON}
      >
        <EmptyState
          icon={FINANCE_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const blocked = reason()
  return (
    <Section
      id='section-finance'
      title='Trade, credit and markets'
      description='Credit for any borrower; the tariffs, subsidies and embargoes of its realm; hoards it holds or that are held in it; the state of the economy for realms and worlds; market access for settlements and peoples, which alone carry goods to market.'
      icon={FINANCE_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          <CreditCard view={view} blocked={blocked} hold={hold} />
          {view.market_access !== null && (
            <AccessCard view={view} blocked={blocked} hold={hold} />
          )}
          <PoliciesCard view={view} blocked={blocked} hold={hold} />
          <HoardsCard view={view} blocked={blocked} hold={hold} />
          <IndicatorsCard view={view} blocked={blocked} hold={hold} />
        </div>
        {view.realm && (
          <Muted variant='caption'>
            {'Belongs to the realm of '}
            <EntityLink kind='entity' id={String(view.realm.id)}>
              {view.realm.name}
            </EntityLink>
          </Muted>
        )}
        <ControlPanel
          title='Hold what you set'
          note='Policies, credit and hoards you set are held against the world while the switch is on; a held policy is never lifted by its realm. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
