import { useState } from 'react'
import {
  BookOpen,
  Church,
  Flame,
  GitBranch,
  Landmark,
  Plus,
  Save,
  ScrollText,
  Sparkles,
  Trash2,
  TriangleAlert,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  judgementDoctrineValues,
  tenetKindValues,
} from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import {
  type Doctrine,
  type TenetKind,
  table,
  useDoctrine,
  useTenetKinds,
  words,
} from './api'

const PERCENT = 100
const WORKING = 'Working…'
const NUMBERS = [
  'orthodoxy',
  'tithe_rate',
  'treasury',
  'clergy_count',
  'clergy_quality',
  'zeal',
  'doctrinal_distance',
] as const
type DoctrineNumber = (typeof NUMBERS)[number]

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function TenetCard({
  cultId,
  tenet,
  blocked,
}: {
  cultId: number
  tenet: Doctrine['tenets'][number]
  blocked: string | null
}) {
  const drop = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:tenet', {
          body: { cult_id: cultId, tenet: tenet.tenet, held: false },
        })
      ),
  })
  const busy = busyOf(blocked, drop.isPending)
  return (
    <li
      data-surface='TenetCard'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Sparkles aria-hidden='true' className='size-icon-sm text-primary' />
        <Text as='span' weight='semibold'>
          {words(tenet.tenet)}
        </Text>
        {tenet.target_name && (
          <Badge variant='outline'>{tenet.target_name}</Badge>
        )}
        <Muted
          as='span'
          variant='caption'
        >{`since epoch ${tenet.since_epoch}`}</Muted>
      </div>
      <Muted>{tenet.effect}</Muted>
      <div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => drop.mutate(undefined)}
        >
          <Trash2 />
          Cast it off
        </Button>
      </div>
    </li>
  )
}

function AddTenet({
  cultId,
  held,
  blocked,
}: {
  cultId: number
  held: TenetKind[]
  blocked: string | null
}) {
  const kinds = useTenetKinds()
  const free = tenetKindValues.filter((item) => !held.includes(item))
  const [tenet, setTenet] = useState<string>(free[0] ?? 'proselytism')
  const [target, setTarget] = useState('')
  const spec = kinds.data?.find((item) => item.tenet === tenet)
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:tenet', {
          body: {
            cult_id: cultId,
            tenet: tenet as TenetKind,
            held: true,
            target: target || null,
          },
        })
      ),
  })
  const busy = busyOf(blocked, add.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Tenet'
          value={tenet}
          table={table(free)}
          blocked={busy}
          onPick={setTenet}
        />
        {spec?.targeted && (
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Its object</Label>
            <Input
              value={target}
              aria-label='Its object'
              onChange={(event) => setTarget(event.target.value)}
            />
          </div>
        )}
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => add.mutate(undefined)}
        >
          <Plus />
          Reveal the tenet
        </Button>
      </div>
      {spec && <Muted variant='caption'>{spec.effect}</Muted>}
      {spec && spec.opposed.length > 0 && (
        <Muted variant='caption'>{`Cannot stand beside: ${spec.opposed.map(words).join(', ')}`}</Muted>
      )}
    </div>
  )
}

function DoctrineForm({
  doctrine,
  blocked,
}: {
  doctrine: Doctrine
  blocked: string | null
}) {
  const id = doctrine.cult?.id ?? 0
  const [numbers, setNumbers] = useState<Record<DoctrineNumber, string>>(
    () =>
      Object.fromEntries(
        NUMBERS.map((key) => [key, String(doctrine[key])])
      ) as Record<DoctrineNumber, string>
  )
  const [judgement, setJudgement] = useState<string>(doctrine.judgement)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:doctrine', {
          body: {
            cult_id: id,
            values: {
              ...Object.fromEntries(
                NUMBERS.map((key) => [
                  key,
                  Math.max(0, Math.round(Number(numbers[key]) || 0)),
                ])
              ),
              judgement,
            },
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:doctrine', {
          body: { cult_id: id, values: {}, release: doctrine.locked },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, release.isPending)
  return (
    <div data-surface='DoctrineForm' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {NUMBERS.map((key) => (
          <div key={key} className='flex min-w-0 flex-col gap-1'>
            <Label>{words(key)}</Label>
            <Input
              type='number'
              min={0}
              max={
                ['treasury', 'clergy_count'].includes(key) ? undefined : PERCENT
              }
              value={numbers[key]}
              aria-label={words(key)}
              onChange={(event) =>
                setNumbers((current) => ({
                  ...current,
                  [key]: event.target.value,
                }))
              }
            />
          </div>
        ))}
        <MindPicker
          label='The dead are judged by'
          value={judgement}
          table={table(judgementDoctrineValues)}
          blocked={busy}
          onPick={setJudgement}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Set the doctrine
        </Button>
        {doctrine.locked.length > 0 && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => release.mutate(undefined)}
          >
            <Unlock />
            Let the faith decide again
          </Button>
        )}
        {doctrine.locked.map((key) => (
          <Badge key={key} variant='outline'>{`held: ${words(key)}`}</Badge>
        ))}
      </div>
    </div>
  )
}

function HeresyRow({
  heresy,
  blocked,
}: {
  heresy: Doctrine['heresies'][number]
  blocked: string | null
}) {
  const judge = useGodAction<boolean>({
    run: (suppressed) =>
      unwrap(
        api.POST('/api/actions/cult:judge_heresy', {
          body: { heresy_id: heresy.heresy?.id ?? 0, suppressed },
        })
      ),
  })
  const busy = busyOf(blocked, judge.isPending)
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'>
      <GitBranch
        aria-hidden='true'
        className='size-icon-sm text-muted-foreground'
      />
      {heresy.heresy && (
        <EntityLink kind='entity' id={String(heresy.heresy.id)}>
          {heresy.heresy.name}
        </EntityLink>
      )}
      <Badge variant='outline'>{`drifted ${heresy.distance}`}</Badge>
      <Badge variant={heresy.suppressed ? 'destructive' : 'outline'}>
        {heresy.suppressed ? 'hunted' : 'tolerated'}
      </Badge>
      <label className='flex items-center gap-2'>
        <Switch
          checked={heresy.suppressed}
          disabled={busy !== null}
          aria-label='Hunt the heresy'
          onCheckedChange={(next) => judge.mutate(next)}
        />
        <Text as='span'>Hunt it</Text>
      </label>
    </li>
  )
}

function Canonise({
  cultId,
  blocked,
}: {
  cultId: number
  blocked: string | null
}) {
  const [saint, setSaint] = useState('')
  const [item, setItem] = useState('')
  const name = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:canonise', {
          body: {
            cult_id: cultId,
            saint_id: Math.round(Number(saint)),
            item_id: item ? Math.round(Number(item)) : null,
          },
        })
      ),
  })
  const busy =
    busyOf(blocked, name.isPending) ?? (saint ? null : 'Name the saint first.')
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <div className='flex w-32 flex-col gap-1'>
        <Label>Saint</Label>
        <Input
          type='number'
          min={1}
          value={saint}
          aria-label='Saint'
          onChange={(event) => setSaint(event.target.value)}
        />
      </div>
      <div className='flex w-32 flex-col gap-1'>
        <Label>Relic item</Label>
        <Input
          type='number'
          min={1}
          value={item}
          aria-label='Relic item'
          onChange={(event) => setItem(event.target.value)}
        />
      </div>
      <Button
        size='sm'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => name.mutate(undefined)}
      >
        <Sparkles />
        Canonise
      </Button>
    </div>
  )
}

function DeclareHeresy({
  cultId,
  blocked,
}: {
  cultId: number
  blocked: string | null
}) {
  const [parent, setParent] = useState('')
  const declare = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:heresy', {
          body: { heresy_id: cultId, parent_id: Math.round(Number(parent)) },
        })
      ),
  })
  const busy =
    busyOf(blocked, declare.isPending) ??
    (parent ? null : 'Name the mother church first.')
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <div className='flex w-40 flex-col gap-1'>
        <Label>Mother church</Label>
        <Input
          type='number'
          min={1}
          value={parent}
          aria-label='Mother church'
          onChange={(event) => setParent(event.target.value)}
        />
      </div>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => declare.mutate(undefined)}
      >
        <GitBranch />
        Declare this faith a heresy of it
      </Button>
    </div>
  )
}

function DoctrineBody({
  doctrine,
  blocked,
}: {
  doctrine: Doctrine
  blocked: string | null
}) {
  const id = doctrine.cult?.id ?? 0
  const parts = Object.entries(doctrine.zeal_parts)
  return (
    <div data-surface='DoctrineSheet' className='flex min-w-0 flex-col gap-5'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {doctrine.god && (
          <Badge variant='info'>{`Faith of ${doctrine.god.name}`}</Badge>
        )}
        <Badge variant='outline'>{`Judgement by ${words(doctrine.judgement)}`}</Badge>
        {doctrine.fanaticism && (
          <Badge variant='destructive'>{`${words(doctrine.fanaticism)} (epoch ${doctrine.fanaticism_epoch ?? ''})`}</Badge>
        )}
        {doctrine.mother?.parent && (
          <Badge variant='warning'>{`Heresy of ${doctrine.mother.parent.name}`}</Badge>
        )}
        {doctrine.excommunicated.map((item) => (
          <Badge
            key={item.id}
            variant='outline'
          >{`Cast out: ${item.name}`}</Badge>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Zeal'
          value={String(doctrine.zeal)}
          icon={Flame}
          tone={doctrine.zeal > 80 ? 'danger' : 'muted'}
        />
        <KpiTile
          label='Treasury'
          value={formatInteger(doctrine.treasury)}
          icon={Landmark}
          hint={`Tithe ${doctrine.tithe_rate}%`}
        />
        <KpiTile
          label='Clergy'
          value={formatInteger(doctrine.clergy_count)}
          icon={Church}
          hint={`Learning ${doctrine.clergy_quality}`}
        />
        <KpiTile
          label='Orthodoxy'
          value={String(doctrine.orthodoxy)}
          icon={BookOpen}
          hint={`Drift ${doctrine.doctrinal_distance}`}
        />
      </div>
      {parts.length > 0 && (
        <div data-surface='ZealWhy' className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Why the zeal moves</Label>
          <ul className='grid min-w-0 grid-cols-1 gap-1 md:grid-cols-2'>
            {parts.map(([why, value]) => (
              <li
                key={why}
                className='flex min-w-0 items-center justify-between gap-2'
              >
                <Text as='span'>{why}</Text>
                <Badge variant={value < 0 ? 'destructive' : 'success'}>
                  {value > 0 ? `+${value}` : String(value)}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Label variant='overline'>Tenets</Label>
      {doctrine.tenets.length === 0 ? (
        <Muted>The faith holds no tenets yet.</Muted>
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
          {doctrine.tenets.map((tenet) => (
            <TenetCard
              key={tenet.tenet}
              cultId={id}
              tenet={tenet}
              blocked={blocked}
            />
          ))}
        </ul>
      )}
      <AddTenet
        cultId={id}
        held={doctrine.tenets.map((item) => item.tenet)}
        blocked={blocked}
      />
      <DoctrineForm doctrine={doctrine} blocked={blocked} />
      <Label variant='overline'>Clergy</Label>
      <ul className='flex min-w-0 flex-wrap gap-2'>
        {doctrine.clergy.map((office) => (
          <li key={office.kind}>
            <Badge variant='outline'>{`${words(office.kind)}: ${office.holder?.name ?? 'vacant'}`}</Badge>
          </li>
        ))}
      </ul>
      <div data-surface='CultHoldings' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Holdings</Label>
        <ul className='flex min-w-0 flex-wrap gap-2'>
          {doctrine.holdings.map((holding) => (
            <li key={`${holding.kind}.${holding.holding?.id}`}>
              <Badge
                variant={holding.kind === 'land' ? 'outline' : 'info'}
              >{`${words(holding.kind)}: ${holding.holding?.name ?? ''}`}</Badge>
            </li>
          ))}
        </ul>
      </div>
      <div data-surface='HeresyTree' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Heresies</Label>
        {doctrine.heresies.length === 0 ? (
          <Muted>No sect has broken away.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {doctrine.heresies.map((heresy) => (
              <HeresyRow
                key={heresy.heresy?.id}
                heresy={heresy}
                blocked={blocked}
              />
            ))}
          </ul>
        )}
        <DeclareHeresy cultId={id} blocked={blocked} />
      </div>
      <div data-surface='Relics' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Saints and relics</Label>
        {doctrine.relics.map((relic) => (
          <div
            key={relic.item?.id}
            className='flex min-w-0 flex-col gap-1 rounded-lg border bg-muted/30 p-2'
          >
            <Text as='span'>{`${relic.item?.name ?? 'A relic'}${relic.saint ? ` of ${relic.saint.name}` : ''}`}</Text>
            <StatBar
              label={`Sanctity, ${formatInteger(relic.pilgrims)} pilgrims`}
              value={relic.sanctity}
              max={PERCENT}
            />
          </div>
        ))}
        <Canonise cultId={id} blocked={blocked} />
      </div>
    </div>
  )
}

export function DoctrineSection({
  cultId,
  readOnlyReason,
}: {
  cultId: number
  readOnlyReason?: string | null
}) {
  const view = useDoctrine(cultId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-doctrine'
      title='Doctrine'
      description='Tenets, zeal, clergy, holdings, heresies and saints.'
      icon={ScrollText}
    >
      {view.isPending && <Muted>Reading the doctrine…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The doctrine could not be read'
          description={view.error.message}
        />
      )}
      {view.data && <DoctrineBody doctrine={view.data} blocked={blocked} />}
    </Section>
  )
}
