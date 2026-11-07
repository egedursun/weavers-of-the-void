import { useState } from 'react'
import {
  Church,
  Megaphone,
  Ban,
  BookOpenCheck,
  Coins,
  Crown,
  Flame,
  Gavel,
  GitFork,
  HandCoins,
  Landmark,
  Lock,
  LockOpen,
  Merge,
  PieChart,
  Plus,
  Save,
  Scale,
  ScrollText,
  Shield,
  Sparkles,
  Trash2,
  UserCog,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  Medallion,
  RangeField,
  StatBar,
  type KpiTone,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { FoundHouse, SealTreaty } from './Covenants'
import { GOVERNMENTS, OFFICES, type Named, named, plain } from './labels'
import {
  AdjustPanel,
  ChoiceGrid,
  Fact,
  NumberField,
  Panel,
  RecordField,
  Tag,
} from './parts'

type Realm = components['schemas']['RealmView']
type Office = Realm['offices'][number]
type Law = components['schemas']['LawView']
type Slice = { id: number; name: string; kind: string; share: number }

const PERCENT = 100
const WORKING = 'Working…'
const RING = 2 * Math.PI * 15.9155
const COMMUNITY_TYPES = ['settlement', 'people'] as const
const MORTALS = ['mortal'] as const
const REALMS = ['polity'] as const
const LENDERS = ['polity', 'faction', 'settlement', 'people'] as const

const OFFICE_POWERS: Record<string, Named & { hint: string }> = {
  rule: {
    label: 'Rule',
    icon: Crown,
    tone: 'gold',
    hint: 'Sits on the throne or rules for it',
  },
  succeed: {
    label: 'Succeed',
    icon: Sparkles,
    tone: 'info',
    hint: 'Stands next in line',
  },
  negotiate: {
    label: 'Negotiate',
    icon: HandCoins,
    tone: 'success',
    hint: 'Courts treaty partners',
  },
  command: {
    label: 'Command',
    icon: Shield,
    tone: 'danger',
    hint: 'Drills the armies',
  },
  treasury: {
    label: 'Treasury',
    icon: Coins,
    tone: 'gold',
    hint: 'Stops taxes leaking',
  },
  judge: {
    label: 'Judge',
    icon: Gavel,
    tone: 'info',
    hint: 'Enforces the laws',
  },
  spy: {
    label: 'Spy',
    icon: BookOpenCheck,
    tone: 'warning',
    hint: 'Runs the spies and forges claims',
  },
  govern: {
    label: 'Govern',
    icon: Landmark,
    tone: 'verdigris',
    hint: 'Holds a province in hand',
  },
  embassy: {
    label: 'Embassy',
    icon: ScrollText,
    tone: 'success',
    hint: 'Wins friends at a foreign court',
  },
  proclaim: {
    label: 'Proclaim',
    icon: Megaphone,
    tone: 'warning',
    hint: 'Cries the ruler’s word and wins the people’s approval',
  },
  preach: {
    label: 'Preach',
    icon: Church,
    tone: 'verdigris',
    hint: 'Carries the realm’s faith into its lands',
  },
}
const LAW_HOLDS: Record<string, Named & { hint: string }> = {
  repeal: {
    label: 'Never repealed',
    icon: Lock,
    tone: 'gold',
    hint: 'No realm, rebel or conqueror strikes it out',
  },
  params: {
    label: 'Terms fixed',
    icon: ScrollText,
    tone: 'info',
    hint: 'Its terms are never rewritten',
  },
  enforcement: {
    label: 'Enforcement fixed',
    icon: Gavel,
    tone: 'warning',
    hint: 'Kept as hard as you set it',
  },
  basis: {
    label: 'Basis fixed',
    icon: Scale,
    tone: 'verdigris',
    hint: 'Its source of authority stays',
  },
}
const SLICE_TONES: KpiTone[] = [
  'gold',
  'success',
  'info',
  'warning',
  'danger',
  'verdigris',
]
const STROKES: Record<KpiTone, string> = {
  gold: 'stroke-primary',
  success: 'stroke-success',
  info: 'stroke-info',
  warning: 'stroke-warning',
  danger: 'stroke-destructive',
  verdigris: 'stroke-info',
  muted: 'stroke-muted-foreground',
}

function toneAt(index: number): KpiTone {
  return SLICE_TONES[index % SLICE_TONES.length] ?? 'gold'
}

function asNumber(value: string, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function PowerBalance({
  slices,
  title = 'Power balance',
}: {
  slices: Slice[]
  title?: string
}) {
  const total = slices.reduce((sum, slice) => sum + slice.share, 0)
  const lengths = slices.map((slice) =>
    total > 0 ? (slice.share / total) * RING : 0
  )
  const offsets = lengths.map((_, index) =>
    lengths.slice(0, index).reduce((sum, value) => sum + value, 0)
  )
  return (
    <Panel
      title={title}
      icon={PieChart}
      tone='verdigris'
      hint='Who holds sway over the realm’s decisions'
      count={slices.length}
    >
      <div
        data-surface='PowerBalance'
        className='flex min-w-0 flex-col gap-3 @md/realm:flex-row @md/realm:items-center'
      >
        {slices.length === 0 ? (
          <EmptyState
            icon={PieChart}
            title='No faction holds sway'
            description='The realm decides by its rulers and its people alone.'
          />
        ) : (
          <svg
            viewBox='0 0 42 42'
            role='img'
            aria-label={title}
            className='size-portrait-lg shrink-0 -rotate-90'
          >
            <circle
              cx='21'
              cy='21'
              r='15.9155'
              fill='none'
              className='stroke-muted'
              strokeWidth='6'
            />
            {slices.map((slice, index) => (
              <circle
                key={slice.id}
                cx='21'
                cy='21'
                r='15.9155'
                fill='none'
                strokeWidth='6'
                strokeDasharray={`${lengths[index] ?? 0} ${RING - (lengths[index] ?? 0)}`}
                strokeDashoffset={-(offsets[index] ?? 0)}
                className={STROKES[toneAt(index)]}
              />
            ))}
          </svg>
        )}
        <ul className='flex min-w-0 flex-1 flex-col gap-1.5'>
          {slices.map((slice, index) => (
            <li key={slice.id} className='flex min-w-0 items-center gap-2'>
              <Medallion icon={PieChart} tone={toneAt(index)} size='sm' />
              <EntityLink kind='entity' id={String(slice.id)}>
                {slice.name}
              </EntityLink>
              {slice.kind && (
                <Badge size='sm' variant='secondary'>
                  {plain({}, slice.kind)}
                </Badge>
              )}
              <Badge
                size='sm'
                variant='outline'
                className='ml-auto'
              >{`${slice.share}%`}</Badge>
            </li>
          ))}
        </ul>
      </div>
    </Panel>
  )
}

export function LawProtection({
  law,
  blocked,
}: {
  law: Law
  blocked: string | null
}) {
  const protect = useGodAction({
    run: (change: { key: string; on: boolean }) =>
      unwrap(
        api.POST('/api/actions/law:protect', {
          body: {
            law_id: law.id,
            hold: change.on ? [change.key] : [],
            release: change.on ? [] : [change.key],
          },
        })
      ),
  })
  const busy = blocked ?? (protect.isPending ? WORKING : null)
  return (
    <div
      data-surface='LawProtection'
      className='grid min-w-0 grid-cols-1 gap-2 @md/realm:grid-cols-2'
    >
      {Object.entries(LAW_HOLDS).map(([key, spec]) => {
        const held = law.locked.includes(key)
        return (
          <label
            key={key}
            className='flex min-w-0 items-center gap-2 rounded-md border p-2'
          >
            <Medallion
              icon={held ? spec.icon : LockOpen}
              tone={held ? spec.tone : 'muted'}
              size='sm'
            />
            <div className='flex min-w-0 flex-1 flex-col'>
              <Label truncate>{spec.label}</Label>
              <Muted>{spec.hint}</Muted>
            </div>
            <Switch
              checked={held}
              disabled={busy !== null}
              aria-label={spec.label}
              onCheckedChange={(on) => protect.mutate({ key, on })}
            />
          </label>
        )
      })}
    </div>
  )
}

function OfficeEditor({
  office,
  blocked,
}: {
  office: Office
  blocked: string | null
}) {
  const [title, setTitle] = useState(office.title ?? '')
  const [powers, setPowers] = useState<string[]>(office.powers)
  const [holder, setHolder] = useState<number | null>(office.holder_id)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/office:edit', {
          body: {
            office_id: office.id,
            title,
            powers,
            holder_id: holder ?? undefined,
            vacate: holder === null && office.holder_id !== null,
            release: [],
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/office:edit', {
          body: { office_id: office.id, vacate: false, release: office.locked },
        })
      ),
  })
  const abolish = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/office:abolish', {
          body: { office_id: office.id },
        })
      ),
  })
  const busy =
    blocked ??
    (save.isPending || abolish.isPending || release.isPending ? WORKING : null)
  const spec = named(OFFICES, office.kind)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text truncate>{office.title ?? spec.label}</Text>
          <div className='flex min-w-0 flex-wrap gap-1'>
            {office.powers.map((power) => (
              <Tag key={power} spec={named(OFFICE_POWERS, power)} />
            ))}
            {office.target && (
              <Badge
                size='sm'
                variant='outline'
              >{`At the court of ${office.target}`}</Badge>
            )}
          </div>
        </div>
        {office.holder_id !== null && office.holder && (
          <EntityLink kind='entity' id={String(office.holder_id)}>
            {office.holder}
          </EntityLink>
        )}
      </div>
      <AdjustPanel
        trigger='Shape'
        title='Shape this office'
        note='Name it, give or take its powers, seat a holder, or abolish the seat.'
      >
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Title</Label>
          <Input
            value={title}
            disabled={busy !== null}
            onChange={(event) => setTitle(event.target.value)}
          />
        </div>
        <div
          role='group'
          aria-label='Powers'
          className='flex min-w-0 flex-wrap gap-2'
        >
          {Object.entries(OFFICE_POWERS).map(([key, power]) => (
            <Button
              key={key}
              size='sm'
              variant={powers.includes(key) ? 'default' : 'outline'}
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() =>
                setPowers((current) =>
                  current.includes(key)
                    ? current.filter((item) => item !== key)
                    : [...current, key]
                )
              }
            >
              <power.icon />
              {power.label}
            </Button>
          ))}
        </div>
        <RecordField
          label='Holder'
          types={MORTALS}
          value={holder}
          onChange={setHolder}
          blocked={busy}
        />
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? 'Choose every field first'}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Keep the office so
          </Button>
          {office.locked.length > 0 && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() => release.mutate(undefined)}
            >
              <LockOpen />
              Release the hold
            </Button>
          )}
          {office.kind !== 'ruler' && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() => abolish.mutate(undefined)}
            >
              <Trash2 />
              Abolish it
            </Button>
          )}
        </div>
      </AdjustPanel>
    </li>
  )
}

function CreateOffice({
  realm,
  blocked,
}: {
  realm: Realm
  blocked: string | null
}) {
  const [kind, setKind] = useState('chancellor')
  const [title, setTitle] = useState('')
  const [holder, setHolder] = useState<number | null>(null)
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/office:create', {
          body: {
            polity_id: realm.id,
            kind: kind as Office['kind'],
            title: title || undefined,
            holder_id: holder ?? undefined,
          },
        })
      ),
  })
  const busy = blocked ?? (create.isPending ? WORKING : null)
  const choices = Object.fromEntries(
    Object.entries(OFFICES).filter(([key]) => key !== 'ruler')
  )
  return (
    <AdjustPanel
      trigger='Create an office'
      title='Create an office'
      note='A new seat of power: its kind gives its first powers; you may rename it.'
    >
      <ChoiceGrid
        label='Kind of office'
        table={choices}
        value={kind}
        blocked={busy}
        onPick={setKind}
      />
      <div className='flex min-w-0 flex-col gap-1'>
        <Label>Title</Label>
        <Input
          value={title}
          placeholder='Lord of the Granaries'
          disabled={busy !== null}
          onChange={(event) => setTitle(event.target.value)}
        />
      </div>
      <RecordField
        label='First holder'
        types={MORTALS}
        value={holder}
        onChange={setHolder}
        blocked={busy}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? 'Choose every field first'}
        onClick={() => create.mutate(undefined)}
      >
        <Plus />
        Create the office
      </Button>
    </AdjustPanel>
  )
}

function Purse({ realm, blocked }: { realm: Realm; blocked: string | null }) {
  const [lender, setLender] = useState<number | null>(null)
  const [principal, setPrincipal] = useState('100')
  const [interest, setInterest] = useState('10')
  const [epochs, setEpochs] = useState('5')
  const lend = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:loan', {
          body: {
            polity_id: realm.id,
            lender_id: lender ?? 0,
            principal: asNumber(principal, 1),
            interest_pct: asNumber(interest, 0),
            epochs: asNumber(epochs, 1),
          },
        })
      ),
  })
  const forgive = useGodAction({
    run: (loanId: number) =>
      unwrap(
        api.POST('/api/actions/loan:edit', {
          body: { loan_id: loanId, status: 'forgiven' },
        })
      ),
  })
  const busy = blocked ?? (lend.isPending || forgive.isPending ? WORKING : null)
  return (
    <Panel
      title='Lenders'
      icon={HandCoins}
      tone='gold'
      hint='Who the crown owes, and what default would cost'
      count={realm.loans.length}
    >
      {realm.loans.length === 0 && <Muted>The crown owes no one.</Muted>}
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={realm.loans} as='li'>
          {(loan) => (
            <li
              key={loan.id}
              className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border p-2'
            >
              <Medallion
                icon={Coins}
                tone={
                  loan.status === 'defaulted'
                    ? 'danger'
                    : loan.status === 'open'
                      ? 'warning'
                      : 'success'
                }
                size='sm'
              />
              <EntityLink kind='entity' id={String(loan.lender_id)}>
                {loan.lender}
              </EntityLink>
              <Badge
                size='sm'
                variant='secondary'
              >{`${loan.principal} at ${loan.interest_pct}%`}</Badge>
              <Badge
                size='sm'
                variant='outline'
              >{`Repaid ${loan.repaid}`}</Badge>
              <Badge
                size='sm'
                variant='outline'
              >{`Due epoch ${loan.due_epoch}`}</Badge>
              <Badge
                size='sm'
                variant={
                  loan.status === 'defaulted' ? 'destructive' : 'secondary'
                }
              >
                {plain({}, loan.status)}
              </Badge>
              {loan.status === 'open' && (
                <Button
                  size='sm'
                  variant='outline'
                  className='ml-auto'
                  disabled={busy !== null}
                  disabledReason={busy ?? 'Choose every field first'}
                  onClick={() => forgive.mutate(loan.id)}
                >
                  <Ban />
                  Forgive
                </Button>
              )}
            </li>
          )}
        </Paged>
      </ul>
      <AdjustPanel
        trigger='Borrow'
        title='Have a lender lend to the crown'
        note='The treasury fills now; the debt and its interest fall due later.'
      >
        <RecordField
          label='Lender'
          types={LENDERS}
          value={lender}
          onChange={setLender}
          blocked={busy}
        />
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/realm:grid-cols-3'>
          <NumberField
            label='Principal'
            icon={Coins}
            value={principal}
            min={1}
            blocked={busy}
            onChange={setPrincipal}
          />
          <NumberField
            label='Interest %'
            icon={Scale}
            value={interest}
            min={0}
            max={PERCENT}
            blocked={busy}
            onChange={setInterest}
          />
          <NumberField
            label='Epochs to repay'
            icon={Flame}
            value={epochs}
            min={1}
            blocked={busy}
            onChange={setEpochs}
          />
        </div>
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null || lender === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => lend.mutate(undefined)}
        >
          <HandCoins />
          Borrow
        </Button>
      </AdjustPanel>
    </Panel>
  )
}

function Repute({ realm, blocked }: { realm: Realm; blocked: string | null }) {
  const repute = realm.ruler_repute
  const [honour, setHonour] = useState(repute?.honour ?? PERCENT / 2)
  const [infamy, setInfamy] = useState(repute?.infamy ?? 0)
  const ruler = realm.ruler
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mortal:repute', {
          body: { mortal_id: ruler?.id ?? 0, honour, infamy },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mortal:repute', {
          body: { mortal_id: ruler?.id ?? 0, release: ['honour', 'infamy'] },
        })
      ),
  })
  if (ruler === null) return null
  const busy = blocked ?? (save.isPending || release.isPending ? WORKING : null)
  return (
    <Panel
      title='The ruler’s name'
      icon={Crown}
      tone='gold'
      hint='Honour and infamy, read apart from renown'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/realm:grid-cols-2'>
        <StatBar
          label='Honour'
          value={repute?.honour ?? PERCENT / 2}
          max={PERCENT}
          icon={Shield}
          tone='success'
        />
        <StatBar
          label='Infamy'
          value={repute?.infamy ?? 0}
          max={PERCENT}
          icon={Flame}
          tone='destructive'
        />
      </div>
      <AdjustPanel
        trigger='Judge the ruler'
        title='Set the ruler’s honour and infamy'
        note='Held values stay as you set them until you release them.'
        hold={(repute?.locked.length ?? 0) > 0}
        onHold={(on) =>
          on ? save.mutate(undefined) : release.mutate(undefined)
        }
      >
        <RangeField
          label='Honour'
          icon={Shield}
          value={honour}
          min={0}
          max={PERCENT}
          level={`${honour}`}
          lowLabel='Shamed'
          highLabel='Spotless'
          onChange={setHonour}
        />
        <RangeField
          label='Infamy'
          icon={Flame}
          value={infamy}
          min={0}
          max={PERCENT}
          level={`${infamy}`}
          lowLabel='Unknown'
          highLabel='Execrated'
          onChange={setInfamy}
        />
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Hold these values
        </Button>
      </AdjustPanel>
    </Panel>
  )
}

function Vassals({ realm, blocked }: { realm: Realm; blocked: string | null }) {
  const [vassal, setVassal] = useState<number | null>(null)
  const [tribute, setTribute] = useState('10')
  const [levy, setLevy] = useState('10')
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/vassal:create', {
          body: {
            vassal_id: vassal ?? 0,
            overlord_id: realm.id,
            tribute_pct: asNumber(tribute, 0),
            levy_pct: asNumber(levy, 0),
          },
        })
      ),
  })
  const edit = useGodAction({
    run: (change: { id: number; key: string; value: number | null }) =>
      unwrap(
        api.POST('/api/actions/vassal:edit', {
          body:
            change.value === null
              ? { vassal_id: change.id, release: [change.key] }
              : { vassal_id: change.id, [change.key]: change.value },
        })
      ),
  })
  const busy = blocked ?? (create.isPending || edit.isPending ? WORKING : null)
  const terms = [
    ...realm.vassal_terms,
    ...(realm.overlord_terms ? [realm.overlord_terms] : []),
  ]
  return (
    <Panel
      title='Vassals and overlords'
      icon={GitFork}
      tone='info'
      hint='Tribute, levies and loyalty owed by treaty'
      count={terms.length}
    >
      {terms.length === 0 && <Muted>No realm owes or is owed fealty.</Muted>}
      <ul className='flex min-w-0 flex-col gap-3'>
        {terms.map((term) => (
          <li
            key={term.id}
            className='flex min-w-0 flex-col gap-2 rounded-md border p-2'
          >
            <Fact
              icon={GitFork}
              label={term.id === realm.id ? 'Our overlord' : 'Vassal'}
            >
              <EntityLink
                kind='entity'
                id={String(term.id === realm.id ? term.overlord_id : term.id)}
              >
                {term.id === realm.id
                  ? (realm.overlord?.name ?? '')
                  : term.name}
              </EntityLink>
            </Fact>
            <div className='grid min-w-0 grid-cols-1 gap-2 @md/realm:grid-cols-3'>
              <StatBar
                label='Tribute %'
                value={term.tribute_pct}
                max={PERCENT}
                icon={Coins}
                tone='default'
              />
              <StatBar
                label='Levy %'
                value={term.levy_pct}
                max={PERCENT}
                icon={Shield}
                tone='warning'
              />
              <StatBar
                label='Loyalty'
                value={term.loyalty}
                max={PERCENT}
                icon={Crown}
                tone={term.loyalty < 30 ? 'destructive' : 'success'}
              />
            </div>
            <AdjustPanel
              trigger='Set terms'
              title='Set the terms of fealty'
              note='Each value you set is held until released.'
            >
              {(['tribute_pct', 'levy_pct', 'loyalty'] as const).map((key) => (
                <div key={key} className='flex min-w-0 items-end gap-2'>
                  <RangeField
                    label={plain({}, key.replace('_pct', ''))}
                    icon={
                      key === 'loyalty'
                        ? Crown
                        : key === 'levy_pct'
                          ? Shield
                          : Coins
                    }
                    value={term[key]}
                    min={0}
                    max={PERCENT}
                    level={`${term[key]}%`}
                    lowLabel='None'
                    highLabel='All'
                    onChange={(value) =>
                      edit.mutate({ id: term.id, key, value })
                    }
                  />
                  {term.locked.includes(key) && (
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? 'Choose every field first'}
                      onClick={() =>
                        edit.mutate({ id: term.id, key, value: null })
                      }
                    >
                      <LockOpen />
                      Release
                    </Button>
                  )}
                </div>
              ))}
            </AdjustPanel>
          </li>
        ))}
      </ul>
      <AdjustPanel
        trigger='Take a vassal'
        title='Make a realm our vassal'
        note='A vassalage treaty is sealed; tribute and levies follow it each age.'
      >
        <RecordField
          label='Vassal realm'
          types={REALMS}
          value={vassal}
          onChange={setVassal}
          blocked={busy}
        />
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/realm:grid-cols-2'>
          <NumberField
            label='Tribute %'
            icon={Coins}
            value={tribute}
            min={0}
            max={PERCENT}
            blocked={busy}
            onChange={setTribute}
          />
          <NumberField
            label='Levy %'
            icon={Shield}
            value={levy}
            min={0}
            max={PERCENT}
            blocked={busy}
            onChange={setLevy}
          />
        </div>
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null || vassal === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => create.mutate(undefined)}
        >
          <GitFork />
          Bind the vassal
        </Button>
      </AdjustPanel>
    </Panel>
  )
}

function Sentences({ realm }: { realm: Realm }) {
  return (
    <Panel
      title='Justice done'
      icon={Gavel}
      tone='danger'
      hint='Every sentence passed under the realm’s laws'
      count={realm.sentences.length}
    >
      {realm.sentences.length === 0 && <Muted>No one has been judged.</Muted>}
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Paged items={realm.sentences} as='li'>
          {(item) => (
            <li
              key={item.id}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Badge size='sm' variant='outline'>{`Epoch ${item.epoch}`}</Badge>
              <EntityLink kind='entity' id={String(item.mortal_id)}>
                {item.mortal}
              </EntityLink>
              <Badge size='sm' variant='secondary'>
                {plain({}, item.crime)}
              </Badge>
              <Badge
                size='sm'
                variant={item.penalty === 'death' ? 'destructive' : 'warning'}
              >
                {plain({}, item.penalty)}
              </Badge>
            </li>
          )}
        </Paged>
      </ul>
    </Panel>
  )
}

export function FoundRealm({ blocked }: { blocked: string | null }) {
  const [core, setCore] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [government, setGovernment] = useState('monarchy')
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:found', {
          body: {
            core_id: core ?? 0,
            name: name || undefined,
            government: government as Realm['government'],
          },
        })
      ),
  })
  const busy = blocked ?? (found.isPending ? WORKING : null)
  return (
    <div data-surface='FoundRealm' className='flex min-w-0 flex-col gap-3'>
      <RecordField
        label='Heartland'
        types={COMMUNITY_TYPES}
        value={core}
        onChange={setCore}
        blocked={busy}
      />
      <div className='flex min-w-0 flex-col gap-1'>
        <Label>Name</Label>
        <Input
          value={name}
          placeholder='The Kingdom of the Salt Coast'
          disabled={busy !== null}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <ChoiceGrid
        label='Government'
        table={GOVERNMENTS}
        value={government}
        blocked={busy}
        onPick={setGovernment}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || core === null}
        disabledReason={busy ?? 'Choose every field first'}
        onClick={() => found.mutate(undefined)}
      >
        <Crown />
        Found the realm
      </Button>
    </div>
  )
}

function SplitRealm({
  realm,
  blocked,
}: {
  realm: Realm
  blocked: string | null
}) {
  const [picked, setPicked] = useState<number[]>([])
  const split = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:split', {
          body: { polity_id: realm.id, member_ids: picked },
        })
      ),
  })
  const busy = blocked ?? (split.isPending ? WORKING : null)
  const lands = realm.members.filter((member) => member.id !== realm.core?.id)
  return (
    <div data-surface='SplitRealm' className='flex min-w-0 flex-col gap-2'>
      {lands.length === 0 && (
        <Muted>Only the heartland remains; nothing can break away.</Muted>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Paged items={lands}>
          {(member) => (
            <Button
              key={member.id}
              size='sm'
              variant={picked.includes(member.id) ? 'default' : 'outline'}
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() =>
                setPicked((current) =>
                  current.includes(member.id)
                    ? current.filter((item) => item !== member.id)
                    : [...current, member.id]
                )
              }
            >
              {member.name}
            </Button>
          )}
        </Paged>
      </div>
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || picked.length === 0}
        disabledReason={busy ?? 'Choose every field first'}
        onClick={() => split.mutate(undefined)}
      >
        <GitFork />
        Set these lands free
      </Button>
    </div>
  )
}

function MergeRealms({
  realm,
  blocked,
}: {
  realm: Realm
  blocked: string | null
}) {
  const [into, setInto] = useState<number | null>(null)
  const merge = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:merge', {
          body: { polity_id: realm.id, into_id: into ?? 0 },
        })
      ),
  })
  const dissolve = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:dissolve', {
          body: { polity_id: realm.id },
        })
      ),
  })
  const busy =
    blocked ?? (merge.isPending || dissolve.isPending ? WORKING : null)
  return (
    <div data-surface='MergeRealms' className='flex min-w-0 flex-col gap-2'>
      <RecordField
        label='Join it to'
        types={REALMS}
        value={into}
        onChange={setInto}
        blocked={busy}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || into === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => merge.mutate(undefined)}
        >
          <Merge />
          Merge the realms
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => dissolve.mutate(undefined)}
        >
          <Trash2 />
          Dissolve this realm
        </Button>
      </div>
    </div>
  )
}

export function Statecraft({
  realm,
  blocked,
}: {
  realm: Realm
  blocked: string | null
}) {
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <PowerBalance slices={realm.power_balance} />
      <Panel
        title='Seats of power'
        icon={UserCog}
        tone='gold'
        hint='Every office, its powers and who holds it'
        count={realm.offices.length}
      >
        <ul className='grid min-w-0 grid-cols-1 gap-2 @2xl/realm:grid-cols-2'>
          <Paged items={realm.offices} as='li'>
            {(office) => (
              <OfficeEditor key={office.id} office={office} blocked={blocked} />
            )}
          </Paged>
        </ul>
        <CreateOffice realm={realm} blocked={blocked} />
      </Panel>
      <div className='grid min-w-0 grid-cols-1 gap-4 @2xl/realm:grid-cols-2'>
        <Repute realm={realm} blocked={blocked} />
        <Purse realm={realm} blocked={blocked} />
      </div>
      <Vassals realm={realm} blocked={blocked} />
      <Sentences realm={realm} />
      <Panel
        title='Shape the realm'
        icon={Landmark}
        tone='verdigris'
        hint='Break lands away, join realms, or found a new one'
      >
        <AdjustPanel
          trigger='Split lands off'
          title='Split lands off the realm'
          note='The chosen lands stand alone; they keep their rulers.'
        >
          <SplitRealm realm={realm} blocked={blocked} />
        </AdjustPanel>
        <AdjustPanel
          trigger='Merge or dissolve'
          title='Merge into another realm or dissolve'
          note='Merging binds the heartland under the other realm’s lord.'
        >
          <MergeRealms realm={realm} blocked={blocked} />
        </AdjustPanel>
        <AdjustPanel
          trigger='Found a realm'
          title='Found a new realm'
          note='The heartland breaks from any lord and becomes the seat of a new realm.'
        >
          <FoundRealm blocked={blocked} />
        </AdjustPanel>
        <AdjustPanel
          trigger='Found a house'
          title='Found a noble house'
          note='The founder heads a new house; their kin gather to it.'
        >
          <FoundHouse blocked={blocked} />
        </AdjustPanel>
        <AdjustPanel
          trigger='Seal a treaty'
          title='Seal a treaty'
          note='Choose its kind, parties and clauses; it binds from this age.'
        >
          <SealTreaty firstParty={realm.core?.id ?? null} blocked={blocked} />
        </AdjustPanel>
      </Panel>
    </div>
  )
}
