import { useState } from 'react'
import {
  BookOpen,
  Church,
  Coins,
  Flame,
  Gem,
  GitBranch,
  Lock,
  Plus,
  ScrollText,
  Sparkles,
  Trash2,
  TriangleAlert,
  Unlock,
  UserX,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { tenetKindValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  ChangeChip,
  EmptyState,
  IconStat,
  KpiTile,
  Medallion,
  RangeField,
  Section,
  ShowMore,
  StatBar,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { goodBand, named, plain, sentence } from '../realm/labels'
import {
  AdjustPanel,
  ChoiceCard,
  ChoiceGrid,
  Hero,
  NumberField,
  Panel,
  RecordField,
  RefLink,
  Tag,
  WhyList,
} from '../realm/parts'
import {
  type Doctrine,
  type TenetKind,
  useDoctrine,
  useTenetKinds,
} from './api'
import {
  CLERGY,
  DOCTRINE_FIELDS,
  FANATICISMS,
  HOLDINGS,
  JUDGEMENTS,
  TENETS,
} from './labels'

const PERCENT = 100
const WORKING = 'Working…'
const SHOWN = 8
const FERVENT = 80
const LUKEWARM = 30
const ZEAL_WORDS: [string, string, string, string] = [
  'Lukewarm',
  'Devout',
  'Fervent',
  'Burning',
]
const ORTHODOXY_WORDS: [string, string, string, string] = [
  'Loose',
  'Varied',
  'Orthodox',
  'Rigid',
]
const LEARNING_WORDS: [string, string, string, string] = [
  'Unlettered',
  'Taught',
  'Learned',
  'Masterful',
]
const TITHE_WORDS: [string, string, string, string] = [
  'Light',
  'Fair',
  'Heavy',
  'Crushing',
]
const DRIFT_WORDS: [string, string, string, string] = [
  'Faithful',
  'Drifting',
  'Strayed',
  'Unrecognisable',
]
const RANGES = [
  ['zeal', Flame, ZEAL_WORDS, 'Lukewarm', 'Burning'],
  ['orthodoxy', BookOpen, ORTHODOXY_WORDS, 'Loose', 'Rigid'],
  ['tithe_rate', Coins, TITHE_WORDS, 'None', 'All of it'],
  ['clergy_quality', Church, LEARNING_WORDS, 'Unlettered', 'Masterful'],
  ['doctrinal_distance', GitBranch, DRIFT_WORDS, 'Faithful', 'Unrecognisable'],
] as const
type RangeKey = (typeof RANGES)[number][0]

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function zealTone(zeal: number) {
  if (zeal > FERVENT) return 'danger' as const
  if (zeal < LUKEWARM) return 'muted' as const
  return 'warning' as const
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
  const spec = named(TENETS, tenet.tenet)
  return (
    <li
      data-surface='TenetCard'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {spec.label}
          </Text>
          <Muted
            variant='caption'
            truncate
          >{`Revealed in epoch ${tenet.since_epoch}`}</Muted>
        </div>
        {tenet.target_name && (
          <Badge size='sm' variant='outline'>
            {sentence(tenet.target_name)}
          </Badge>
        )}
      </div>
      <Muted className='flex-1'>{tenet.effect}</Muted>
      <div className='flex min-w-0 justify-end'>
        <Button
          size='sm'
          variant='ghost'
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
  const look = named(TENETS, tenet)
  return (
    <AdjustPanel
      trigger='Reveal a tenet'
      title='Reveal a new tenet'
      note='The faithful take it up at once. A tenet cannot stand beside its opposite.'
    >
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/faith:grid-cols-2'>
        <MindPicker
          label='Tenet'
          value={tenet}
          table={Object.fromEntries(
            free.map((item) => [item, named(TENETS, item).label])
          )}
          blocked={busy}
          onPick={setTenet}
        />
        {spec?.targeted && (
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Its object</Label>
            <Input
              value={target}
              aria-label='Its object'
              placeholder='A food, a beast or a place'
              onChange={(event) => setTarget(event.target.value)}
            />
          </div>
        )}
      </div>
      <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
        <Medallion icon={look.icon} tone={look.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold'>{look.label}</Text>
          {spec && <Muted>{spec.effect}</Muted>}
          {spec && spec.opposed.length > 0 && (
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <Muted as='span' variant='caption'>
                Cannot stand beside
              </Muted>
              {spec.opposed.map((item) => (
                <Tag key={item} spec={named(TENETS, item)} />
              ))}
            </div>
          )}
        </div>
      </div>
      <div>
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
    </AdjustPanel>
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
  const [ranges, setRanges] = useState<Record<RangeKey, number>>(
    () =>
      Object.fromEntries(RANGES.map(([key]) => [key, doctrine[key]])) as Record<
        RangeKey,
        number
      >
  )
  const [treasury, setTreasury] = useState(String(doctrine.treasury))
  const [clergy, setClergy] = useState(String(doctrine.clergy_count))
  const [judgement, setJudgement] = useState<string>(doctrine.judgement)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:doctrine', {
          body: {
            cult_id: id,
            values: {
              ...Object.fromEntries(
                RANGES.map(([key]) => [
                  key,
                  Math.max(0, Math.min(PERCENT, Math.round(ranges[key]))),
                ])
              ),
              treasury: Math.max(0, Math.round(Number(treasury) || 0)),
              clergy_count: Math.max(0, Math.round(Number(clergy) || 0)),
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
    <AdjustPanel
      trigger='Adjust the doctrine'
      title='Shape the doctrine'
      note='Set how the faith burns, tithes and judges. What you set is held until you let the faith decide again. Every change goes into the ledger.'
    >
      <div data-surface='DoctrineForm' className='flex min-w-0 flex-col gap-3'>
        <ChoiceGrid
          label='The dead are judged'
          table={JUDGEMENTS}
          hints={Object.fromEntries(
            Object.entries(JUDGEMENTS).map(([key, item]) => [key, item.hint])
          )}
          value={judgement}
          blocked={busy}
          onPick={setJudgement}
        />
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/faith:grid-cols-2'>
          {RANGES.map(([key, icon, words, low, high]) => (
            <RangeField
              key={key}
              label={plain(DOCTRINE_FIELDS, key)}
              icon={icon}
              value={ranges[key]}
              min={0}
              max={PERCENT}
              level={goodBand(ranges[key], [...words]).label}
              lowLabel={low}
              highLabel={high}
              onChange={(value) =>
                setRanges((current) => ({ ...current, [key]: value }))
              }
            />
          ))}
          <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3'>
            <div className='flex min-w-0 items-center gap-2.5'>
              <Medallion icon={Church} tone='gold' size='sm' />
              <div className='flex min-w-0 flex-col'>
                <Text as='span' weight='medium'>
                  Purse and priesthood
                </Text>
                <Muted as='span' variant='caption' truncate>
                  Gold in the temple coffers and priests serving
                </Muted>
              </div>
            </div>
            <div className='grid min-w-0 grid-cols-2 gap-2'>
              <NumberField
                label='Treasury'
                icon={Coins}
                tone='text-primary'
                min={0}
                value={treasury}
                blocked={busy}
                onChange={setTreasury}
              />
              <NumberField
                label='Clergy'
                icon={Users}
                min={0}
                value={clergy}
                blocked={busy}
                onChange={setClergy}
              />
            </div>
          </div>
        </div>
        {doctrine.locked.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {doctrine.locked.map((key) => (
              <Tag
                key={key}
                spec={{ label: key, icon: Lock, tone: 'info' }}
                text={`Holding ${plain(DOCTRINE_FIELDS, key).toLowerCase()}`}
              />
            ))}
          </div>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Lock />
            Set and hold the doctrine
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
        </div>
      </div>
    </AdjustPanel>
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
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-background p-2'>
      <Medallion
        icon={GitBranch}
        tone={heresy.suppressed ? 'danger' : 'warning'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        {heresy.heresy && <RefLink node={heresy.heresy} />}
        <Muted
          variant='caption'
          truncate
        >{`Broke away in epoch ${heresy.declared_epoch} · drifted ${heresy.distance}`}</Muted>
      </div>
      <Tag
        spec={
          heresy.suppressed
            ? { label: 'Hunted', icon: Flame, tone: 'danger' }
            : { label: 'Tolerated', icon: Users, tone: 'muted' }
        }
      />
      <label className='flex shrink-0 items-center gap-2'>
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

function Heresies({
  doctrine,
  blocked,
}: {
  doctrine: Doctrine
  blocked: string | null
}) {
  const id = doctrine.cult?.id ?? 0
  const [parent, setParent] = useState<number | null>(null)
  const declare = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:heresy', {
          body: { heresy_id: id, parent_id: parent ?? 0 },
        })
      ),
  })
  const busy = busyOf(blocked, declare.isPending)
  return (
    <Panel
      title='Heresies'
      icon={GitBranch}
      tone='warning'
      count={doctrine.heresies.length}
      hint='Sects that broke away, hunted or tolerated'
    >
      <div data-surface='HeresyTree' className='flex min-w-0 flex-col gap-2'>
        {doctrine.mother?.parent && (
          <div className='flex min-w-0 items-center gap-2 rounded-lg border border-warning/40 bg-warning/5 p-2'>
            <Medallion icon={GitBranch} tone='warning' size='sm' />
            <div className='flex min-w-0 flex-1 flex-col'>
              <Label>This faith is a heresy of</Label>
              <RefLink node={doctrine.mother.parent} />
            </div>
            <Tag
              spec={
                doctrine.mother.suppressed
                  ? { label: 'Hunted', icon: Flame, tone: 'danger' }
                  : { label: 'Tolerated', icon: Users, tone: 'muted' }
              }
            />
          </div>
        )}
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
        <AdjustPanel
          trigger='Declare a schism'
          title='Declare this faith a heresy'
          note='Name the mother church this faith broke from.'
        >
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='min-w-48 flex-1'>
              <RecordField
                label='Mother church'
                types={['cult']}
                value={parent}
                onChange={setParent}
                blocked={busy}
                placeholder='Choose a faith'
              />
            </div>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || parent === null}
              disabledReason={busy ?? 'Choose the mother church first.'}
              onClick={() => declare.mutate(undefined)}
            >
              <GitBranch />
              Declare the schism
            </Button>
          </div>
        </AdjustPanel>
      </div>
    </Panel>
  )
}

function Saints({
  doctrine,
  blocked,
}: {
  doctrine: Doctrine
  blocked: string | null
}) {
  const id = doctrine.cult?.id ?? 0
  const [saint, setSaint] = useState<number | null>(null)
  const [item, setItem] = useState<number | null>(null)
  const name = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cult:canonise', {
          body: { cult_id: id, saint_id: saint ?? 0, item_id: item },
        })
      ),
  })
  const busy = busyOf(blocked, name.isPending)
  return (
    <Panel
      title='Saints and relics'
      icon={Sparkles}
      count={doctrine.relics.length}
      hint='The holy dead and what pilgrims walk to see'
    >
      <div data-surface='Relics' className='flex min-w-0 flex-col gap-3'>
        {doctrine.relics.length === 0 ? (
          <Muted>No saint has been raised yet.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {doctrine.relics.map((relic) => (
              <li
                key={relic.item?.id ?? relic.saint?.id}
                className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Medallion icon={Sparkles} tone='gold' size='sm' />
                  <div className='flex min-w-0 flex-1 flex-col'>
                    <Label variant='overline'>Saint</Label>
                    {relic.saint ? (
                      <RefLink node={relic.saint} />
                    ) : (
                      <Muted>Nameless</Muted>
                    )}
                  </div>
                  <IconStat
                    icon={Users}
                    label='Pilgrims'
                    value={formatInteger(relic.pilgrims)}
                    tone='info'
                  />
                </div>
                <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Gem
                    aria-hidden='true'
                    className='size-icon-xs shrink-0 text-brand-verdigris'
                  />
                  {relic.item ? (
                    <RefLink node={relic.item} />
                  ) : (
                    <Muted>No relic</Muted>
                  )}
                  {relic.shrine && (
                    <>
                      <Church
                        aria-hidden='true'
                        className='size-icon-xs shrink-0 text-muted-foreground'
                      />
                      <RefLink node={relic.shrine} />
                    </>
                  )}
                </div>
                <StatBar
                  label={`Sanctity, canonised in epoch ${relic.canonised_epoch}`}
                  value={relic.sanctity}
                  max={PERCENT}
                  icon={Sparkles}
                />
              </li>
            ))}
          </ul>
        )}
        <AdjustPanel
          trigger='Canonise a saint'
          title='Raise a saint'
          note='Name a mortal a saint of this faith, with a relic for pilgrims if you wish.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/faith:grid-cols-2'>
            <RecordField
              label='Saint'
              types={['mortal']}
              value={saint}
              onChange={setSaint}
              blocked={busy}
              placeholder='Choose a mortal'
            />
            <RecordField
              label='Relic'
              types={['item']}
              value={item}
              onChange={setItem}
              blocked={busy}
              placeholder='No relic'
            />
          </div>
          <div>
            <Button
              size='sm'
              disabled={busy !== null || saint === null}
              disabledReason={busy ?? 'Choose the saint first.'}
              onClick={() => name.mutate(undefined)}
            >
              <Sparkles />
              Canonise
            </Button>
          </div>
        </AdjustPanel>
      </div>
    </Panel>
  )
}

function Holdings({ doctrine }: { doctrine: Doctrine }) {
  const [kind, setKind] = useState<string | null>(null)
  const kinds = Object.keys(HOLDINGS).filter((key) =>
    doctrine.holdings.some((item) => item.kind === key)
  )
  const shown = doctrine.holdings.filter(
    (item) => kind === null || item.kind === kind
  )
  const list = useShowMore(shown, SHOWN)
  return (
    <Panel
      title='Holdings'
      icon={Church}
      count={doctrine.holdings.length}
      hint='Lands, temples, holy places and relics the faith holds'
    >
      <div data-surface='CultHoldings' className='flex min-w-0 flex-col gap-2'>
        {doctrine.holdings.length === 0 ? (
          <Muted>The faith holds nothing.</Muted>
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-2 @xs/faith:grid-cols-2 @2xl/faith:grid-cols-3'>
              {kinds.map((key) => (
                <ChoiceCard
                  key={key}
                  spec={HOLDINGS[key]}
                  hint={kind === key ? 'Showing only these' : 'Show only these'}
                  count={
                    doctrine.holdings.filter((item) => item.kind === key).length
                  }
                  selected={kind === key}
                  onSelect={() => setKind(kind === key ? null : key)}
                />
              ))}
            </div>
            <ul className='grid min-w-0 grid-cols-1 gap-x-3 gap-y-2 @xl/faith:grid-cols-2'>
              {list.visible.map((holding) => {
                const spec = named(HOLDINGS, holding.kind)
                return (
                  <li
                    key={`${holding.kind}.${holding.holding?.id}`}
                    className='flex min-w-0 items-center gap-2'
                  >
                    <spec.icon
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                    <div className='min-w-0 flex-1 truncate'>
                      {holding.holding ? (
                        <RefLink node={holding.holding} />
                      ) : (
                        <Muted>Lost</Muted>
                      )}
                    </div>
                    <Muted
                      as='span'
                      variant='caption'
                    >{`since ${holding.since_epoch}`}</Muted>
                  </li>
                )
              })}
            </ul>
            <ShowMore state={list} noun={['holding', 'holdings']} />
          </>
        )}
      </div>
    </Panel>
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
  const judgement = named(JUDGEMENTS, doctrine.judgement)
  const zeal = goodBand(doctrine.zeal, ZEAL_WORDS)
  const filled = doctrine.clergy.filter((office) => office.holder).length
  return (
    <div
      data-surface='DoctrineSheet'
      className='@container/faith flex min-w-0 flex-col gap-4'
    >
      <Hero
        icon={Church}
        tone='gold'
        eyebrow={doctrine.god ? `Faith of ${doctrine.god.name}` : 'Faith'}
        title={doctrine.cult ? <RefLink node={doctrine.cult} /> : 'A faith'}
      >
        <Tag
          spec={judgement}
          text={
            doctrine.judgement === 'none'
              ? 'The dead are not judged'
              : `Judges the dead ${judgement.label.toLowerCase()}`
          }
        />
        <Badge size='sm' variant='secondary'>
          <Users aria-hidden='true' />
          {`${doctrine.members.length} peoples keep it`}
        </Badge>
        {doctrine.fanaticism && (
          <Tag
            spec={named(FANATICISMS, doctrine.fanaticism)}
            text={`${named(FANATICISMS, doctrine.fanaticism).label} since epoch ${doctrine.fanaticism_epoch ?? ''}`}
          />
        )}
        {doctrine.mother?.parent && (
          <Tag
            spec={{ label: 'Heresy', icon: GitBranch, tone: 'warning' }}
            text={`Heresy of ${doctrine.mother.parent.name}`}
          />
        )}
        {doctrine.excommunicated.map((item) => (
          <Tag
            key={item.id}
            spec={{ label: 'Cast out', icon: UserX, tone: 'danger' }}
            text={`Cast out: ${item.name}`}
          />
        ))}
      </Hero>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xs/faith:grid-cols-2 @xl/faith:grid-cols-4'>
        <KpiTile
          label='Zeal'
          value={doctrine.zeal}
          icon={Flame}
          tone={zealTone(doctrine.zeal)}
          meter={{ value: doctrine.zeal, max: PERCENT, label: 'Zeal' }}
          hint={`${zeal.label}; above 80 the faith turns fanatic`}
        />
        <KpiTile
          label='Orthodoxy'
          value={doctrine.orthodoxy}
          icon={BookOpen}
          tone='info'
          meter={{
            value: doctrine.orthodoxy,
            max: PERCENT,
            label: 'Orthodoxy',
          }}
          hint={`Drifted ${doctrine.doctrinal_distance} from the founding`}
        />
        <KpiTile
          label='Treasury'
          value={formatInteger(doctrine.treasury)}
          icon={Coins}
          tone='gold'
          meter={{ value: doctrine.tithe_rate, max: PERCENT, label: 'Tithe' }}
          hint={`Tithe of ${doctrine.tithe_rate}% from the faithful`}
        />
        <KpiTile
          label='Clergy'
          value={formatInteger(doctrine.clergy_count)}
          icon={Church}
          tone='verdigris'
          meter={{
            value: doctrine.clergy_quality,
            max: PERCENT,
            label: 'Clergy learning',
          }}
          hint={`Learning ${doctrine.clergy_quality} of 100`}
        />
      </div>
      <DoctrineForm
        key={JSON.stringify([
          doctrine.locked,
          doctrine.judgement,
          doctrine.zeal,
          doctrine.orthodoxy,
          doctrine.tithe_rate,
          doctrine.treasury,
          doctrine.clergy_count,
          doctrine.clergy_quality,
          doctrine.doctrinal_distance,
        ])}
        doctrine={doctrine}
        blocked={blocked}
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/faith:grid-cols-2'>
        <Panel
          title='Why the zeal moves'
          icon={Flame}
          tone='warning'
          hint='What stirs and cools the faithful this epoch'
          actions={
            parts.length > 0 && (
              <ChangeChip
                value={parts.reduce((sum, [, value]) => sum + value, 0)}
                label='Net'
              />
            )
          }
        >
          <div data-surface='ZealWhy' className='flex min-w-0 flex-col'>
            {parts.length === 0 ? (
              <Muted>Nothing stirs the faithful.</Muted>
            ) : (
              <WhyList parts={parts} />
            )}
          </div>
        </Panel>
        <Panel
          title='Clergy'
          icon={Church}
          tone='verdigris'
          hint={`${filled} of ${doctrine.clergy.length} offices filled`}
        >
          <ul className='flex min-w-0 flex-col gap-2'>
            {doctrine.clergy.length === 0 && (
              <Muted>No office is founded.</Muted>
            )}
            {doctrine.clergy.map((office) => {
              const spec = named(CLERGY, office.kind)
              return (
                <li
                  key={office.kind}
                  className='flex min-w-0 items-center gap-2'
                >
                  <Medallion
                    icon={spec.icon}
                    tone={office.holder ? spec.tone : 'muted'}
                    size='sm'
                  />
                  <div className='flex min-w-0 flex-1 flex-col'>
                    <Label truncate>{spec.label}</Label>
                    {office.holder ? (
                      <RefLink node={office.holder} />
                    ) : (
                      <Muted as='span'>Vacant</Muted>
                    )}
                  </div>
                  <Muted
                    as='span'
                    variant='caption'
                  >{`since ${office.since_epoch}`}</Muted>
                </li>
              )
            })}
          </ul>
        </Panel>
      </div>
      <Panel
        title='Tenets'
        icon={ScrollText}
        count={doctrine.tenets.length}
        hint='What the faith holds true, and what it does to the faithful'
      >
        {doctrine.tenets.length === 0 ? (
          <Muted>The faith holds no tenets yet.</Muted>
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/faith:grid-cols-2'>
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
      </Panel>
      <Holdings doctrine={doctrine} />
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/faith:grid-cols-2'>
        <Heresies doctrine={doctrine} blocked={blocked} />
        <Saints doctrine={doctrine} blocked={blocked} />
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
