import { type ReactNode, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  Brain,
  DoorClosed,
  Flame,
  Ghost,
  Link2,
  Lock,
  RefreshCw,
  Save,
  Scale,
  Skull,
  Sparkles,
  Unlink,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  AttributeTile,
  EmptyState,
  KpiTile,
  type KpiTone,
  RangeField,
  Section,
  ShowMore,
  StatBar,
  Timeline,
  TimelineItem,
  type TimelineTone,
  useShowMore,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { goodBand, named, sentence } from '../realm/labels'
import {
  AdjustPanel,
  ChoiceGrid,
  Hero,
  Panel,
  RecordField,
  RefLink,
  Tag,
} from '../realm/parts'
import {
  PossessionCard,
  RaiseSoul,
  RealmGods,
  SoulLedger,
  SoulSeal,
} from './Souls'
import { StratumEditor } from './Strata'
import { type SoulCard, type Stratum, useAfterlife, useSoul } from './api'
import {
  ALIGNMENTS,
  BINDINGS,
  DEEDS,
  GATES,
  JUDGEMENTS,
  RITES,
  SOUL_STATES,
  STRATA,
  criteriaText,
} from './labels'

const PERCENT = 100
const WORKING = 'Working…'
const SOULS_SHOWN = 12
const AUTOMATIC = /^judged by \w+: score/
const MEMORY_WORDS: [string, string, string, string] = [
  'Forgotten',
  'Fading',
  'Remembered',
  'Vivid',
]
const VENERATION_WORDS: [string, string, string, string] = [
  'Neglected',
  'Honoured',
  'Revered',
  'Worshipped',
]

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function timelineTone(tone: KpiTone | undefined): TimelineTone {
  if (tone === 'gold') return 'primary'
  if (tone === 'danger') return 'destructive'
  if (tone === 'warning') return 'warning'
  if (tone === 'success' || tone === 'verdigris') return 'success'
  return 'default'
}

function LeverGroup({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <Label variant='overline'>{title}</Label>
      {children}
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
  const [picked, setStratum] = useState('')
  const stratum = picked || String(strata[0]?.id ?? '')
  const [reason, setReason] = useState('')
  const [target, setTarget] = useState<number | null>(null)
  const [binding, setBinding] = useState<string>('place')
  const [home, setHome] = useState<number | null>(null)
  const [memory, setMemory] = useState(soul.memory_strength)
  const [veneration, setVeneration] = useState(soul.veneration)
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
            target_id: target ?? 0,
            binding: binding as SoulCard['binding'],
          },
        })
      ),
  })
  const loose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:bind', {
          body: { spirit_id: id, target_id: 0, binding: 'none' },
        })
      ),
  })
  const reborn = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:reincarnate', {
          body: { spirit_id: id, community_id: home },
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
                Math.min(PERCENT, Math.round(memory))
              ),
              veneration: Math.max(
                0,
                Math.min(PERCENT, Math.round(veneration))
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
    loose.isPending,
    reborn.isPending,
    edit.isPending
  )
  return (
    <AdjustPanel
      trigger='Adjust the soul'
      title='Hold this soul in your hand'
      note='Judge it, bind it, send it back into the world, or change how it is remembered. Every change goes into the ledger.'
    >
      <div data-surface='SoulLevers' className='flex min-w-0 flex-col gap-3'>
        <LeverGroup title='Temper and memory'>
          <ChoiceGrid
            label='Temper'
            table={ALIGNMENTS}
            value={alignment}
            blocked={busy}
            onPick={setAlignment}
          />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/soul:grid-cols-2'>
            <RangeField
              label='Memory of the living'
              icon={Brain}
              value={memory}
              min={0}
              max={PERCENT}
              level={goodBand(memory, MEMORY_WORDS).label}
              lowLabel='Forgotten'
              highLabel='Vivid'
              onChange={setMemory}
            />
            <RangeField
              label='Veneration'
              icon={Flame}
              value={veneration}
              min={0}
              max={PERCENT}
              level={goodBand(veneration, VENERATION_WORDS).label}
              lowLabel='Neglected'
              highLabel='Worshipped'
              onChange={setVeneration}
            />
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => edit.mutate(undefined)}
            >
              <Save />
              Save the soul
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(undefined)}
            >
              <Sparkles />
              Release it
            </Button>
          </div>
        </LeverGroup>
        {strata.length > 0 && (
          <LeverGroup title='Judge it'>
            <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/soul:grid-cols-2'>
              <MindPicker
                label='Send to'
                value={stratum}
                table={Object.fromEntries(
                  strata.map((item) => [
                    String(item.id),
                    `${item.name} (${named(STRATA, item.kind).label})`,
                  ])
                )}
                blocked={busy}
                onPick={setStratum}
              />
              <div className='flex min-w-0 flex-col gap-1'>
                <Label>Reason</Label>
                <Input
                  value={reason}
                  aria-label='Reason'
                  placeholder='Why the soul goes there'
                  onChange={(event) => setReason(event.target.value)}
                />
              </div>
            </div>
            <div>
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
          </LeverGroup>
        )}
        <LeverGroup title='Bind it'>
          <ChoiceGrid
            label='Bound to'
            table={BINDINGS}
            value={binding}
            blocked={busy}
            onPick={setBinding}
          />
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='min-w-48 flex-1'>
              <RecordField
                label='The record it haunts'
                types={null}
                value={target}
                onChange={setTarget}
                blocked={busy}
              />
            </div>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || target === null}
              disabledReason={busy ?? 'Choose the record first.'}
              onClick={() => bind.mutate(undefined)}
            >
              <Link2 />
              Bind
            </Button>
            {soul.binding !== 'none' && (
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => loose.mutate(undefined)}
              >
                <Unlink />
                Loose it
              </Button>
            )}
          </div>
        </LeverGroup>
        <LeverGroup title='Send it back'>
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='min-w-48 flex-1'>
              <RecordField
                label='Reborn among'
                types={['people', 'settlement', 'tribe']}
                value={home}
                onChange={setHome}
                blocked={busy}
                placeholder='Wherever fate decides'
              />
            </div>
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
        </LeverGroup>
      </div>
    </AdjustPanel>
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
  const alignment = named(ALIGNMENTS, soul.alignment)
  const imprint = Object.entries(soul.imprint)
  return (
    <div
      data-surface='SoulCard'
      className='@container/soul flex min-w-0 flex-col gap-4'
    >
      <Hero
        icon={Ghost}
        tone={alignment.tone}
        eyebrow={soul.origin ? 'The soul of' : 'A soul'}
        title={
          soul.origin ? (
            <RefLink node={soul.origin} />
          ) : (
            (soul.spirit?.name ?? 'Nameless')
          )
        }
      >
        <Tag spec={named(SOUL_STATES, soul.state)} />
        <Tag spec={alignment} />
        <Tag spec={named(RITES, soul.rite)} />
        {soul.stratum && (
          <Tag
            spec={named(STRATA, soul.stratum.kind)}
            text={soul.stratum.name}
          />
        )}
        {soul.sealed && (
          <Tag
            spec={{
              label: 'Sealed against rebirth',
              icon: Lock,
              tone: 'warning',
            }}
          />
        )}
        {soul.gate && <Tag spec={named(GATES, soul.gate)} />}
        {soul.patron_name && (
          <Tag
            spec={{ label: 'Patron', icon: Sparkles, tone: 'gold' }}
            text={`Of ${soul.patron_name}`}
          />
        )}
        {soul.traits.map((trait) => (
          <Badge key={trait} size='sm' variant='outline'>
            {sentence(trait)}
          </Badge>
        ))}
      </Hero>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xs/soul:grid-cols-3'>
        <KpiTile
          label='Unrest'
          value={soul.unrest}
          icon={Skull}
          tone={soul.unrest >= 60 ? 'danger' : 'muted'}
          meter={{ value: soul.unrest, max: PERCENT, label: 'Unrest' }}
          hint='Restless souls haunt, and the vengeful possess'
        />
        <KpiTile
          label='Memory of the living'
          value={soul.memory_strength}
          icon={Brain}
          tone='verdigris'
          meter={{
            value: soul.memory_strength,
            max: PERCENT,
            label: 'Memory of the living',
          }}
          hint={`${goodBand(soul.memory_strength, MEMORY_WORDS).label}; fades unless the living remember`}
        />
        <KpiTile
          label='Veneration'
          value={soul.veneration}
          icon={Flame}
          tone='gold'
          meter={{ value: soul.veneration, max: PERCENT, label: 'Veneration' }}
          hint={`${goodBand(soul.veneration, VENERATION_WORDS).label}; offerings from the peoples who honour it`}
        />
      </div>
      <SoulSeal
        key={`${soul.sealed}.${soul.seal_strength}`}
        soul={soul}
        blocked={blocked}
      />
      <PossessionCard
        key={`${soul.possession?.host?.id ?? 0}.${soul.possession?.stress ?? 0}`}
        soul={soul}
        blocked={blocked}
      />
      {(soul.bound || soul.reborn_as) && (
        <Panel title='Ties to the living' icon={Link2} tone='verdigris'>
          <div className='flex min-w-0 flex-col gap-2'>
            {soul.bound && (
              <div className='flex min-w-0 items-center gap-2'>
                <Tag spec={named(BINDINGS, soul.binding)} text='Bound to' />
                <RefLink node={soul.bound} />
              </div>
            )}
            {soul.reborn_as && (
              <div className='flex min-w-0 items-center gap-2'>
                <Tag
                  spec={{
                    label: 'Reborn as',
                    icon: RefreshCw,
                    tone: 'success',
                  }}
                />
                <RefLink node={soul.reborn_as} />
              </div>
            )}
          </div>
        </Panel>
      )}
      <Panel
        title='Deeds weighed at death'
        icon={Scale}
        hint='The ledger the judges read'
      >
        <div
          data-surface='DeedsLedger'
          className='grid min-w-0 grid-cols-2 gap-2 @md/soul:grid-cols-3 @xl/soul:grid-cols-5'
        >
          {Object.entries(DEEDS).map(([key, spec]) => (
            <AttributeTile
              key={key}
              icon={spec.icon}
              abbr={spec.label}
              label={spec.label}
              value={soul.deeds[key] ?? 0}
              max={PERCENT}
              tone={
                key === 'infamy' || key === 'violence'
                  ? 'destructive'
                  : key === 'honour'
                    ? 'success'
                    : key === 'faith'
                      ? 'info'
                      : 'default'
              }
            />
          ))}
        </div>
        {imprint.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted as='span' variant='caption'>
              Carried into the next life
            </Muted>
            {imprint.map(([key, value]) => (
              <Badge
                key={key}
                size='sm'
                variant='secondary'
              >{`${sentence(key)} ${value}`}</Badge>
            ))}
          </div>
        )}
      </Panel>
      {soul.judgements.length > 0 && (
        <Panel
          title='Judgements'
          icon={Scale}
          tone='info'
          count={soul.judgements.length}
        >
          <Timeline label='Judgements'>
            {soul.judgements.map((item, index) => {
              const doctrine = named(JUDGEMENTS, item.doctrine)
              return (
                <TimelineItem
                  key={`${item.epoch}.${index}`}
                  icon={doctrine.icon}
                  framed
                  title={
                    item.stratum ? `Sent to ${item.stratum}` : 'Left to wander'
                  }
                  timestamp={`Epoch ${item.epoch}`}
                  tone={item.stratum ? 'primary' : 'warning'}
                  last={index === soul.judgements.length - 1}
                >
                  <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                    <Tag spec={doctrine} />
                    <Badge size='sm' variant='secondary'>
                      {`Score ${item.score}`}
                    </Badge>
                    <Tag spec={named(RITES, item.rite)} />
                  </div>
                  {!AUTOMATIC.test(item.reason) && (
                    <Muted variant='caption'>{sentence(item.reason)}</Muted>
                  )}
                </TimelineItem>
              )
            })}
          </Timeline>
        </Panel>
      )}
      <SoulLedger
        key={JSON.stringify([
          soul.deeds,
          soul.imprint,
          soul.traits,
          soul.rite,
          soul.state,
          soul.patron_son_id,
          soul.locked,
        ])}
        soul={soul}
        blocked={blocked}
      />
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

function StratumRung({
  realmId,
  stratum,
  most,
  last,
  blocked,
}: {
  realmId: number
  stratum: Stratum
  most: number
  last: boolean
  blocked: string | null
}) {
  const souls = useShowMore(stratum.souls, SOULS_SHOWN)
  const spec = named(STRATA, stratum.kind)
  return (
    <TimelineItem
      icon={spec.icon}
      tone={timelineTone(spec.tone)}
      framed
      last={last}
      title={stratum.name}
      timestamp={`${stratum.population} ${stratum.population === 1 ? 'soul' : 'souls'}`}
    >
      <div data-surface='Stratum' className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Tag spec={spec} />
          {stratum.closed && (
            <Tag
              spec={{ label: 'Gates closed', icon: DoorClosed, tone: 'muted' }}
            />
          )}
          {stratum.son_name && (
            <Tag
              spec={{ label: 'Ruler', icon: Sparkles, tone: 'gold' }}
              text={`Only for ${stratum.son_name}`}
            />
          )}
          {stratum.cult && (
            <Tag
              spec={{ label: 'Church', icon: Users, tone: 'info' }}
              text={`Claimed by ${stratum.cult.name}`}
            />
          )}
          {criteriaText(stratum.criteria).map((line) => (
            <Badge key={line} size='sm' variant='outline'>
              {line}
            </Badge>
          ))}
        </div>
        <StatBar
          label='Share of the dead here'
          value={stratum.population}
          max={Math.max(1, most)}
          icon={Users}
          tone={
            spec.tone === 'danger'
              ? 'destructive'
              : spec.tone === 'gold'
                ? 'default'
                : 'muted'
          }
        />
        {stratum.souls.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'>
            {souls.visible.map((soul) => (
              <span key={soul.id} className='flex min-w-0 items-center gap-1'>
                <Ghost
                  aria-hidden='true'
                  className='size-icon-xs shrink-0 text-muted-foreground'
                />
                <RefLink node={soul} />
              </span>
            ))}
          </div>
        )}
        <ShowMore state={souls} noun={['soul', 'souls']} />
        <StratumEditor
          key={JSON.stringify([
            stratum.name,
            stratum.criteria,
            stratum.son_id,
            stratum.cult?.id,
            stratum.closed,
          ])}
          realmId={realmId}
          stratum={stratum}
          blocked={blocked}
        />
      </div>
    </TimelineItem>
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
  const [name, setName] = useState('')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/afterlife:stratum', {
          body: {
            realm_id: regionId,
            kind: kind as Stratum['kind'],
            name: name || null,
            clear_links: false,
            remove: false,
          },
        })
      ),
  })
  const strata = [...(view.data?.strata ?? [])].sort(
    (left, right) =>
      (STRATA[left.kind]?.depth ?? 0) - (STRATA[right.kind]?.depth ?? 0)
  )
  if (view.isPending || view.isError) return null
  const busy = busyOf(blocked, add.isPending)
  const total = strata.reduce((sum, item) => sum + item.population, 0)
  const most = Math.max(0, ...strata.map((item) => item.population))
  return (
    <Section
      id='section-afterlife'
      title='Realm of the dead'
      description='The strata of the afterlife and the souls in each.'
      icon={Skull}
    >
      <div className='@container/soul flex min-w-0 flex-col gap-4'>
        {strata.length === 0 ? (
          <EmptyState
            icon={Skull}
            title='No strata'
            description='No soul has been judged here yet.'
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 @xs/soul:grid-cols-2'>
              <KpiTile
                label='Souls at rest'
                value={total}
                icon={Ghost}
                tone='verdigris'
                hint='Every soul judged into this realm'
              />
              <KpiTile
                label='Strata'
                value={strata.length}
                icon={Scale}
                tone='gold'
                hint='From the heavens down to the depths'
              />
            </div>
            <RealmGods gods={view.data?.gods ?? []} />
            <div
              data-surface='AfterlifeRealm'
              className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'
            >
              <div className='flex min-w-0 items-center gap-2'>
                <ArrowUp
                  aria-hidden='true'
                  className='size-icon-sm text-primary'
                />
                <Label variant='overline'>The heavens</Label>
              </div>
              <Timeline label='Strata of the afterlife'>
                {strata.map((stratum, index) => (
                  <StratumRung
                    key={`${stratum.id}-${stratum.name}`}
                    realmId={regionId}
                    stratum={stratum}
                    most={most}
                    last={index === strata.length - 1}
                    blocked={blocked}
                  />
                ))}
              </Timeline>
              <div className='flex min-w-0 items-center gap-2'>
                <ArrowDown
                  aria-hidden='true'
                  className='size-icon-sm text-destructive'
                />
                <Label variant='overline'>The depths</Label>
              </div>
            </div>
          </>
        )}
        <div className='flex min-w-0 flex-col'>
          <AdjustPanel
            trigger='Make a stratum'
            title='Make a new stratum'
            note='Raise a stratum of any kind, with your own name; shape who it takes once it stands.'
          >
            <ChoiceGrid
              label='Kind'
              table={STRATA}
              value={kind}
              blocked={busy}
              onPick={setKind}
            />
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>Its name</Label>
              <Input
                value={name}
                aria-label='Its name'
                placeholder='Named after its kind'
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div>
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
          </AdjustPanel>
          <RaiseSoul regionId={regionId} blocked={blocked} />
        </div>
      </div>
    </Section>
  )
}
