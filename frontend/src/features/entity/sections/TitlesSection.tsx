import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, KpiTile, Paged, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { NodeListEditor, RefLink } from '../realm/parts'
import {
  type TitleDetail,
  type TitleRank,
  type Titles,
  type TitleSummary,
  useTitles,
} from '../titles/api'
import {
  HISTORY_ICON,
  LANDS_ICON,
  RANKS,
  TENURE_ICON,
  TITLE_ICON,
} from '../titles/labels'

const SPAN = 100
const WORKING = 'Working on it.'
const HOLDERS = ['mortal', 'polity', 'faction', 'cult', 'settlement']

type Ctx = { view: Titles; blocked: string | null; hold: boolean }

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
  if (!node) return <span>no one</span>
  return <RefLink node={node} />
}

function SummaryRow({ item }: { item: TitleSummary }) {
  const look = RANKS[item.rank] ?? RANKS.county
  return (
    <ItemRow
      icon={look.icon}
      tone={item.dormant ? 'muted' : look.tone}
      title={<Ref node={item.title} />}
      meta={
        <>
          {`${item.rank_label}, ${item.lands} lands by right, `}
          {item.holder ? (
            <>
              {'held by '}
              <Ref node={item.holder} />
            </>
          ) : (
            'dormant'
          )}
        </>
      }
      badges={
        item.dormant ? <Badge variant='outline'>Dormant</Badge> : undefined
      }
    />
  )
}

function DetailCard({ detail, ctx }: { detail: TitleDetail; ctx: Ctx }) {
  const id = ctx.view.node_id
  const [holder, setHolder] = useState<number | null>(null)
  const [emblem, setEmblem] = useState('')
  const rank = useGodAction({
    run: (value: TitleRank) =>
      unwrap(
        api.POST('/api/actions/title:edit', {
          body: {
            title_id: id,
            rank: value,
            clear_liege: false,
            hold: ctx.hold,
          },
        })
      ),
  })
  const pass = useGodAction({
    run: ({ to, usurped }: { to: number | null; usurped: boolean }) =>
      unwrap(
        api.POST('/api/actions/title:grant', {
          body: { title_id: id, holder_id: to, usurped, hold: ctx.hold },
        })
      ),
    success: () => {
      setHolder(null)
      return 'Done'
    },
  })
  const arms = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/title:edit', {
          body: {
            title_id: id,
            emblem: emblem.trim(),
            clear_liege: false,
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setEmblem('')
      return 'Arms set'
    },
  })
  const fate = useGodAction({
    run: (destroyed: boolean) =>
      destroyed
        ? unwrap(
            api.POST('/api/actions/title:restore', {
              body: {
                title_id: id,
                holder_id: holder,
                usurped: false,
                hold: ctx.hold,
              },
            })
          )
        : unwrap(
            api.POST('/api/actions/title:destroy', { body: { title_id: id } })
          ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/title:edit', {
          body: { title_id: id, clear_liege: true, hold: ctx.hold },
        })
      ),
  })
  const freeze = useGodAction({
    run: (hold: boolean) =>
      unwrap(
        api.POST('/api/actions/title:hold', {
          body: { title_id: id, clear_liege: false, hold },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(api.POST('/api/actions/title:remove', { body: { title_id: id } })),
  })
  const crown = useGodAction({
    run: (regalia: number[]) =>
      unwrap(
        api.POST('/api/actions/title:edit', {
          body: { title_id: id, regalia, clear_liege: false, hold: ctx.hold },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    rank.isPending,
    crown.isPending,
    pass.isPending,
    arms.isPending,
    fate.isPending,
    release.isPending,
    freeze.isPending,
    strike.isPending
  )
  const look = RANKS[detail.rank] ?? RANKS.county
  const frozen = detail.held.length > 0
  const destroyed = detail.destroyed_epoch !== null
  return (
    <MindCard
      title={detail.rank_label}
      icon={look.icon}
      wide
      hint='A title rules its de jure lands by right; the ruler of a realm is the holder of its primary title. Lands held long under another title drift into it, a realm holding most of a higher title’s lands and its capital may usurp it, and dormant titles can be restored.'
    >
      <div className='grid min-w-0 grid-cols-2 gap-3 @lg/mind:grid-cols-4'>
        <KpiTile
          label='Prestige'
          value={detail.prestige}
          icon={look.icon}
          tone='gold'
        />
        <KpiTile
          label='Lands by right'
          value={detail.lands.length}
          icon={LANDS_ICON}
          tone='info'
        />
        <KpiTile
          label='Lesser titles'
          value={detail.vassal_titles.length}
          icon={TITLE_ICON}
          tone='verdigris'
        />
        <KpiTile
          label='Holders'
          value={detail.holders.length}
          icon={HISTORY_ICON}
          tone='muted'
        />
      </div>
      <ItemRow
        icon={look.icon}
        tone={destroyed ? 'muted' : look.tone}
        title={
          <>
            {'Held by '}
            <Ref node={detail.holder} />
          </>
        }
        meta={
          <>
            {detail.polity && (
              <>
                {'Primary title of '}
                <Ref node={detail.polity} />
                {'; '}
              </>
            )}
            {detail.liege && (
              <>
                {'under '}
                <Ref node={detail.liege} />
                {'; '}
              </>
            )}
            {detail.succession_law && (
              <>
                {'passed on by '}
                <Ref node={detail.succession_law} />
                {'; '}
              </>
            )}
            {detail.capital && (
              <>
                {'seat at '}
                <Ref node={detail.capital} />
                {'; '}
              </>
            )}
            {`arms: ${detail.emblem ?? 'none'}; since epoch ${detail.created_epoch}`}
            {detail.regalia.length > 0 &&
              `; regalia: ${detail.regalia.map((item) => item.name).join(', ')}`}
          </>
        }
        badges={
          <>
            {destroyed && <Badge variant='destructive'>Destroyed</Badge>}
            {frozen && <Badge variant='outline'>Held</Badge>}
          </>
        }
        actions={
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Strike the title'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        }
        editLabel='the title'
        editor={
          <div className='flex min-w-0 flex-col gap-3'>
            <MindPicker
              label='Rank'
              value={detail.rank}
              table={table(ctx.view.ranks)}
              blocked={busy}
              onPick={(value) => rank.mutate(value as TitleRank)}
            />
            <AdjustStats
              id={`title-${id}`}
              inline
              groups={[
                {
                  title: 'Title',
                  fields: [
                    {
                      key: 'prestige',
                      label: 'Prestige',
                      value: detail.prestige,
                      min: 0,
                      max: SPAN,
                    },
                  ],
                },
              ]}
              run={({ value }) =>
                unwrap(
                  api.POST('/api/actions/title:edit', {
                    body: {
                      title_id: id,
                      prestige: value,
                      clear_liege: false,
                      hold: ctx.hold,
                    },
                  })
                )
              }
            />
            <NodeListEditor
              label='Regalia'
              types={['item']}
              nodes={detail.regalia}
              blocked={busy}
              onChange={(ids) => crown.mutate(ids)}
            />
            <div className='flex min-w-0 flex-wrap justify-end gap-2'>
              {detail.liege && (
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => release.mutate()}
                >
                  Free it from its liege
                </Button>
              )}
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => fate.mutate(destroyed)}
              >
                {destroyed ? 'Restore it' : 'Destroy it'}
              </Button>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => freeze.mutate(!frozen)}
              >
                {frozen ? 'Let it move again' : 'Hold it against the world'}
              </Button>
            </div>
          </div>
        }
      />
      <AddBar
        title='Pass it on'
        action={
          <div className='flex flex-wrap justify-end gap-2'>
            <Button
              size='sm'
              disabled={busy !== null || holder === null}
              disabledReason={
                busy ?? (holder === null ? 'Choose a holder first.' : undefined)
              }
              onClick={() => pass.mutate({ to: holder, usurped: false })}
            >
              Grant
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || holder === null}
              disabledReason={
                busy ?? (holder === null ? 'Choose who seizes it.' : undefined)
              }
              onClick={() => pass.mutate({ to: holder, usurped: true })}
            >
              Usurp
            </Button>
            <Button
              size='sm'
              variant='ghost'
              disabled={busy !== null || !detail.holder}
              disabledReason={
                busy ?? (detail.holder ? undefined : 'It is already dormant.')
              }
              onClick={() => pass.mutate({ to: null, usurped: false })}
            >
              Leave it dormant
            </Button>
          </div>
        }
      >
        <NodePicker
          label='To'
          types={HOLDERS}
          value={holder}
          onChange={setHolder}
          blocked={busy}
        />
      </AddBar>
      <AddBar
        title='Blazon new arms'
        action={
          <Button
            size='sm'
            disabled={busy !== null || !emblem.trim()}
            disabledReason={
              busy ?? (emblem.trim() ? undefined : 'Describe the arms first.')
            }
            onClick={() => arms.mutate()}
          >
            Set
          </Button>
        }
      >
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`arms-${id}`}>
            Arms
          </Label>
          <Input
            id={`arms-${id}`}
            value={emblem}
            maxLength={60}
            disabled={busy !== null}
            onChange={(event) => setEmblem(event.target.value)}
          />
        </div>
      </AddBar>
      {detail.vassal_titles.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Lesser titles beneath it</Label>
          <Paged
            items={detail.vassal_titles}
            initial={4}
            noun={['title', 'titles']}
          >
            {(item) => <SummaryRow key={item.title.id} item={item} />}
          </Paged>
        </div>
      )}
    </MindCard>
  )
}

function LandsCard({ detail, ctx }: { detail: TitleDetail; ctx: Ctx }) {
  const id = ctx.view.node_id
  const [land, setLand] = useState<number | null>(null)
  const add = useGodAction({
    run: (memberId: number) =>
      unwrap(
        api.POST('/api/actions/de_jure:set', {
          body: { title_id: id, member_id: memberId, hold: ctx.hold },
        })
      ),
    success: () => {
      setLand(null)
      return 'Added'
    },
  })
  const drop = useGodAction({
    run: (memberId: number) =>
      unwrap(
        api.POST('/api/actions/de_jure:remove', {
          body: { title_id: id, member_id: memberId },
        })
      ),
  })
  const busy = why(ctx.blocked, add.isPending, drop.isPending)
  return (
    <MindCard
      title='Lands by right'
      icon={LANDS_ICON}
      hint='The de jure lands of a title. The map’s de jure layer colours every land by the title it belongs to, deeper where another realm holds it in fact.'
    >
      {detail.lands.length === 0 ? (
        <Muted variant='caption'>No land belongs to it by right.</Muted>
      ) : (
        <Paged items={detail.lands} initial={6} noun={['land', 'lands']}>
          {(node) => (
            <div
              key={node.id}
              className='flex min-w-0 items-center justify-between gap-2'
            >
              <Text truncate>
                <Ref node={node} />
              </Text>
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label={`Strike ${node.name} from the title`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => drop.mutate(node.id)}
              >
                <X />
              </Button>
            </div>
          )}
        </Paged>
      )}
      {detail.drift.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Drifting in</Label>
          {detail.drift.map((entry) => (
            <Muted key={entry.land?.id} variant='caption'>
              {`${entry.land?.name ?? 'A land'}: ${entry.epochs} epochs under this title`}
            </Muted>
          ))}
        </div>
      )}
      <AddBar
        title='Claim a land by right'
        action={
          <Button
            size='sm'
            disabled={busy !== null || land === null}
            disabledReason={
              busy ?? (land === null ? 'Choose a land first.' : undefined)
            }
            onClick={() => land !== null && add.mutate(land)}
          >
            <Plus />
            Add
          </Button>
        }
      >
        <NodePicker
          label='Land'
          types={['region', 'title']}
          value={land}
          onChange={setLand}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

function HistoryCard({ detail }: { detail: TitleDetail }) {
  return (
    <MindCard title='Holders through time' icon={HISTORY_ICON}>
      {detail.holders.length === 0 ? (
        <Muted variant='caption'>No one has held it yet.</Muted>
      ) : (
        <Paged
          items={[...detail.holders].reverse()}
          initial={6}
          noun={['holder', 'holders']}
        >
          {(entry) => (
            <ItemRow
              key={`${entry.holder?.id}-${entry.since_epoch}`}
              icon={TENURE_ICON}
              tone={entry.until_epoch === null ? 'gold' : 'muted'}
              title={<Ref node={entry.holder} />}
              meta={`${entry.tenure_label}, epoch ${entry.since_epoch}${entry.until_epoch !== null ? ` to ${entry.until_epoch}` : ' to now'}`}
            />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

function HoldingsCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [name, setName] = useState('')
  const [rank, setRank] = useState('county')
  const make = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/title:create', {
          body: {
            rank: rank as TitleRank,
            name: name.trim(),
            holder_id: view.node_id,
            lands: [],
          },
        })
      ),
    success: () => {
      setName('')
      return 'Created'
    },
  })
  const busy = why(ctx.blocked, make.isPending)
  const empty =
    view.titles_held.length === 0 &&
    view.realm_titles.length === 0 &&
    view.seat_titles.length === 0 &&
    view.claims.length === 0 &&
    view.de_jure_chain.length === 0
  return (
    <MindCard
      title='Titles'
      icon={TITLE_ICON}
      wide
      hint='The titles it holds or that its realm is ruled by, the seat it raised for its leader, the titles it has a claim on, and the chain of titles its land belongs to by right.'
    >
      {empty && (
        <Muted variant='caption'>Holds no title and is held by none.</Muted>
      )}
      {view.titles_held.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Held</Label>
          <Paged
            items={view.titles_held}
            initial={4}
            noun={['title', 'titles']}
          >
            {(item) => <SummaryRow key={item.title.id} item={item} />}
          </Paged>
        </div>
      )}
      {view.realm_titles.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Titles of this realm</Label>
          <Paged
            items={view.realm_titles}
            initial={4}
            noun={['title', 'titles']}
          >
            {(item) => <SummaryRow key={item.title.id} item={item} />}
          </Paged>
        </div>
      )}
      {view.seat_titles.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Seat of its leader</Label>
          {view.seat_titles.map((item) => (
            <SummaryRow key={item.title.id} item={item} />
          ))}
        </div>
      )}
      {view.claims.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Claims</Label>
          {view.claims.map((claim) => (
            <Muted key={claim.title.id} variant='caption'>
              <Ref node={claim.title} />
              {`, strength ${claim.strength}, since epoch ${claim.since_epoch}`}
            </Muted>
          ))}
        </div>
      )}
      {view.de_jure_chain.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Belongs by right to</Label>
          {view.de_jure_chain.map((item) => (
            <SummaryRow key={item.title.id} item={item} />
          ))}
        </div>
      )}
      <AddBar
        title='Create a title for it'
        action={
          <Button
            size='sm'
            disabled={busy !== null || !name.trim()}
            disabledReason={
              busy ?? (name.trim() ? undefined : 'Name the title first.')
            }
            onClick={() => make.mutate()}
          >
            <Plus />
            Create
          </Button>
        }
      >
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`title-name-${view.node_id}`}>
            Name
          </Label>
          <Input
            id={`title-name-${view.node_id}`}
            value={name}
            maxLength={200}
            disabled={busy !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <MindPicker
          label='Rank'
          value={rank}
          table={table(view.ranks)}
          blocked={busy}
          onPick={setRank}
        />
      </AddBar>
    </MindCard>
  )
}

export function TitlesSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useTitles(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section id='section-titles' title='Titles' icon={TITLE_ICON}>
        <EmptyState
          icon={TITLE_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold }
  return (
    <Section
      id='section-titles'
      title='Titles'
      description='For a title: its rank, holder, lands by right, lesser titles and holders through time. For anything else: the titles it holds or claims and the titles its land belongs to.'
      icon={TITLE_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          {view.detail && <DetailCard detail={view.detail} ctx={ctx} />}
          {view.detail && <LandsCard detail={view.detail} ctx={ctx} />}
          {view.detail && <HistoryCard detail={view.detail} />}
          <HoldingsCard ctx={ctx} />
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Ranks, holders, lands, arms and prestige you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
