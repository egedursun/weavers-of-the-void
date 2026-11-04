import { useState } from 'react'
import {
  Ghost,
  Link2,
  Lock,
  RefreshCw,
  Save,
  Scale,
  Skull,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  bindingKindValues,
  spiritAlignmentValues,
  stratumKindValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import {
  type SoulCard,
  type Stratum,
  table,
  useAfterlife,
  useSoul,
  words,
} from './api'

const PERCENT = 100
const WORKING = 'Working…'
const LEDGER = ['renown', 'honour', 'faith', 'violence', 'infamy'] as const

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className='flex w-32 flex-col gap-1'>
      <Label>{label}</Label>
      <Input
        type='number'
        min={0}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function SoulLevers({
  soul,
  strata,
  blocked,
}: {
  soul: SoulCard
  strata: Stratum[]
  blocked: string | null
}) {
  const id = soul.spirit?.id ?? 0
  const [stratum, setStratum] = useState(String(strata[0]?.id ?? ''))
  const [reason, setReason] = useState('')
  const [target, setTarget] = useState('')
  const [binding, setBinding] = useState<string>('place')
  const [home, setHome] = useState('')
  const [memory, setMemory] = useState(String(soul.memory_strength))
  const [veneration, setVeneration] = useState(String(soul.veneration))
  const [alignment, setAlignment] = useState<string>(soul.alignment)
  const judge = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:judge', {
          body: { spirit_id: id, stratum_id: Number(stratum), reason },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:release', { body: { spirit_id: id } })
      ),
  })
  const bind = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:bind', {
          body: {
            spirit_id: id,
            target_id: Math.round(Number(target)),
            binding: binding as SoulCard['binding'],
          },
        })
      ),
  })
  const seal = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:seal', {
          body: { spirit_id: id, sealed: !soul.sealed },
        })
      ),
  })
  const reborn = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:reincarnate', {
          body: {
            spirit_id: id,
            community_id: home ? Math.round(Number(home)) : null,
          },
        })
      ),
  })
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:edit', {
          body: {
            spirit_id: id,
            values: {
              memory_strength: Math.max(
                0,
                Math.min(PERCENT, Math.round(Number(memory) || 0))
              ),
              veneration: Math.max(
                0,
                Math.min(PERCENT, Math.round(Number(veneration) || 0))
              ),
              alignment,
            },
          },
        })
      ),
  })
  const busy = busyOf(
    blocked,
    judge.isPending,
    release.isPending,
    bind.isPending,
    seal.isPending,
    reborn.isPending,
    edit.isPending
  )
  return (
    <div data-surface='SoulLevers' className='flex min-w-0 flex-col gap-3'>
      {strata.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <MindPicker
            label='Send to'
            value={stratum}
            table={Object.fromEntries(
              strata.map((item) => [String(item.id), item.name])
            )}
            blocked={busy}
            onPick={setStratum}
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Label>Reason</Label>
            <Input
              value={reason}
              aria-label='Reason'
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => judge.mutate(undefined)}
          >
            <Scale />
            Judge
          </Button>
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField
          label='Bind to record'
          value={target}
          onChange={setTarget}
        />
        <MindPicker
          label='Binding'
          value={binding}
          table={table(bindingKindValues)}
          blocked={busy}
          onPick={setBinding}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || !target}
          disabledReason={busy ?? 'Name the record first.'}
          onClick={() => bind.mutate(undefined)}
        >
          <Link2 />
          Bind
        </Button>
        <NumberField label='Reborn in' value={home} onChange={setHome} />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => reborn.mutate(undefined)}
        >
          <RefreshCw />
          Reincarnate
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField label='Memory' value={memory} onChange={setMemory} />
        <NumberField
          label='Veneration'
          value={veneration}
          onChange={setVeneration}
        />
        <MindPicker
          label='Temper'
          value={alignment}
          table={table(spiritAlignmentValues)}
          blocked={busy}
          onPick={setAlignment}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => edit.mutate(undefined)}
        >
          <Save />
          Save
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => seal.mutate(undefined)}
        >
          <Lock />
          {soul.sealed ? 'Break the seal' : 'Seal against rebirth'}
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => release.mutate(undefined)}
        >
          <Sparkles />
          Release
        </Button>
      </div>
    </div>
  )
}

function SoulBody({
  soul,
  blocked,
}: {
  soul: SoulCard
  blocked: string | null
}) {
  const realm = useAfterlife(soul.spirit?.id ?? 0)
  return (
    <div data-surface='SoulCard' className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {soul.origin && (
          <EntityLink kind='entity' id={String(soul.origin.id)}>
            {soul.origin.name}
          </EntityLink>
        )}
        <Badge variant='info'>{words(soul.state)}</Badge>
        <Badge
          variant={soul.alignment === 'vengeful' ? 'destructive' : 'outline'}
        >
          {words(soul.alignment)}
        </Badge>
        <Badge variant='outline'>{`Rites: ${words(soul.rite)}`}</Badge>
        {soul.stratum && <Badge variant='outline'>{soul.stratum.name}</Badge>}
        {soul.sealed && <Badge variant='warning'>sealed</Badge>}
        {soul.bound && (
          <Badge variant='outline'>{`bound to ${soul.bound.name}`}</Badge>
        )}
        {soul.possessing && (
          <Badge variant='destructive'>{`possessing ${soul.possessing.name}`}</Badge>
        )}
        {soul.reborn_as && (
          <Badge variant='success'>{`reborn as ${soul.reborn_as.name}`}</Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <StatBar
          label='Memory of the living'
          value={soul.memory_strength}
          max={PERCENT}
        />
        <StatBar
          label='Veneration'
          value={soul.veneration}
          max={PERCENT}
          tone='success'
        />
      </div>
      <div
        data-surface='DeedsLedger'
        className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-5'
      >
        {LEDGER.map((key) => (
          <StatBar
            key={key}
            label={words(key)}
            value={soul.deeds[key] ?? 0}
            max={PERCENT}
            tone={
              key === 'infamy' || key === 'violence' ? 'destructive' : 'default'
            }
          />
        ))}
      </div>
      {soul.judgements.length > 0 && (
        <Timeline label='Judgements'>
          {soul.judgements.map((item, index) => (
            <TimelineItem
              key={`${item.epoch}.${index}`}
              icon={Scale}
              title={item.reason}
              timestamp={`Epoch ${item.epoch}`}
              tone={item.stratum ? 'primary' : 'warning'}
              last={index === soul.judgements.length - 1}
            />
          ))}
        </Timeline>
      )}
      <SoulLevers
        soul={soul}
        strata={realm.data?.strata ?? []}
        blocked={blocked}
      />
    </div>
  )
}

export function SoulSection({
  spiritId,
  readOnlyReason,
}: {
  spiritId: number
  readOnlyReason?: string | null
}) {
  const soul = useSoul(spiritId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  if (soul.isError) return null
  return (
    <Section
      id='section-soul'
      title='Soul'
      description='Deeds, judgement, rest and return.'
      icon={Ghost}
    >
      {soul.isPending && <Muted>Reading the soul…</Muted>}
      {soul.data && <SoulBody soul={soul.data} blocked={blocked} />}
    </Section>
  )
}

function StratumRow({
  realmId,
  stratum,
  blocked,
}: {
  realmId: number
  stratum: Stratum
  blocked: string | null
}) {
  const [name, setName] = useState(stratum.name)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: { realm_id: realmId, kind: stratum.kind, name, remove: false },
        })
      ),
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: { realm_id: realmId, kind: stratum.kind, remove: true },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, remove.isPending)
  return (
    <li
      data-surface='Stratum'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Skull
          aria-hidden='true'
          className='size-icon-sm text-muted-foreground'
        />
        <Text as='span' weight='semibold'>
          {stratum.name}
        </Text>
        <Badge variant='outline'>{words(stratum.kind)}</Badge>
        <Badge variant='info'>{`${stratum.population} souls`}</Badge>
        {Object.entries(stratum.criteria).map(([key, value]) => (
          <Badge key={key} variant='outline'>{`${words(key)} ${value}`}</Badge>
        ))}
      </div>
      {stratum.souls.length > 0 && (
        <div className='flex min-w-0 flex-wrap gap-2'>
          {stratum.souls.map((soul) => (
            <EntityLink key={soul.id} kind='entity' id={String(soul.id)}>
              {soul.name}
            </EntityLink>
          ))}
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Label>Name</Label>
          <Input
            value={name}
            aria-label='Name'
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Rename
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate(undefined)}
        >
          <Trash2 />
          Unmake
        </Button>
      </div>
    </li>
  )
}

export function AfterlifeSection({
  regionId,
  readOnlyReason,
}: {
  regionId: number
  readOnlyReason?: string | null
}) {
  const view = useAfterlife(regionId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const [kind, setKind] = useState<string>('paradise')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: {
            realm_id: regionId,
            kind: kind as Stratum['kind'],
            remove: false,
          },
        })
      ),
  })
  const strata = view.data?.strata ?? []
  if (view.isPending || view.isError) return null
  const busy = busyOf(blocked, add.isPending)
  return (
    <Section
      id='section-afterlife'
      title='Realm of the dead'
      description='The strata of the afterlife and the souls in each.'
      icon={Skull}
    >
      <ul data-surface='AfterlifeRealm' className='flex min-w-0 flex-col gap-2'>
        {strata.map((stratum) => (
          <StratumRow
            key={stratum.id}
            realmId={regionId}
            stratum={stratum}
            blocked={blocked}
          />
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='New stratum'
          value={kind}
          table={table(stratumKindValues)}
          blocked={busy}
          onPick={setKind}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => add.mutate(undefined)}
        >
          <Sparkles />
          Make it
        </Button>
      </div>
      {strata.length === 0 && (
        <EmptyState
          icon={Skull}
          title='No strata'
          description='No soul has been judged here yet.'
        />
      )}
    </Section>
  )
}
