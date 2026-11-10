import { useState } from 'react'
import { X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Paged, PagedList, StatBar } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodAction } from '@/features/pantheon/godAction'
import { ItemRow, MindCard, NodePicker } from '../mind/parts'
import { sentence } from '../realm/labels'
import { RefLink } from '../realm/parts'
import { type Affairs, type CourtPosition, type PositionView } from './api'
import { COURT_ICON, POSITIONS, spec } from './labels'

const SPAN = 100
const WORKING = 'Working on it.'
type Ctx = { view: Affairs; blocked: string | null; hold: boolean }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function PositionRow({
  position,
  row,
  ctx,
  realmId,
}: {
  position: CourtPosition
  row: PositionView | undefined
  ctx: Ctx
  realmId: number
}) {
  const [holder, setHolder] = useState<number | null>(row?.holder?.id ?? null)
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/position:set', {
          body: {
            polity_id: realmId,
            position,
            holder_id: holder,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/position:remove', {
          body: { polity_id: realmId, position },
        })
      ),
  })
  const busy = why(ctx.blocked, set.isPending, strike.isPending)
  const look = spec(POSITIONS, position)
  return (
    <ItemRow
      icon={look.icon}
      tone={row?.holder ? look.tone : 'muted'}
      title={look.label}
      meta={row?.holder ? <RefLink node={row.holder} /> : 'Vacant'}
      badges={row?.locked ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        row ? (
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Strike the ${look.label.toLowerCase()}`}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        ) : undefined
      }
      editLabel={`the ${look.label.toLowerCase()}`}
      editor={
        <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
          <NodePicker
            label='Holder'
            types={['mortal']}
            value={holder}
            onChange={setHolder}
            blocked={busy}
          />
          <Button
            size='sm'
            disabled={busy !== null || holder === null}
            disabledReason={
              busy ?? (holder === null ? 'Choose a mortal.' : undefined)
            }
            onClick={() => set.mutate()}
          >
            Appoint
          </Button>
        </div>
      }
    />
  )
}

export function CourtCard({ ctx, realmId }: { ctx: Ctx; realmId: number }) {
  const court = ctx.view.court
  const filled = new Map(ctx.view.positions.map((row) => [row.position, row]))
  const positions = Object.keys(POSITIONS) as CourtPosition[]
  const parts = Object.entries(court?.parts ?? {}).filter(
    ([, value]) => value > 0
  )
  return (
    <MindCard
      title='The court'
      icon={COURT_ICON}
      hint='Courtiers are those at the capital who know the ruler. Grandeur grows from the ruler’s dwelling, art at the capital, fine goods, courtiers and revels; it wins the ruler renown, warms other realms and draws talent. Each position works for the ruler: the steward saves coin, the champion wins honour, the physician heals, the tutor teaches the heir and the chronicler spreads the ruler’s fame.'
    >
      {court ? (
        <>
          <StatBar
            label='Grandeur'
            value={court.grandeur}
            max={SPAN}
            icon={COURT_ICON}
            tone='verdigris'
          />
          <Muted variant='caption'>{`${court.courtiers} courtiers attend the ruler.`}</Muted>
          {parts.length > 0 && (
            <PagedList
              items={parts}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap items-center gap-1.5'
              itemKey={([key]) => key}
            >
              {([key, value]) => (
                <Badge
                  key={key}
                  variant='secondary'
                >{`${sentence(key)} +${value}`}</Badge>
              )}
            </PagedList>
          )}
          {court.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
        </>
      ) : (
        <Muted variant='caption'>
          The court gathers at the next epoch; set its grandeur now if you wish.
        </Muted>
      )}
      <AdjustStats
        id={`court-${realmId}`}
        inline
        groups={[
          {
            title: 'Court',
            fields: [
              {
                key: 'grandeur',
                label: 'Grandeur',
                value: court?.grandeur ?? 0,
                min: 0,
                max: SPAN,
              },
              {
                key: 'courtiers',
                label: 'Courtiers',
                value: court?.courtiers ?? 0,
                min: 0,
                max: 10_000,
              },
            ],
          },
        ]}
        run={({ key, value }) =>
          unwrap(
            api.POST('/api/actions/court:edit', {
              body: { polity_id: realmId, [key]: value, hold: ctx.hold },
            })
          )
        }
      />
      <Label variant='overline'>Positions</Label>
      <Paged items={positions} initial={6} noun={['position', 'positions']}>
        {(position) => (
          <PositionRow
            key={position}
            position={position}
            row={filled.get(position)}
            ctx={ctx}
            realmId={realmId}
          />
        )}
      </Paged>
    </MindCard>
  )
}
