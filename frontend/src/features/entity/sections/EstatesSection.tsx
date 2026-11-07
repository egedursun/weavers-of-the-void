import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { EmptyState, KpiTile, Paged, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type Company,
  type Estate,
  type EstatePrivilege,
  type Estates,
  type Guild,
  type HolyOrder,
  type Movement,
  type MovementCause,
  type SocialClass,
  type Technique,
  useEstates,
} from '../estates/api'
import {
  COMPANY_ICON,
  ESTATES_ICON,
  GUILD_ICON,
  MOVEMENT_ICON,
  ORDER_ICON,
  PARTY_ICON,
  PRIVILEGE_ICONS,
  SHARE_ICON,
  loyaltyTone,
} from '../estates/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { RefLink } from '../realm/parts'

const SPAN = 100
const WORKING = 'Working on it.'
const HOLDERS = ['mortal', 'polity', 'house', 'faction', 'settlement']

type Ctx = { view: Estates; blocked: string | null; hold: boolean }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function Ref({
  node,
}: {
  node: { id: number; kind: string; name: string } | null | undefined
}) {
  if (!node) return <span>none</span>
  return <RefLink node={node} />
}

function EstateRow({ row, ctx }: { row: Estate; ctx: Ctx }) {
  const [privilege, setPrivilege] = useState('')
  const toggle = useGodAction({
    run: ({ which, grant }: { which: EstatePrivilege; grant: boolean }) =>
      unwrap(
        api.POST('/api/actions/estate:privilege', {
          body: {
            estate_id: row.estate.id,
            privilege: which,
            grant,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setPrivilege('')
      return 'Done'
    },
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/estate:remove', {
          body: { estate_id: row.estate.id },
        })
      ),
  })
  const busy = why(ctx.blocked, toggle.isPending, strike.isPending)
  return (
    <ItemRow
      icon={ESTATES_ICON}
      tone={loyaltyTone(row.loyalty)}
      title={<Ref node={row.estate} />}
      meta={`${row.class_label}: loyalty ${row.loyalty}, influence ${row.influence}`}
      badges={
        <>
          {row.privileges.map((item) => (
            <Badge key={item} variant='secondary'>
              {PRIVILEGE_ICONS[item]?.label ?? item}
            </Badge>
          ))}
          {row.held.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Strike the estate'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the estate'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`estate-${row.estate.id}`}
            inline
            groups={[
              {
                title: 'Estate',
                fields: [
                  {
                    key: 'loyalty',
                    label: 'Loyalty',
                    value: row.loyalty,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'influence',
                    label: 'Influence',
                    value: row.influence,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/estate:edit', {
                  body: {
                    estate_id: row.estate.id,
                    [key]: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          {row.privileges.map((item) => (
            <div
              key={item}
              className='flex min-w-0 items-center justify-between gap-2'
            >
              <Text truncate>{PRIVILEGE_ICONS[item]?.label ?? item}</Text>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => toggle.mutate({ which: item, grant: false })}
              >
                Take back
              </Button>
            </div>
          ))}
          <AddBar
            title='Grant a privilege'
            action={
              <Button
                size='sm'
                disabled={busy !== null || !privilege}
                disabledReason={
                  busy ?? (privilege ? undefined : 'Choose a privilege.')
                }
                onClick={() =>
                  toggle.mutate({
                    which: privilege as EstatePrivilege,
                    grant: true,
                  })
                }
              >
                Grant
              </Button>
            }
          >
            <MindPicker
              label='Privilege'
              value={privilege}
              table={table(ctx.view.privileges)}
              blocked={busy}
              onPick={setPrivilege}
            />
          </AddBar>
        </div>
      }
    >
      <Progress
        value={row.loyalty}
        size='sm'
        tone={row.loyalty >= 50 ? 'success' : 'warning'}
        aria-label={`Loyalty ${row.loyalty}`}
      />
    </ItemRow>
  )
}

type Holding = {
  holder: { id: number; kind: string; name: string }
  share: number
  held: boolean
}

type Backing = {
  community: { id: number; kind: string; name: string }
  share: number
  held: boolean
}

function SupportRow({
  movementId,
  item,
  ctx,
}: {
  movementId: number
  item: Backing
  ctx: Ctx
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/movement:support_remove', {
          body: { movement_id: movementId, community_id: item.community.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <ItemRow
      icon={MOVEMENT_ICON}
      tone={item.share >= 50 ? 'warning' : 'muted'}
      title={<Ref node={item.community} />}
      meta={`${item.share}% stand behind it`}
      badges={item.held ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Wipe the support of ${item.community.name}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`support in ${item.community.name}`}
      editor={
        <AdjustStats
          id={`support-${movementId}-${item.community.id}`}
          inline
          groups={[
            {
              title: 'Support',
              fields: [
                {
                  key: 'share',
                  label: 'Share',
                  value: item.share,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/movement:support', {
                body: {
                  movement_id: movementId,
                  community_id: item.community.id,
                  share: value,
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

function ShareRow({
  companyId,
  item,
  ctx,
}: {
  companyId: number
  item: Holding
  ctx: Ctx
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/company:share_remove', {
          body: { company_id: companyId, holder_id: item.holder.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <div className='flex min-w-0 items-center justify-between gap-2'>
      <Text truncate>
        <Ref node={item.holder} />
      </Text>
      <div className='flex shrink-0 items-center gap-1'>
        <Muted variant='caption'>{`${item.share}%`}</Muted>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Strike the share of ${item.holder.name}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      </div>
    </div>
  )
}

function MovementRow({ row, ctx }: { row: Movement; ctx: Ctx }) {
  const party = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/movement:edit', {
          body: {
            movement_id: row.movement.id,
            is_party: !row.is_party,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/movement:remove', {
          body: { movement_id: row.movement.id },
        })
      ),
  })
  const busy = why(ctx.blocked, party.isPending, strike.isPending)
  return (
    <ItemRow
      icon={row.is_party ? PARTY_ICON : MOVEMENT_ICON}
      tone={row.support >= 50 ? 'danger' : 'info'}
      title={<Ref node={row.movement} />}
      meta={`${row.cause_label}, ${row.support}% behind it, since epoch ${row.founded_epoch}`}
      badges={
        <>
          {row.is_party && <Badge variant='secondary'>Party</Badge>}
          {row.held.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Strike the movement'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the movement'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`movement-${row.movement.id}`}
            inline
            groups={[
              {
                title: 'Movement',
                fields: [
                  {
                    key: 'support',
                    label: 'Support',
                    value: row.support,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/movement:edit', {
                  body: {
                    movement_id: row.movement.id,
                    support: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          <Paged
            items={row.communities}
            initial={5}
            noun={['community', 'communities']}
          >
            {(item) => (
              <SupportRow
                key={item.community.id}
                movementId={row.movement.id}
                item={item}
                ctx={ctx}
              />
            )}
          </Paged>
          <div className='flex justify-end'>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => party.mutate()}
            >
              {row.is_party ? 'Make it a movement again' : 'Make it a party'}
            </Button>
          </div>
        </div>
      }
    >
      <Progress
        value={row.support}
        size='sm'
        tone={row.support >= 50 ? 'warning' : 'success'}
        aria-label={`Support ${row.support}`}
      />
    </ItemRow>
  )
}

function CompanyRow({ row, ctx }: { row: Company; ctx: Ctx }) {
  const [holder, setHolder] = useState<number | null>(null)
  const share = useGodAction({
    run: (holderId: number) =>
      unwrap(
        api.POST('/api/actions/company:share', {
          body: {
            company_id: row.company.id,
            holder_id: holderId,
            share: 10,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setHolder(null)
      return 'Share given'
    },
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/company:remove', {
          body: { company_id: row.company.id },
        })
      ),
  })
  const busy = why(ctx.blocked, share.isPending, strike.isPending)
  return (
    <ItemRow
      icon={COMPANY_ICON}
      tone='gold'
      title={<Ref node={row.company} />}
      meta={
        <>
          {row.route && (
            <>
              {'Holds '}
              <Ref node={row.route} />
              {'; '}
            </>
          )}
          {row.region && (
            <>
              {'rules '}
              <Ref node={row.region} />
              {'; '}
            </>
          )}
          {`worth ${row.value}, pays ${row.dividend_pct}% to ${row.shares.length} shareholders`}
        </>
      }
      badges={
        row.held.length > 0 ? <Badge variant='outline'>Held</Badge> : undefined
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Strike the charter'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the company'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`company-${row.company.id}`}
            inline
            groups={[
              {
                title: 'Company',
                fields: [
                  {
                    key: 'dividend_pct',
                    label: 'Dividend',
                    value: row.dividend_pct,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/company:edit', {
                  body: {
                    company_id: row.company.id,
                    dividend_pct: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          {row.shares.map((item) => (
            <ShareRow
              key={item.holder.id}
              companyId={row.company.id}
              item={item}
              ctx={ctx}
            />
          ))}
          <AddBar
            title='Give a share'
            action={
              <Button
                size='sm'
                disabled={busy !== null || holder === null}
                disabledReason={
                  busy ??
                  (holder === null ? 'Choose a shareholder.' : undefined)
                }
                onClick={() => holder !== null && share.mutate(holder)}
              >
                Give 10%
              </Button>
            }
          >
            <NodePicker
              label='Shareholder'
              types={HOLDERS}
              value={holder}
              onChange={setHolder}
              blocked={busy}
            />
          </AddBar>
        </div>
      }
    />
  )
}

function OrderRow({ row, ctx }: { row: HolyOrder; ctx: Ctx }) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/holy_order:remove', {
          body: { order_id: row.order.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  return (
    <ItemRow
      icon={ORDER_ICON}
      tone='verdigris'
      title={<Ref node={row.order} />}
      meta={
        <>
          {'Sworn to '}
          <Ref node={row.cult} />
          {row.fortress && (
            <>
              {', holding '}
              <Ref node={row.fortress} />
            </>
          )}
          {`, fed ${row.tithe_share}% of the tithes`}
        </>
      }
      badges={
        row.held.length > 0 ? <Badge variant='outline'>Held</Badge> : undefined
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Strike the vows'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the order'
      editor={
        <AdjustStats
          id={`order-${row.order.id}`}
          inline
          groups={[
            {
              title: 'Holy order',
              fields: [
                {
                  key: 'tithe_share',
                  label: 'Share of tithes',
                  value: row.tithe_share,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/holy_order:edit', {
                body: {
                  order_id: row.order.id,
                  tithe_share: value,
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

function GuildCard({ guild, ctx }: { guild: Guild; ctx: Ctx }) {
  const [technique, setTechnique] = useState('')
  const keep = useGodAction({
    run: ({ which, keepIt }: { which: Technique; keepIt: boolean }) =>
      unwrap(
        api.POST('/api/actions/guild:secret', {
          body: { guild_id: guild.guild.id, technique: which, keep: keepIt },
        })
      ),
    success: () => {
      setTechnique('')
      return 'Done'
    },
  })
  const busy = why(ctx.blocked, keep.isPending)
  const open = guild.known.filter((item) => !guild.secrets.includes(item))
  return (
    <MindCard
      title='Guild'
      icon={GUILD_ICON}
      hint='Guild members rise from apprentice to grandmaster by their craft; the guild keeps craft secrets from other towns, takes apprentices in and its standards raise the quality of its town’s works.'
    >
      <Text weight='semibold'>
        <Ref node={guild.guild} />
      </Text>
      <Paged items={guild.members} initial={5} noun={['member', 'members']}>
        {(item) => (
          <div
            key={item.member.id}
            className='flex min-w-0 items-center justify-between gap-2'
          >
            <Text truncate>
              <Ref node={item.member} />
            </Text>
            <Badge variant='outline'>{item.rank_label}</Badge>
          </div>
        )}
      </Paged>
      {guild.secrets.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Secrets</Label>
          {guild.secrets.map((item) => (
            <div
              key={item}
              className='flex min-w-0 items-center justify-between gap-2'
            >
              <Text truncate>{item.replaceAll('_', ' ')}</Text>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => keep.mutate({ which: item, keepIt: false })}
              >
                Let it out
              </Button>
            </div>
          ))}
        </div>
      )}
      <AddBar
        title='Keep a craft secret'
        action={
          <Button
            size='sm'
            disabled={busy !== null || !technique}
            disabledReason={
              busy ??
              (technique
                ? undefined
                : open.length
                  ? 'Choose a technique.'
                  : 'Its town knows no open technique.')
            }
            onClick={() =>
              keep.mutate({ which: technique as Technique, keepIt: true })
            }
          >
            Keep
          </Button>
        }
      >
        <MindPicker
          label='Technique'
          value={technique}
          table={Object.fromEntries(
            open.map((item) => [item, item.replaceAll('_', ' ')])
          )}
          blocked={busy}
          onPick={setTechnique}
        />
      </AddBar>
    </MindCard>
  )
}

function RealmCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [social, setSocial] = useState('')
  const [cause, setCause] = useState('')
  const [home, setHome] = useState<number | null>(null)
  const gather = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/estate:found', {
          body: { realm_id: view.node_id, social_class: social as SocialClass },
        })
      ),
    success: () => {
      setSocial('')
      return 'Gathered'
    },
  })
  const raise = useGodAction({
    run: (homeId: number) =>
      unwrap(
        api.POST('/api/actions/movement:found', {
          body: {
            realm_id: view.node_id,
            cause: cause as MovementCause,
            home_id: homeId,
          },
        })
      ),
    success: () => {
      setCause('')
      setHome(null)
      return 'Raised'
    },
  })
  const busy = why(ctx.blocked, gather.isPending, raise.isPending)
  return (
    <MindCard
      title='Estates and movements'
      icon={ESTATES_ICON}
      wide
      hint='Each class gathers as an estate with a loyalty and a share of the realm’s power; privileges buy loyalty at a cost in taxes or power. Movements grow from pressures, protest, become parties where there is a council or assembly, and rise where there is none.'
    >
      {view.estates.length === 0 && view.movements.length === 0 && (
        <Muted variant='caption'>No estate or movement stirs here.</Muted>
      )}
      {view.estates.length > 0 && (
        <Paged items={view.estates} initial={4} noun={['estate', 'estates']}>
          {(row) => <EstateRow key={row.estate.id} row={row} ctx={ctx} />}
        </Paged>
      )}
      {view.movements.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Movements and parties</Label>
          <Paged
            items={view.movements}
            initial={4}
            noun={['movement', 'movements']}
          >
            {(row) => <MovementRow key={row.movement.id} row={row} ctx={ctx} />}
          </Paged>
        </div>
      )}
      <AddBar
        title='Gather an estate'
        action={
          <Button
            size='sm'
            disabled={busy !== null || !social}
            disabledReason={busy ?? (social ? undefined : 'Choose a class.')}
            onClick={() => gather.mutate()}
          >
            <Plus />
            Gather
          </Button>
        }
      >
        <MindPicker
          label='Class'
          value={social}
          table={table(view.classes)}
          blocked={busy}
          onPick={setSocial}
        />
      </AddBar>
      <AddBar
        title='Raise a movement'
        action={
          <Button
            size='sm'
            disabled={busy !== null || !cause || home === null}
            disabledReason={
              busy ??
              (!cause
                ? 'Choose a cause.'
                : home === null
                  ? 'Choose where it rises.'
                  : undefined)
            }
            onClick={() => home !== null && raise.mutate(home)}
          >
            <Plus />
            Raise
          </Button>
        }
      >
        <MindPicker
          label='Cause'
          value={cause}
          table={table(view.causes)}
          blocked={busy}
          onPick={setCause}
        />
        <NodePicker
          label='Rising in'
          types={['settlement', 'people']}
          value={home}
          onChange={setHome}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

export function EstatesSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useEstates(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-estates'
        title='Estates and movements'
        icon={ESTATES_ICON}
      >
        <EmptyState
          icon={ESTATES_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold }
  const quiet =
    !view.can_found &&
    view.holdings.length === 0 &&
    view.companies.length === 0 &&
    view.orders.length === 0 &&
    view.guilds.length === 0 &&
    view.movements.length === 0 &&
    view.estates.length === 0
  return (
    <Section
      id='section-estates'
      title='Estates and movements'
      description='Estates of the realm with their loyalty and privileges, movements and parties with their support, chartered companies and their shareholders, holy orders, and guilds with their ranks and craft secrets.'
      icon={ESTATES_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
          <KpiTile
            label='Estates'
            value={view.estates.length}
            icon={ESTATES_ICON}
            tone='gold'
          />
          <KpiTile
            label='Movements'
            value={view.movements.length}
            icon={MOVEMENT_ICON}
            tone='info'
          />
          <KpiTile
            label='Companies'
            value={view.companies.length}
            icon={COMPANY_ICON}
            tone='warning'
          />
          <KpiTile
            label='Shares held'
            value={view.holdings.length}
            icon={SHARE_ICON}
            tone='verdigris'
          />
        </div>
        {quiet ? (
          <EmptyState
            icon={ESTATES_ICON}
            title='Nothing here'
            description={
              view.reason ??
              'It holds no estate, movement, company, order or guild.'
            }
          />
        ) : (
          <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
            {view.can_found && <RealmCard ctx={ctx} />}
            {view.companies.length > 0 && (
              <MindCard
                title='Chartered companies'
                icon={COMPANY_ICON}
                hint='A company holds the trade of a route abroad, pays dividends to its shareholders, may seize land at the route’s far end and collapses when its coffers run dry.'
              >
                <Paged
                  items={view.companies}
                  initial={3}
                  noun={['company', 'companies']}
                >
                  {(row) => (
                    <CompanyRow key={row.company.id} row={row} ctx={ctx} />
                  )}
                </Paged>
              </MindCard>
            )}
            {view.orders.length > 0 && (
              <MindCard
                title='Holy orders'
                icon={ORDER_ICON}
                hint='Warriors sworn to a faith, fed by its tithes and holding a border town.'
              >
                <Paged
                  items={view.orders}
                  initial={3}
                  noun={['order', 'orders']}
                >
                  {(row) => <OrderRow key={row.order.id} row={row} ctx={ctx} />}
                </Paged>
              </MindCard>
            )}
            {view.guilds.map((guild) => (
              <GuildCard key={guild.guild.id} guild={guild} ctx={ctx} />
            ))}
            {(view.holdings.length > 0 || view.guild_rank) && (
              <MindCard title='Stakes and standing' icon={SHARE_ICON}>
                {view.guild_rank && (
                  <Text>{`A ${view.guild_rank.toLowerCase()} of a guild.`}</Text>
                )}
                {view.holdings.map((item) => (
                  <div
                    key={item.holder.id}
                    className='flex min-w-0 items-center justify-between gap-2'
                  >
                    <Text truncate>
                      <Ref node={item.holder} />
                    </Text>
                    <Muted variant='caption'>{`${item.share}% held`}</Muted>
                  </div>
                ))}
              </MindCard>
            )}
          </div>
        )}
        <ControlPanel
          title='Hold what you set'
          note='Loyalties, privileges, support, shares and secrets you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
