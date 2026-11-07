import { useState } from 'react'
import { Flag, Handshake, Lock, Megaphone, Scale, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, Medallion, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { type WarRoom as Room } from './api'
import { CASUS_BELLI, PERCENT, SIDE, busyOf, named, whole } from './labels'
import { NumberField, Plain, Tag } from './parts'

type SideRow = Room['weariness'][number]

const JUSTIFIED = { label: 'Justified', icon: Scale, tone: 'success' as const }
const UNJUSTIFIED = {
  label: 'Unjustified',
  icon: Scale,
  tone: 'danger' as const,
}

function supportTone(support: number) {
  if (support >= 60) return 'success' as const
  if (support >= 35) return 'warning' as const
  return 'destructive' as const
}

export function SupportLine({ row }: { row: SideRow }) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <StatBar
        label='War support'
        icon={Megaphone}
        value={row.support}
        max={PERCENT}
        tone={supportTone(row.support)}
      />
      <Muted as='span' variant='caption'>
        {`Could claim demands worth ${row.budget} if it won now`}
      </Muted>
    </div>
  )
}

export function WarCause({ room }: { room: Room }) {
  const cause = room.casus_belli
  const kind = cause ? named(CASUS_BELLI, cause.kind) : null
  return (
    <div
      data-surface='WarCause'
      className='flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={kind?.icon ?? Flag}
          tone={room.justified ? (kind?.tone ?? 'gold') : 'danger'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label variant='overline'>Casus belli</Label>
          <Text as='span' weight='medium' truncate>
            {kind ? kind.label : 'None; a war of conquest'}
          </Text>
        </div>
        <Tag item={room.justified ? JUSTIFIED : UNJUSTIFIED} />
      </div>
      {cause ? (
        <>
          <StatBar
            label='Justification'
            icon={Scale}
            value={cause.justification}
            max={PERCENT}
            tone={room.justified ? 'success' : 'warning'}
          />
          <Muted as='span' variant='caption'>
            {cause.holder && cause.target ? (
              <>
                <EntityLink kind='entity' id={String(cause.holder.id)}>
                  {cause.holder.name}
                </EntityLink>
                {' held it against '}
                <EntityLink kind='entity' id={String(cause.target.id)}>
                  {cause.target.name}
                </EntityLink>
                {` since epoch ${cause.since_epoch}.`}
              </>
            ) : (
              `Held since epoch ${cause.since_epoch}.`
            )}
          </Muted>
        </>
      ) : (
        <Muted as='span' variant='caption'>
          {room.justified
            ? 'It needed none: a rising or a defence against one.'
            : 'Its ruler earned tyranny, other realms took it as a threat and its own people back it less.'}
        </Muted>
      )}
    </div>
  )
}

function SideConduct({
  warId,
  row,
  blocked,
}: {
  warId: number
  row: SideRow
  blocked: string | null
}) {
  const [support, setSupport] = useState(String(row.support))
  const [weariness, setWeariness] = useState(String(row.weariness))
  const save = useGodAction<boolean>({
    run: (hold) =>
      unwrap(
        api.POST('/api/actions/war:edit_side', {
          body: {
            war_id: warId,
            side_id: row.entity?.id ?? 0,
            values: hold
              ? {
                  support: whole(support, PERCENT),
                  weariness: whole(weariness, PERCENT),
                }
              : {},
            release: hold ? [] : ['support', 'weariness'],
          },
        })
      ),
  })
  const leave = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:separate_peace', {
          body: { war_id: warId, side_id: row.entity?.id ?? 0 },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, leave.isPending)
  const locked = row.locked ?? []
  const side = named(SIDE, row.side)
  const gone = row.left_epoch !== null && row.left_epoch !== undefined
  const leaveWhy =
    busy ??
    (row.primary
      ? 'A side that leads the war ends it with a peace'
      : gone
        ? 'It has already left the war'
        : undefined)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2.5'>
      <div className='flex min-w-0 items-center gap-2'>
        <Text as='span' weight='medium' truncate className='min-w-0 flex-1'>
          {row.entity?.name ?? 'A people'}
        </Text>
        <Tag item={side} />
        {locked.length > 0 && (
          <Badge size='sm' variant='outline'>
            <Lock />
            Held
          </Badge>
        )}
        {gone && <Plain icon={Flag}>{`Left ${row.left_epoch}`}</Plain>}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/mil:grid-cols-2'>
        <NumberField
          label='War support'
          icon={Megaphone}
          value={support}
          max={PERCENT}
          framed={false}
          onChange={setSupport}
        />
        <NumberField
          label='Weariness'
          icon={Flag}
          value={weariness}
          max={PERCENT}
          framed={false}
          onChange={setWeariness}
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(true)}
        >
          <Lock />
          Set and hold
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || locked.length === 0}
          disabledReason={
            busy ?? (locked.length === 0 ? 'Nothing is held' : undefined)
          }
          onClick={() => save.mutate(false)}
        >
          <Unlock />
          Release
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={leaveWhy !== undefined}
          disabledReason={leaveWhy}
          onClick={() => leave.mutate(undefined)}
        >
          <Handshake />
          Separate peace
        </Button>
      </div>
    </div>
  )
}

export function SupportControls({
  room,
  blocked,
}: {
  room: Room
  blocked: string | null
}) {
  return (
    <div data-surface='WarSupport' className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>War support and peace</Label>
      <Muted as='span' variant='caption'>
        Support follows opinion, justification, propaganda, the dead, taxes, the
        maimed and occupied homes; low support pushes toward peace and raises a
        peace movement. Held values stay as set.
      </Muted>
      <div className='grid min-w-0 grid-cols-1 gap-2 @xl/mil:grid-cols-2'>
        {room.weariness.map((row) => (
          <SideConduct
            key={row.entity?.id ?? row.side}
            warId={room.war.id}
            row={row}
            blocked={blocked}
          />
        ))}
      </div>
    </div>
  )
}
