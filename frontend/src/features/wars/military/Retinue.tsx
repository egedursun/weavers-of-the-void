import { useState } from 'react'
import {
  Banknote,
  CalendarClock,
  Coins,
  DoorOpen,
  Gavel,
  HandCoins,
  Handshake,
  Heart,
  HeartHandshake,
  Lock,
  Shield,
  Skull,
  Sword,
  Undo2,
  UserRound,
  Users,
  Home,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  Medallion,
  StatBar,
  Paged,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker, Held, RecordButtons } from './controls'
import { CONTRACT_STATUS, type RecordRow, nameOf, useRecords } from './depth'
import { type Named, PERCENT, busyOf, cardGrid } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Plain,
  Tag,
} from './parts'
import {
  type Values,
  numbersOf,
  useRecordActions,
  useRecordCreate,
} from './recordHooks'

const COMPANIES = ['people', 'faction', 'settlement', 'army']
const CONTRACT_NUMBERS = [
  'soldiers',
  'pay_per_season',
  'seasons_left',
  'loyalty',
  'unpaid_seasons',
] as const
const LOYALTY_LOW = 30
const CAPTIVE_STATUS: Record<string, Named> = {
  held: { label: 'Held', icon: Lock, tone: 'warning' },
  ransomed: { label: 'Ransomed', icon: HandCoins, tone: 'gold' },
  escaped: { label: 'Escaped', icon: DoorOpen, tone: 'info' },
  executed: { label: 'Executed', icon: Skull, tone: 'danger' },
  turncoat: { label: 'Turned coat', icon: Undo2, tone: 'verdigris' },
  rescued: { label: 'Rescued', icon: Shield, tone: 'success' },
  released: { label: 'Released', icon: Handshake, tone: 'success' },
  ward: { label: 'Raised as a ward', icon: HeartHandshake, tone: 'info' },
  paroled: { label: 'Freed on parole', icon: Gavel, tone: 'gold' },
  married_in: {
    label: 'Married into the captors',
    icon: HeartHandshake,
    tone: 'success',
  },
  adopted: {
    label: 'Adopted',
    icon: Home,
    tone: 'success',
  },
}

function ContractCard({
  row,
  employerId,
  blocked,
}: {
  row: RecordRow
  employerId: number
  blocked: string | null
}) {
  const actions = useRecordActions('contract', row.id, employerId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const status = nameOf(CONTRACT_STATUS, String(row.values.status))
  const company = row.refs.company_entity_id
  const army = row.refs.army_entity_id
  const loyalty = Number(row.values.loyalty ?? 0)
  return (
    <li className='@container/mil flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={Sword} tone={status.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          {company ? (
            <EntityLink kind='entity' id={String(company.id)}>
              {company.name}
            </EntityLink>
          ) : (
            <Text as='span' weight='semibold'>
              A free company
            </Text>
          )}
          <Muted as='span' variant='caption' truncate>
            {army ? `Fighting in ${army.name}` : 'Not yet in the field'}
          </Muted>
        </div>
        <Tag item={status} />
        <Held locked={row.locked} />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 @lg/mil:grid-cols-4'>
        <MiniStat
          icon={Users}
          label='Soldiers'
          value={Number(row.values.soldiers ?? 0)}
          tone='info'
        />
        <MiniStat
          icon={Coins}
          label='Pay a season'
          value={Number(row.values.pay_per_season ?? 0)}
          tone='gold'
        />
        <MiniStat
          icon={CalendarClock}
          label='Seasons left'
          value={Number(row.values.seasons_left ?? 0)}
          tone='muted'
        />
        <MiniStat
          icon={Banknote}
          label='Unpaid'
          value={Number(row.values.unpaid_seasons ?? 0)}
          tone={Number(row.values.unpaid_seasons ?? 0) > 0 ? 'danger' : 'muted'}
        />
      </div>
      <StatBar
        framed
        label='Loyalty'
        icon={Heart}
        value={loyalty}
        max={PERCENT}
        tone={loyalty < LOYALTY_LOW ? 'destructive' : 'success'}
      />
      <Adjust
        title='The contract'
        note='Its soldiers, pay, seasons and temper, where it fights and whether it holds.'
      >
        <FieldGrid>
          <ChoiceField
            label='Standing'
            icon={Gavel}
            value={String(value('status'))}
            table={CONTRACT_STATUS}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, status: next })}
          />
          <NumberField
            label='Soldiers'
            icon={Users}
            value={String(value('soldiers') ?? 0)}
            onChange={(next) => setDraft({ ...draft, soldiers: next })}
          />
          <NumberField
            label='Pay a season'
            icon={Coins}
            value={String(value('pay_per_season') ?? 0)}
            onChange={(next) => setDraft({ ...draft, pay_per_season: next })}
          />
          <NumberField
            label='Seasons left'
            icon={CalendarClock}
            value={String(value('seasons_left') ?? 0)}
            onChange={(next) => setDraft({ ...draft, seasons_left: next })}
          />
          <NumberField
            label='Loyalty'
            icon={Heart}
            value={String(value('loyalty') ?? 0)}
            max={PERCENT}
            onChange={(next) => setDraft({ ...draft, loyalty: next })}
          />
          <NumberField
            label='Seasons unpaid'
            icon={Banknote}
            value={String(value('unpaid_seasons') ?? 0)}
            onChange={(next) => setDraft({ ...draft, unpaid_seasons: next })}
          />
          <EntityPicker
            label='Fights in'
            icon={Sword}
            types={['army']}
            value={
              typeof value('army_entity_id') === 'number'
                ? (value('army_entity_id') as number)
                : null
            }
            onChange={(next) => setDraft({ ...draft, army_entity_id: next })}
            blocked={blocked}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={numbersOf(draft, CONTRACT_NUMBERS)}
          locked={row.locked}
          blocked={blocked}
          removeLabel='Tear up the contract'
        />
      </Adjust>
    </li>
  )
}

export function MercenaryContracts({
  employerId,
  blocked,
}: {
  employerId: number
  blocked: string | null
}) {
  const contracts = useRecords('contract', employerId)
  const create = useRecordCreate('contract', employerId)
  const [company, setCompany] = useState<number | null>(null)
  const [soldiers, setSoldiers] = useState('200')
  const [pay, setPay] = useState('20')
  const [seasons, setSeasons] = useState('4')
  const rows = contracts.data?.rows ?? []
  const busy = busyOf(blocked, create.isPending)
  return (
    <Panel
      title='Sellswords'
      icon={Sword}
      tone='gold'
      count={rows.length}
      hint='Companies sworn for pay, season by season'
    >
      <div
        data-surface='MercenaryContracts'
        className='flex min-w-0 flex-col gap-3'
      >
        {rows.length === 0 ? (
          <EmptyState
            icon={Sword}
            title='No hired swords'
            description='Hire a company; unpaid seasons sour its loyalty until it turns.'
          />
        ) : (
          <ul className={cardGrid(rows.length)}>
            <Paged items={rows} as='li'>
              {(row) => (
                <ContractCard
                  key={row.id}
                  row={row}
                  employerId={employerId}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <Adjust
          title='Hire a company'
          note='Name the company, how many swords and the pay each season.'
          label='Hire a company'
        >
          <FieldGrid>
            <EntityPicker
              label='Company'
              icon={Users}
              types={COMPANIES}
              value={company}
              onChange={setCompany}
              blocked={blocked}
            />
            <NumberField
              label='Soldiers'
              icon={Users}
              value={soldiers}
              min={1}
              onChange={setSoldiers}
            />
            <NumberField
              label='Pay a season'
              icon={Coins}
              value={pay}
              onChange={setPay}
            />
            <NumberField
              label='Seasons'
              icon={CalendarClock}
              value={seasons}
              min={1}
              onChange={setSeasons}
            />
          </FieldGrid>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              create.mutate({
                employer_entity_id: employerId,
                company_entity_id: company,
                soldiers: Math.max(1, Math.round(Number(soldiers) || 1)),
                pay_per_season: Math.round(Number(pay) || 0),
                seasons_left: Math.max(1, Math.round(Number(seasons) || 1)),
              })
            }
          >
            <HandCoins />
            Hire
          </Button>
        </Adjust>
      </div>
    </Panel>
  )
}

function PrisonerCard({
  row,
  captorId,
  blocked,
}: {
  row: RecordRow
  captorId: number
  blocked: string | null
}) {
  const actions = useRecordActions('captive', row.id, captorId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const status = nameOf(CAPTIVE_STATUS, String(row.values.status))
  const captive = row.refs.captive_entity_id
  const married = row.refs.married_entity_id
  const loyalty = Number(row.values.loyalty ?? 0)
  return (
    <li className='@container/mil flex min-w-0 flex-col gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={status.icon} tone={status.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          {captive ? (
            <EntityLink kind='entity' id={String(captive.id)}>
              {captive.name}
            </EntityLink>
          ) : (
            <Text as='span'>A captive</Text>
          )}
          <Muted as='span' variant='caption' truncate>
            {`Taken in epoch ${String(row.values.taken_epoch)}${row.refs.home_entity_id ? ` from ${row.refs.home_entity_id.name}` : ''}`}
          </Muted>
        </div>
        <Tag item={status} />
        <Held locked={row.locked} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {married && (
          <Plain icon={HeartHandshake}>{`Wed to ${married.name}`}</Plain>
        )}
        {row.values.status === 'paroled' && (
          <Plain icon={Gavel}>
            {typeof row.values.oath_id === 'number'
              ? 'Sworn not to fight again'
              : 'Freed without an oath'}
          </Plain>
        )}
        {typeof row.values.ransom_paid === 'number' && (
          <Plain
            icon={HandCoins}
          >{`Ransomed for ${row.values.ransom_paid}`}</Plain>
        )}
      </div>
      <StatBar
        label='Loyalty to the captors'
        icon={Heart}
        value={Math.max(0, loyalty)}
        max={PERCENT}
        tone='verdigris'
      />
      <Adjust
        title='The prisoner'
        note='Their fate, their loyalty, any ransom paid and any marriage made in captivity.'
      >
        <FieldGrid>
          <ChoiceField
            label='Fate'
            icon={Lock}
            value={String(value('status'))}
            table={CAPTIVE_STATUS}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, status: next })}
          />
          <NumberField
            label='Loyalty'
            icon={Heart}
            value={String(value('loyalty') ?? 0)}
            min={-PERCENT}
            max={PERCENT}
            onChange={(next) => setDraft({ ...draft, loyalty: next })}
          />
          <NumberField
            label='Ransom paid'
            icon={HandCoins}
            value={String(value('ransom_paid') ?? 0)}
            onChange={(next) => setDraft({ ...draft, ransom_paid: next })}
          />
          <EntityPicker
            label='Wed to'
            icon={HeartHandshake}
            types={['mortal']}
            value={
              typeof value('married_entity_id') === 'number'
                ? (value('married_entity_id') as number)
                : null
            }
            onChange={(next) => setDraft({ ...draft, married_entity_id: next })}
            blocked={blocked}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={numbersOf(draft, ['loyalty', 'ransom_paid'])}
          locked={row.locked}
          blocked={blocked}
          removeLabel='Strike the record'
        />
      </Adjust>
    </li>
  )
}

export function NamedPrisoners({
  captorId,
  blocked,
}: {
  captorId: number
  blocked: string | null
}) {
  const prisoners = useRecords('captive', captorId)
  const [mortal, setMortal] = useState<number | null>(null)
  const take = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/captive:take', {
          body: { captor_id: captorId, mortal_id: mortal ?? 0 },
        })
      ),
    invalidate: [['military']],
    onDone: () => setMortal(null),
  })
  const rows = prisoners.data?.rows ?? []
  const busy = busyOf(blocked, take.isPending)
  return (
    <Panel
      title='Named prisoners'
      icon={UserRound}
      tone='warning'
      count={rows.length}
      hint='Mortals held by name, for ransom, marriage or worse'
    >
      <div
        data-surface='NamedPrisoners'
        className='flex min-w-0 flex-col gap-3'
      >
        {rows.length === 0 ? (
          <EmptyState
            icon={UserRound}
            title='No one held by name'
            description='Captives taken in battle or by decree appear here.'
          />
        ) : (
          <ul className={cardGrid(rows.length)}>
            <Paged items={rows} as='li'>
              {(row) => (
                <PrisonerCard
                  key={row.id}
                  row={row}
                  captorId={captorId}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <Adjust
          title='Take a captive'
          note='Seize a living mortal and hold them here.'
          label='Take a captive'
        >
          <FieldGrid>
            <EntityPicker
              label='Mortal'
              icon={UserRound}
              types={['mortal']}
              value={mortal}
              onChange={setMortal}
              blocked={blocked}
            />
          </FieldGrid>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null || mortal === null}
            disabledReason={
              busy ?? (mortal === null ? 'Choose a mortal' : undefined)
            }
            onClick={() => take.mutate()}
          >
            <Lock />
            Take
          </Button>
        </Adjust>
      </div>
    </Panel>
  )
}
