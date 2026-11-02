import { useState } from 'react'
import { Archive, Church, Link2, RotateCcw, Ship } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ConfirmDialog,
  FormRow,
  JobProgress,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type EntityContext, isLiving } from '../actions/context'
import { useLoreGate } from '../actions/gate'
import { humanize } from '../actions/schema'
import { useJob, useLoreMutation } from '../api/mutations'
import { useCosmos, useForeignGods } from '../api/queries'
import { type ArchiveMode } from '../api/types'

const CREATOR = 'creator'
const GODLESS = 'none'

function PatronRow({
  ctx,
  blocked,
}: {
  ctx: EntityContext
  blocked: string | null
}) {
  const foreignGods = useForeignGods()
  const current = ctx.detail.patron
  const initial =
    current?.kind === 'creator'
      ? CREATOR
      : current?.kind === 'son'
        ? `son:${current.id}`
        : current?.kind === 'foreign_god'
          ? `god:${current.id}`
          : GODLESS
  const [choice, setChoice] = useState(initial)
  const assign = useLoreMutation({
    run: (value: string) => {
      const [kind, raw] = value.split(':')
      const id = raw ? Number(raw) : null
      return unwrap(
        api.PUT('/api/entities/{entity_id}/patron', {
          params: { path: { entity_id: ctx.entity.id } },
          body: {
            creator: kind === CREATOR,
            son_id: kind === 'son' ? id : null,
            foreign_god_id: kind === 'god' ? id : null,
          },
        })
      )
    },
    success: 'Patron assigned',
  })
  const sons = (ctx.state?.sons ?? []).filter(
    (view) => view.son.status !== 'dead'
  )
  const gods = (foreignGods.data ?? []).filter(
    (god) =>
      god.status !== 'dead' &&
      (god.world_id === ctx.entity.world_id || god.id === current?.id)
  )
  const worldName = (worldId: number | null) =>
    ctx.multiWorld
      ? ctx.state?.worlds.find((world) => world.id === worldId)?.name
      : undefined
  const reason =
    blocked ??
    (choice === initial ? 'This is the present patron.' : null) ??
    (assign.isPending ? 'Working on it.' : null)
  return (
    <FormRow label='Patron' description={`Now: ${current?.name ?? 'godless'}`}>
      {(id) => (
        <div className='flex w-full min-w-0 flex-col gap-2 sm:flex-row'>
          <Select value={choice} onValueChange={setChoice}>
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={CREATOR}>The Creator himself</SelectItem>
              {sons.length > 0 && (
                <SelectGroup>
                  <SelectLabel>Sons</SelectLabel>
                  {sons.map((view) => (
                    <SelectItem key={view.son.id} value={`son:${view.son.id}`}>
                      {[view.son.name, worldName(view.son.current_world_id)]
                        .filter(Boolean)
                        .join(' · ')}
                    </SelectItem>
                  ))}
                </SelectGroup>
              )}
              {gods.length > 0 && (
                <SelectGroup>
                  <SelectLabel>Foreign gods</SelectLabel>
                  {gods.map((god) => (
                    <SelectItem key={god.id} value={`god:${god.id}`}>
                      {god.name}
                    </SelectItem>
                  ))}
                </SelectGroup>
              )}
              <SelectItem value={GODLESS}>Leave godless</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant='outline'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => assign.mutate(choice)}
          >
            <Church />
            Assign
          </Button>
        </div>
      )}
    </FormRow>
  )
}

function ArchiveRow({
  ctx,
  blocked,
}: {
  ctx: EntityContext
  blocked: string | null
}) {
  const override = ctx.entity.archive_override
  const initial: ArchiveMode =
    override === 'history'
      ? 'history'
      : override === 'atlas'
        ? 'atlas'
        : 'automatic'
  const [mode, setMode] = useState<ArchiveMode>(initial)
  const importance = ctx.detail.importance
  const assign = useLoreMutation({
    run: (next: ArchiveMode) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/archive', {
          params: { path: { entity_id: ctx.entity.id } },
          body: { mode: next },
        })
      ),
    success: 'Archive state set',
  })
  const reason =
    blocked ??
    (mode === initial ? 'This is the present state.' : null) ??
    (assign.isPending ? 'Working on it.' : null)
  return (
    <FormRow
      label='Archive'
      description='Records whose importance falls sink into history by themselves.'
    >
      {(id) => (
        <div className='flex w-full min-w-0 flex-col gap-2'>
          {importance && (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant={importance.archived ? 'secondary' : 'outline'}>
                {importance.archived ? 'In history' : 'In the Atlas'}
              </Badge>
              <Muted as='span' variant='caption'>
                {`Importance ${formatInteger(importance.importance)} · last named in epoch ${formatInteger(importance.last_mention)}${importance.reason ? ` · ${importance.reason}` : ''}`}
              </Muted>
            </div>
          )}
          <div className='flex w-full min-w-0 flex-col gap-2 sm:flex-row'>
            <Select
              value={mode}
              onValueChange={(value) => setMode(value as ArchiveMode)}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='automatic'>Automatic</SelectItem>
                <SelectItem value='atlas'>Keep in the Atlas</SelectItem>
                <SelectItem value='history'>Sink into history</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant='outline'
              disabled={reason !== null}
              disabledReason={reason ?? undefined}
              onClick={() => assign.mutate(mode)}
            >
              <Archive />
              Assign
            </Button>
          </div>
        </div>
      )}
    </FormRow>
  )
}

function SuggestBonds({
  ctx,
  blocked,
}: {
  ctx: EntityContext
  blocked: string | null
}) {
  const gate = useLoreGate()
  const suggest = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/entities/{entity_id}/suggest-links', {
          params: { path: { entity_id: ctx.entity.id } },
        })
      ),
    success: `Fate is looking at bonds for ${ctx.entity.name}`,
  })
  const job = useJob(suggest.data?.job_id ?? null)
  const reason =
    blocked ??
    gate.reason({ llm: true }) ??
    (suggest.isPending ? 'Working on it.' : null)
  return (
    <FormRow
      label='Bonds'
      description={`It has ${formatInteger(ctx.detail.bond_total)} bonds; Fate adds none without evidence.`}
    >
      {() => (
        <div className='flex w-full min-w-0 flex-col gap-2'>
          <Button
            variant='outline'
            className='self-start'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => suggest.mutate()}
          >
            <Link2 />
            Let Fate suggest bonds
          </Button>
          {job.data && (
            <JobProgress job={job.data} title='Fate looks for bonds' />
          )}
        </div>
      )}
    </FormRow>
  )
}

function Voyage({
  ctx,
  blocked,
}: {
  ctx: EntityContext
  blocked: string | null
}) {
  const cosmos = useCosmos()
  const [confirming, setConfirming] = useState(false)
  const journey = cosmos.data?.journeys.find(
    (item) =>
      item.traveller_entity_id === ctx.entity.id &&
      (item.status === 'underway' || item.status === 'waiting')
  )
  const recall = useLoreMutation({
    run: (journeyId: number) =>
      unwrap(
        api.POST('/api/voyages/{journey_id}/recall', {
          params: { path: { journey_id: journeyId } },
        })
      ),
    success: 'Expedition recalled',
  })
  if (!ctx.multiWorld || !isLiving(ctx.type)) return null
  const worldName = (id: number) =>
    cosmos.data?.worlds.find((item) => item.world.id === id)?.world.name ??
    `World ${id}`
  const hasRoute = (cosmos.data?.routes ?? []).some(
    (route) =>
      route.active &&
      route.known &&
      (route.world_a_id === ctx.entity.world_id ||
        route.world_b_id === ctx.entity.world_id)
  )
  const reason = blocked ?? (recall.isPending ? 'Working on it.' : null)
  return (
    <FormRow label='Voyage'>
      {() =>
        journey ? (
          <div className='flex w-full min-w-0 flex-wrap items-center gap-2'>
            <Ship
              aria-hidden='true'
              className='size-icon-sm text-muted-foreground'
            />
            <Text as='span' className='min-w-0 flex-1'>
              {`On the road to ${worldName(journey.destination_world_id)} · ${humanize(journey.intent)} · ${journey.epochs_left > 0 ? `arrives in ${journey.epochs_left} epochs` : 'arrives this epoch'}`}
            </Text>
            <Button
              variant='ghost'
              disabled={reason !== null}
              disabledReason={reason ?? undefined}
              onClick={() => setConfirming(true)}
            >
              <RotateCcw />
              Recall
            </Button>
            <ConfirmDialog
              open={confirming}
              onOpenChange={setConfirming}
              title='Recall the expedition?'
              desc='The travellers turn back home.'
              confirmText='Recall'
              isLoading={recall.isPending}
              handleConfirm={() => {
                setConfirming(false)
                recall.mutate(journey.id)
              }}
            />
          </div>
        ) : (
          <Muted>
            {hasRoute
              ? 'Not travelling. Send it with the expedition command below.'
              : `There is no open road out of ${worldName(ctx.entity.world_id)}; open one in the Cosmos screen first or wait for a closed road.`}
          </Muted>
        )
      }
    </FormRow>
  )
}

export function ArrangeExtras({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  return (
    <Section
      id='section-arrange'
      title='Arrange'
      description='Direct assignments; the world carries on by itself from there.'
      level={3}
    >
      <div className='flex min-w-0 flex-col gap-4'>
        {isLiving(ctx.type) && (
          <PatronRow
            key={`patron-${ctx.detail.patron?.id ?? 0}`}
            ctx={ctx}
            blocked={readOnlyReason}
          />
        )}
        <ArchiveRow
          key={`archive-${ctx.entity.archive_override ?? 'auto'}`}
          ctx={ctx}
          blocked={readOnlyReason}
        />
        <SuggestBonds ctx={ctx} blocked={readOnlyReason} />
        <Voyage ctx={ctx} blocked={readOnlyReason} />
      </div>
    </Section>
  )
}
