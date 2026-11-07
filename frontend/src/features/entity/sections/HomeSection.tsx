import { useState } from 'react'
import { Eraser, Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type Aggregate,
  type Dwelling,
  type DwellingKind,
  type Home,
  type Household,
  type HouseholdRole,
  type Member,
  useHome,
} from '../lineage/api'
import {
  CARE_ICON,
  DWELLINGS,
  FURNISHING_ICON,
  HOME_ICON,
  PURSE_ICON,
  ROLES,
} from '../lineage/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'

const SPAN = 100
const WORKING = 'Working on it.'

type Ctx = { view: Home; blocked: string | null; hold: boolean }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function MemberRow({
  member,
  household,
  ctx,
}: {
  member: Member
  household: Household
  ctx: Ctx
}) {
  const role = useGodAction({
    run: (value: HouseholdRole) =>
      unwrap(
        api.POST('/api/actions/household:member', {
          body: {
            household_id: household.id,
            mortal_id: member.mortal.id,
            role: value,
            hold: ctx.hold,
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/household:release', {
          body: { mortal_id: member.mortal.id },
        })
      ),
  })
  const busy = why(ctx.blocked, role.isPending, release.isPending)
  const look = ROLES[member.role] ?? ROLES.dependent
  return (
    <ItemRow
      icon={look.icon}
      tone={look.tone}
      title={
        <EntityLink kind='entity' id={String(member.mortal.id)}>
          {member.mortal.name}
        </EntityLink>
      }
      meta={
        member.cares_for
          ? `${member.role_label}, caring for ${member.cares_for.name}`
          : `${member.role_label} since epoch ${member.joined_epoch}`
      }
      badges={member.held ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Take ${member.mortal.name} out of the household`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => release.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`role of ${member.mortal.name}`}
      editor={
        <MindPicker
          label='Role in the household'
          value={member.role}
          table={table(ctx.view.roles)}
          blocked={busy}
          onPick={(value) => role.mutate(value as HouseholdRole)}
        />
      }
    />
  )
}

function DwellingCard({
  household,
  dwelling,
  ctx,
}: {
  household: Household
  dwelling: Dwelling | null
  ctx: Ctx
}) {
  const [item, setItem] = useState<number | null>(null)
  const kind = useGodAction({
    run: (value: DwellingKind) =>
      unwrap(
        api.POST('/api/actions/dwelling:set', {
          body: {
            household_id: household.id,
            kind: value,
            clear_district: false,
            hold: ctx.hold,
          },
        })
      ),
  })
  const furnish = useGodAction({
    run: (itemId: number) =>
      unwrap(
        api.POST('/api/actions/furnishing:add', {
          body: { household_id: household.id, item_id: itemId },
        })
      ),
    success: () => {
      setItem(null)
      return 'Furnished'
    },
  })
  const unfurnish = useGodAction({
    run: (itemId: number) =>
      unwrap(
        api.POST('/api/actions/furnishing:remove', {
          body: { item_id: itemId },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/dwelling:remove', {
          body: { household_id: household.id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    kind.isPending,
    furnish.isPending,
    unfurnish.isPending,
    strike.isPending
  )
  const look = dwelling
    ? (DWELLINGS[dwelling.kind] ?? DWELLINGS.hut)
    : DWELLINGS.hut
  return (
    <MindCard
      title='Home'
      icon={HOME_ICON}
      hint='Quality feeds comfort, beauty, status and rest; squalor breeds sickness; a noble home must be large and fine.'
    >
      {dwelling === null ? (
        <>
          <Muted variant='caption'>
            This household has no roof of its own.
          </Muted>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => kind.mutate('hut')}
          >
            <Plus />
            Give it a hut
          </Button>
        </>
      ) : (
        <>
          <ItemRow
            icon={look.icon}
            tone={look.tone}
            title={`${dwelling.kind_label} of ${dwelling.rooms} rooms`}
            meta={
              dwelling.district_label
                ? `In the ${dwelling.district_label.toLowerCase()} district`
                : dwelling.settlement
                  ? `In ${dwelling.settlement.name}`
                  : 'Out in the open land'
            }
            badges={
              dwelling.held.length > 0 ? (
                <Badge variant='outline'>Held</Badge>
              ) : undefined
            }
            editLabel='the home'
            editor={
              <div className='flex min-w-0 flex-col gap-4'>
                <MindPicker
                  label='Kind of home'
                  value={dwelling.kind}
                  table={table(ctx.view.dwellings)}
                  blocked={busy}
                  onPick={(value) => kind.mutate(value as DwellingKind)}
                />
                <AdjustStats
                  id={`dwelling-${household.id}`}
                  inline
                  groups={[
                    {
                      title: 'Home',
                      fields: [
                        {
                          key: 'quality',
                          label: 'Quality',
                          value: dwelling.quality,
                          min: 0,
                          max: SPAN,
                        },
                        {
                          key: 'rooms',
                          label: 'Rooms',
                          value: dwelling.rooms,
                          min: 1,
                        },
                      ],
                    },
                  ]}
                  run={({ key, value }) =>
                    unwrap(
                      api.POST('/api/actions/dwelling:set', {
                        body: {
                          household_id: household.id,
                          [key]: value,
                          clear_district: false,
                          hold: ctx.hold,
                        },
                      })
                    )
                  }
                />
              </div>
            }
          />
          <div className='flex min-w-0 flex-col gap-1'>
            <div className='flex min-w-0 items-center justify-between gap-2'>
              <Muted variant='caption'>
                {`Quality ${dwelling.effective_quality}, ${dwelling.expected_quality} expected of its class`}
              </Muted>
              <Badge
                variant={
                  dwelling.effective_quality >= dwelling.expected_quality
                    ? 'secondary'
                    : 'destructive'
                }
              >
                {dwelling.effective_quality >= dwelling.expected_quality
                  ? 'A source of pride'
                  : 'Below its station'}
              </Badge>
            </div>
            <Progress
              value={dwelling.effective_quality}
              size='sm'
              tone={
                dwelling.effective_quality >= dwelling.expected_quality
                  ? 'success'
                  : 'warning'
              }
              aria-label={`Home quality ${dwelling.effective_quality}`}
            />
          </div>
          <Paged
            items={dwelling.furnishings}
            initial={4}
            noun={['furnishing', 'furnishings']}
          >
            {(entry) => (
              <ItemRow
                key={entry.item.id}
                icon={FURNISHING_ICON}
                tone='gold'
                title={
                  <EntityLink kind='entity' id={String(entry.item.id)}>
                    {entry.item.name}
                  </EntityLink>
                }
                meta={`Placed in epoch ${entry.placed_epoch}`}
                actions={
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`Take ${entry.item.name} out of the home`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => unfurnish.mutate(entry.item.id)}
                  >
                    <X />
                  </Button>
                }
              />
            )}
          </Paged>
          <AddBar
            title='Furnish the home'
            action={
              <Button
                size='sm'
                disabled={busy !== null || item === null}
                disabledReason={
                  busy ?? (item === null ? 'Choose an item first.' : undefined)
                }
                onClick={() => item !== null && furnish.mutate(item)}
              >
                <Plus />
                Furnish
              </Button>
            }
          >
            <NodePicker
              label='Item or work of art'
              types={['item', 'artwork']}
              value={item}
              onChange={setItem}
              blocked={busy}
            />
          </AddBar>
          <div className='flex justify-end'>
            <Button
              size='sm'
              variant='ghost'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => strike.mutate()}
            >
              <Eraser />
              Take the home away
            </Button>
          </div>
        </>
      )}
    </MindCard>
  )
}

function DebtsCard({ household, ctx }: { household: Household; ctx: Ctx }) {
  const [lender, setLender] = useState('')
  const owe = useGodAction({
    run: ({ lenderId, amount }: { lenderId: number; amount: number }) =>
      unwrap(
        api.POST('/api/actions/household:debt', {
          body: {
            household_id: household.id,
            lender_household_id: lenderId,
            amount,
            hold: ctx.hold,
          },
        })
      ),
  })
  const busy = why(ctx.blocked, owe.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {household.debts.length === 0 ? (
        <Muted variant='caption'>The household owes no one.</Muted>
      ) : (
        household.debts.map((debt) => (
          <ItemRow
            key={debt.household_id}
            icon={PURSE_ICON}
            tone='danger'
            title={`Owes ${debt.name}`}
            meta={`${debt.amount}, paid down with interest each epoch`}
            actions={
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  owe.mutate({ lenderId: debt.household_id, amount: 0 })
                }
              >
                Forgive
              </Button>
            }
            editLabel={`debt to ${debt.name}`}
            editor={
              <AdjustStats
                id={`debt-${household.id}-${debt.household_id}`}
                inline
                groups={[
                  {
                    title: 'Debt',
                    fields: [
                      {
                        key: 'amount',
                        label: 'Owed',
                        value: debt.amount,
                        min: 0,
                      },
                    ],
                  },
                ]}
                run={({ value }) =>
                  unwrap(
                    api.POST('/api/actions/household:debt', {
                      body: {
                        household_id: household.id,
                        lender_household_id: debt.household_id,
                        amount: value,
                        hold: ctx.hold,
                      },
                    })
                  )
                }
              />
            }
          />
        ))
      )}
      {ctx.view.neighbours.length > 0 && (
        <AddBar
          title='Put the household in debt'
          action={
            <Button
              size='sm'
              disabled={busy !== null || !lender}
              disabledReason={
                busy ?? (lender ? undefined : 'Choose a lender first.')
              }
              onClick={() =>
                owe.mutate({ lenderId: Number(lender), amount: 20 })
              }
            >
              <Plus />
              Owe 20
            </Button>
          }
        >
          <MindPicker
            label='Lending household'
            value={lender}
            table={table(ctx.view.neighbours)}
            blocked={busy}
            onPick={setLender}
          />
        </AddBar>
      )}
    </div>
  )
}

function HouseholdCard({ household, ctx }: { household: Household; ctx: Ctx }) {
  const dissolve = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/household:remove', {
          body: { household_id: household.id },
        })
      ),
  })
  const decisions = useGodAction({
    run: (hold: boolean) =>
      unwrap(
        api.POST('/api/actions/household:hold', {
          body: { household_id: household.id, fields: ['decisions'], hold },
        })
      ),
  })
  const busy = why(ctx.blocked, dissolve.isPending, decisions.isPending)
  const choosing = !household.held.includes('decisions')
  return (
    <MindCard
      title={household.name}
      icon={PURSE_ICON}
      wide
      hint='The household pools its members’ work and holdings, pays for food, upkeep, tithes and taxes, cares for its weak and makes choices when it can.'
    >
      <div className='grid min-w-0 grid-cols-2 gap-3 @lg/mind:grid-cols-4'>
        <KpiTile
          label='Wealth'
          value={household.wealth}
          icon={PURSE_ICON}
          tone='gold'
        />
        <KpiTile
          label='Income'
          value={household.income}
          icon={PURSE_ICON}
          tone='success'
        />
        <KpiTile
          label='Expenses'
          value={household.expenses}
          icon={PURSE_ICON}
          tone='warning'
        />
        <KpiTile
          label='Burden'
          value={household.burden}
          icon={CARE_ICON}
          tone={household.burden > 40 ? 'danger' : 'muted'}
          meter={{ value: household.burden, max: SPAN, label: 'Burden' }}
          harmful
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {household.social_class && (
          <Badge variant='outline'>
            {household.social_class.replaceAll('_', ' ')}
          </Badge>
        )}
        <Badge variant='outline'>{`${household.servants} servants`}</Badge>
        <Badge variant='outline'>{`${household.dependents} dependents`}</Badge>
        <Badge variant='outline'>{`Formed in epoch ${household.formed_epoch}`}</Badge>
        {household.last_decision_label && (
          <Badge variant='secondary'>
            {`${household.last_decision_label}, epoch ${household.decided_epoch ?? ''}`}
          </Badge>
        )}
        {household.debts.map((debt) => (
          <Badge key={debt.household_id} variant='destructive'>
            {`Owes ${debt.name} ${debt.amount}`}
          </Badge>
        ))}
      </div>
      <ItemRow
        icon={PURSE_ICON}
        tone='gold'
        title='Set the purse and the people kept'
        meta='Held values stop the household from reckoning them'
        editLabel='household values'
        editor={
          <AdjustStats
            id={`household-${household.id}`}
            inline
            groups={[
              {
                title: 'Purse',
                fields: [
                  {
                    key: 'wealth',
                    label: 'Wealth',
                    value: household.wealth,
                    min: 0,
                  },
                  {
                    key: 'income',
                    label: 'Income',
                    value: household.income,
                    min: 0,
                  },
                  {
                    key: 'expenses',
                    label: 'Expenses',
                    value: household.expenses,
                    min: 0,
                  },
                ],
              },
              {
                title: 'People',
                fields: [
                  {
                    key: 'servants',
                    label: 'Servants',
                    value: household.servants,
                    min: 0,
                  },
                  {
                    key: 'dependents',
                    label: 'Dependents',
                    value: household.dependents,
                    min: 0,
                  },
                  {
                    key: 'burden',
                    label: 'Burden',
                    value: household.burden,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
              {
                title: 'History',
                fields: [
                  {
                    key: 'formed_epoch',
                    label: 'Formed in epoch',
                    value: household.formed_epoch,
                    min: 0,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/household:edit', {
                  body: {
                    household_id: household.id,
                    [key]: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
        }
      />
      <DebtsCard household={household} ctx={ctx} />
      <Paged items={household.members} initial={6} noun={['member', 'members']}>
        {(member) => (
          <MemberRow
            key={member.mortal.id}
            member={member}
            household={household}
            ctx={ctx}
          />
        )}
      </Paged>
      <div className='flex min-w-0 flex-wrap justify-end gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => decisions.mutate(choosing)}
        >
          {choosing ? 'Hold its choices' : 'Let it choose again'}
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => dissolve.mutate()}
        >
          <Eraser />
          Dissolve the household
        </Button>
      </div>
      <DwellingCard
        household={household}
        dwelling={household.dwelling}
        ctx={ctx}
      />
    </MindCard>
  )
}

function AggregateRow({ row, ctx }: { row: Aggregate; ctx: Ctx }) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/household_aggregate:remove', {
          body: {
            community_id: ctx.view.node_id,
            social_class: row.social_class,
          },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  const look = DWELLINGS[row.dwelling_kind] ?? DWELLINGS.hut
  return (
    <ItemRow
      icon={look.icon}
      tone={look.tone}
      title={`${row.households} ${row.social_class_label.toLowerCase()} households`}
      meta={`${row.mean_size} to a ${row.dwelling_label.toLowerCase()}, quality ${row.quality}, wealth ${row.wealth}`}
      badges={
        row.held.length > 0 ? <Badge variant='outline'>Held</Badge> : undefined
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Strike the ${row.social_class_label.toLowerCase()} households`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`${row.social_class_label} households`}
      editor={
        <AdjustStats
          id={`aggregate-${ctx.view.node_id}-${row.social_class}`}
          inline
          groups={[
            {
              title: row.social_class_label,
              fields: [
                {
                  key: 'households',
                  label: 'Households',
                  value: row.households,
                  min: 0,
                },
                {
                  key: 'mean_size',
                  label: 'Members each',
                  value: row.mean_size,
                  min: 0,
                },
                {
                  key: 'quality',
                  label: 'Home quality',
                  value: row.quality,
                  min: 0,
                  max: SPAN,
                },
                { key: 'wealth', label: 'Wealth', value: row.wealth, min: 0 },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/household_aggregate:edit', {
                body: {
                  community_id: ctx.view.node_id,
                  social_class: row.social_class,
                  [key]: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    />
  )
}

function CommunityCards({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  return (
    <>
      <MindCard
        title='Named households'
        icon={HOME_ICON}
        wide
        hint='Every named mortal of this place belongs to one household; the richest come first.'
      >
        {view.households.length === 0 ? (
          <Muted variant='caption'>No named household lives here.</Muted>
        ) : (
          <Paged
            items={view.households}
            initial={4}
            noun={['household', 'households']}
          >
            {(household) => (
              <ItemRow
                key={household.id}
                icon={PURSE_ICON}
                tone='gold'
                title={household.name}
                meta={`Wealth ${household.wealth}, ${household.members.length} members${household.dwelling ? `, a ${household.dwelling.kind_label.toLowerCase()} of quality ${household.dwelling.effective_quality}` : ''}`}
                badges={
                  household.head ? (
                    <EntityLink kind='entity' id={String(household.head.id)}>
                      {household.head.name}
                    </EntityLink>
                  ) : undefined
                }
              />
            )}
          </Paged>
        )}
      </MindCard>
      <MindCard
        title='The common folk'
        icon={HOME_ICON}
        wide
        hint='Cohorts are made of anonymous households, reckoned each epoch by class from the people of this place.'
      >
        {view.aggregates.length === 0 ? (
          <Muted variant='caption'>No cohorts are counted here yet.</Muted>
        ) : (
          <Paged
            items={view.aggregates}
            initial={5}
            noun={['class', 'classes']}
          >
            {(row) => (
              <AggregateRow key={row.social_class} row={row} ctx={ctx} />
            )}
          </Paged>
        )}
      </MindCard>
    </>
  )
}

function NoHousehold({ ctx }: { ctx: Ctx }) {
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/household:found', {
          body: { head_id: ctx.view.node_id },
        })
      ),
  })
  const busy = why(ctx.blocked, found.isPending)
  return (
    <MindCard
      title='Household'
      icon={HOME_ICON}
      hint='The world houses every named mortal each epoch.'
    >
      <Text>Not yet part of any household.</Text>
      <Button
        size='sm'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => found.mutate()}
      >
        <Plus />
        Found a household for them
      </Button>
    </MindCard>
  )
}

export function HomeSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useHome(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section id='section-home' title='Household and home' icon={HOME_ICON}>
        <EmptyState
          icon={HOME_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  if (view.reason)
    return (
      <Section id='section-home' title='Household and home' icon={HOME_ICON}>
        <EmptyState
          icon={HOME_ICON}
          title='No household here'
          description={view.reason}
        />
      </Section>
    )
  const ctx: Ctx = { view, blocked: reason(), hold }
  return (
    <Section
      id='section-home'
      title='Household and home'
      description='The household a mortal belongs to, with its purse, roles, care and home; for settlements and peoples, their named households and the anonymous households of the common folk.'
      icon={HOME_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          {view.can_hold_household &&
            (view.household ? (
              <HouseholdCard household={view.household} ctx={ctx} />
            ) : (
              <NoHousehold ctx={ctx} />
            ))}
          {view.can_hold_aggregates && <CommunityCards ctx={ctx} />}
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Purses, roles, homes and counts you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
