import { useState } from 'react'
import {
  ArrowRight,
  CalendarClock,
  Coins,
  Crown,
  Gavel,
  Gem,
  HandCoins,
  Landmark,
  Percent,
  Plus,
  Save,
  Scale,
  ScrollText,
  ShieldCheck,
  Trash2,
  TrendingDown,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { type ActProp } from '@/api/mutation'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  AttributeTile,
  EmptyState,
  EntityLink,
  IconStat,
  LoadingBlock,
  Medallion,
  MiniStat,
  Paged,
  PagedList,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import {
  AdjustPanel,
  FIELD_GRID,
  NumberField,
  PartHeader,
} from '@/features/entity/economy/EntityEconomy'
import {
  ECONOMY_REFRESH,
  useCurrencies,
  useDebtLaws,
  useDebtsLedger,
} from '@/features/entity/economy/api'
import {
  DEBT_REMEDY,
  type DebtRemedy,
  LOAN_STATUS,
  type LoanStatus,
  CURRENCY_ISSUER,
  MATERIAL_LABEL,
  type MaterialKind,
  MONEY_BACKING,
  MONEY_FORM,
  type Named,
} from '@/features/entity/economy/labels'
import {
  FORM_CARD,
  NONE,
  useBusy,
  useKindChoices,
  whole,
} from '@/features/entity/economy/model'
import {
  ChoiceSelect,
  ConfirmButton,
  EntityChoice,
  HeldBadge,
  ReleaseButton,
  TextField,
} from '@/features/entity/economy/parts'
import { SwitchField } from '@/features/entity/wilds/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { Opener } from './Opener'

type Currency = components['schemas']['CurrencyView']
type MoneyForm = components['schemas']['MoneyForm']
type MoneyBacking = components['schemas']['MoneyBacking']
type CurrencyIssuer = components['schemas']['CurrencyIssuer']
const METAL_FORMS: ReadonlySet<string> = new Set(['coin', 'commodity'])

function metalsAllowed(form: string): boolean {
  return METAL_FORMS.has(form)
}
type Loan = components['schemas']['LoanView']
type Debt = components['schemas']['DebtView']
type DebtLaw = components['schemas']['DebtLawView']

const PERCENT = 100
const LOW = 50
const PAGE = 12
const ISSUER_TYPES = ['people', 'settlement', 'faction', 'polity'] as const
const LENDER_TYPES = ['faction', 'people', 'settlement', 'polity'] as const
const BORROWER_TYPES = ['people', 'settlement', 'faction', 'polity'] as const
const LAW_HOLDER_TYPES = ['polity', 'settlement', 'people', 'cult'] as const
const DEFAULT_JUBILEE = '7'
const PURPOSE: Record<string, string> = {
  war: 'to wage war',
  trade: 'for trade',
  famine: 'against famine',
  building: 'to build',
  ransom: 'to pay a ransom',
  tribute: 'to pay tribute',
}
const PURPOSE_CHOICES: Record<string, Named> = {
  war: { label: 'To wage war', icon: Crown, tone: 'danger' },
  trade: { label: 'For trade', icon: Scale, tone: 'gold' },
  famine: { label: 'Against famine', icon: HandCoins, tone: 'warning' },
  building: { label: 'To build', icon: Landmark, tone: 'info' },
  ransom: { label: 'To pay a ransom', icon: Coins, tone: 'warning' },
  tribute: { label: 'To pay tribute', icon: Gem, tone: 'gold' },
}
const STATUS_CHOICES: Record<string, Named> = { ...LOAN_STATUS }
const REMEDY_CHOICES: Record<string, Named> = Object.fromEntries(
  Object.entries(DEBT_REMEDY).map(([key, item]) => [
    key,
    { label: item.label, icon: item.icon, tone: item.tone },
  ])
)

function plainWords(value: string): string {
  return value.replaceAll('_', ' ')
}

function metalWord(metal: string): string {
  return (
    MATERIAL_LABEL[metal as MaterialKind] ?? plainWords(metal)
  ).toLowerCase()
}

function CurrencyCard({
  currency,
  worldId,
}: {
  currency: Currency
  worldId: number | null
}) {
  const [name, setName] = useState(currency.name)
  const [metal, setMetal] = useState<string>(currency.metal ?? '')
  const [purity, setPurity] = useState(String(currency.purity))
  const [trust, setTrust] = useState(String(currency.trust))
  const [supply, setSupply] = useState(String(currency.supply))
  const [hold, setHold] = useState(currency.held)
  const [form, setForm] = useState<string>(currency.form)
  const [backing, setBacking] = useState<string>(currency.backing)
  const [issuerKind, setIssuerKind] = useState<string>(currency.issuer_kind)
  const [convertible, setConvertible] = useState(currency.convertible)
  const metals = useKindChoices(worldId)
  const metalBlocked = metalsAllowed(form)
    ? null
    : `${MONEY_FORM[form as MoneyForm].label} is not made of metal.`
  const edit = useGodAction({
    writes: [{ lever: 'currency:edit' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:edit', {
          body: {
            currency_id: currency.id,
            name: name.trim() || null,
            metal:
              metal && metalsAllowed(form) ? (metal as MaterialKind) : null,
            purity: whole(purity, PERCENT),
            trust: whole(trust, PERCENT),
            supply: whole(supply),
            form: form as MoneyForm,
            backing: backing as MoneyBacking,
            issuer_kind: issuerKind as CurrencyIssuer,
            convertible,
            hold,
          },
        })
      ),
  })
  const debase = useGodAction({
    writes: [{ lever: 'currency:debase' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:debase', {
          body: { currency_id: currency.id },
        })
      ),
  })
  const release = useGodAction({
    writes: [{ lever: 'currency:release' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:release', {
          body: { currency_id: currency.id },
        })
      ),
  })
  const remove = useGodAction({
    writes: [{ lever: 'currency:delete' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:delete', {
          body: { currency_id: currency.id },
        })
      ),
  })
  const busy = useBusy(
    null,
    edit.isPending,
    debase.isPending,
    release.isPending,
    remove.isPending
  )
  const debased = currency.debased_epoch !== null
  return (
    <li className='@container/coin flex h-full min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Coins} tone={debased ? 'danger' : 'gold'} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text weight='semibold' truncate>
            {currency.name}
          </Text>
          <Muted variant='caption'>
            {`${MONEY_FORM[currency.form].label} of `}
            <EntityLink kind='entity' id={String(currency.issuer_id)}>
              {currency.issuer_name}
            </EntityLink>
            {currency.metal === null
              ? `, ${CURRENCY_ISSUER[currency.issuer_kind].label.toLowerCase()}, since epoch ${currency.minted_epoch}`
              : ` in ${metalWord(currency.metal)}, epoch ${currency.minted_epoch}`}
          </Muted>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge variant='outline'>
              <ShieldCheck />
              {`Backed by ${MONEY_BACKING[currency.backing].label.toLowerCase()}`}
            </Badge>
            <Badge variant={currency.convertible ? 'success' : 'outline'}>
              <ArrowRight />
              {currency.convertible
                ? 'Can be exchanged for its backing'
                : 'Cannot be exchanged for its backing'}
            </Badge>
          </div>
        </div>
        <div className='flex min-w-0 flex-wrap justify-end gap-1.5'>
          <HeldBadge held={currency.held} />
          {debased ? (
            <Badge variant='destructive'>
              <TrendingDown />
              {`Debased in epoch ${currency.debased_epoch}`}
            </Badge>
          ) : (
            <Badge variant='success'>
              <Coins />
              Sound
            </Badge>
          )}
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/coin:grid-cols-4'>
        <AttributeTile
          icon={Gem}
          abbr='Purity'
          label='Purity of the metal'
          value={currency.purity}
          max={PERCENT}
          tone={currency.purity < LOW ? 'destructive' : 'default'}
          hint='Debasing thins the metal'
        />
        <AttributeTile
          icon={Scale}
          abbr='Trust'
          label='Trust of those who use it'
          value={currency.trust}
          max={PERCENT}
          tone={currency.trust < LOW ? 'destructive' : 'success'}
          hint='Low trust drives people back to barter'
        />
        <MiniStat
          icon={HandCoins}
          tone='gold'
          label='Coins abroad'
          value={formatInteger(currency.supply)}
        />
        <MiniStat
          icon={Users}
          tone='info'
          label='Peoples using it'
          value={currency.users.length}
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <ReleaseButton
            act={release}
            held={currency.held}
            busy={busy}
            onRelease={() => release.mutate(undefined)}
          />
          <ConfirmButton
            act={remove}
            icon={Trash2}
            label='Melt it down'
            title={`Melt down ${currency.name}?`}
            description='The coin is gone: everyone who counts in it falls back to barter or another coin.'
            confirm='Melt it'
            busy={busy}
            onConfirm={() => remove.mutate(undefined)}
          />
        </div>
        <AdjustPanel
          acts={[edit, debase]}
          label='Adjust the coin'
          title={`Strike ${currency.name} anew`}
          note='Rename it, strike it in another metal, set its purity and trust from 0 to 100 and how many coins are abroad, or debase it at a stroke.'
          hold={hold}
          onHold={setHold}
        >
          <div className={cn(FIELD_GRID, '@md/coin:grid-cols-2')}>
            <TextField
              label={`${currency.name} name`}
              value={name}
              onChange={setName}
            />
            <ChoiceSelect
              label='Metal'
              value={metalsAllowed(form) ? metal : ''}
              table={metals}
              blocked={busy ?? metalBlocked}
              placeholder={metalBlocked ?? undefined}
              onPick={setMetal}
            />
            <ChoiceSelect
              label='Form of money'
              value={form}
              table={MONEY_FORM}
              blocked={busy}
              onPick={setForm}
            />
            <ChoiceSelect
              label='Backed by'
              value={backing}
              table={MONEY_BACKING}
              blocked={busy}
              onPick={setBacking}
            />
            <ChoiceSelect
              label='Issued by'
              value={issuerKind}
              table={CURRENCY_ISSUER}
              blocked={busy}
              onPick={setIssuerKind}
            />
            <SwitchField
              label='Can be exchanged for its backing'
              checked={convertible}
              disabled={busy !== null}
              onChange={setConvertible}
            />
          </div>
          <div className={cn(FIELD_GRID, 'grid-cols-3')}>
            <NumberField
              label='Purity'
              aria={`${currency.name} Purity`}
              value={purity}
              max={PERCENT}
              onChange={setPurity}
            />
            <NumberField
              label='Trust'
              aria={`${currency.name} Trust`}
              value={trust}
              max={PERCENT}
              onChange={setTrust}
            />
            <NumberField
              label='Coins'
              aria={`${currency.name} Coins`}
              value={supply}
              onChange={setSupply}
            />
          </div>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              act={edit}
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => edit.mutate(undefined)}
            >
              <Save />
              Set the coin
            </Button>
            <Button
              act={debase}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => debase.mutate(undefined)}
            >
              <TrendingDown />
              Debase it
            </Button>
          </div>
        </AdjustPanel>
      </div>
    </li>
  )
}

export function CoinForge({
  worldId,
  onDone,
}: {
  worldId: number | null
  onDone?: () => void
}) {
  const [issuer, setIssuer] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [metal, setMetal] = useState<string>('')
  const [purity, setPurity] = useState('90')
  const [trust, setTrust] = useState('60')
  const [supply, setSupply] = useState('1000')
  const [form, setForm] = useState<string>('coin')
  const [backing, setBacking] = useState<string>('metal')
  const [convertible, setConvertible] = useState(true)
  const metals = useKindChoices(worldId)
  const metalBlocked = metalsAllowed(form)
    ? null
    : `${MONEY_FORM[form as MoneyForm].label} is not made of metal.`
  const strike = useGodAction({
    writes: [{ lever: 'currency:create' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/currency:create', {
          body: {
            issuer_id: Number(issuer),
            name: name.trim(),
            metal:
              metal && metalsAllowed(form) ? (metal as MaterialKind) : null,
            purity: whole(purity, PERCENT),
            trust: whole(trust, PERCENT),
            supply: whole(supply),
            form: form as MoneyForm,
            backing: backing as MoneyBacking,
            convertible,
          },
        })
      ),
    onDone: () => {
      setName('')
      onDone?.()
    },
  })
  const gate = useBusy(null, strike.isPending)
  const busy =
    gate ??
    (issuer === null
      ? 'Choose who strikes the coin first.'
      : !name.trim()
        ? 'Give the coin a name first.'
        : metalsAllowed(form) && !metal
          ? 'Choose the metal it is struck in first.'
          : null)
  return (
    <div data-surface='CoinForge' className={FORM_CARD}>
      <PartHeader
        icon={Coins}
        title='Strike a new coin'
        note='A people, settlement, association or realm begins to mint. Its markets count in the new coin from the next epoch.'
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-3')}>
        <EntityChoice
          label='Struck by'
          types={ISSUER_TYPES}
          value={issuer}
          blocked={gate}
          placeholder='Choose an issuer'
          onChange={setIssuer}
        />
        <TextField
          label='Coin name'
          value={name}
          placeholder='The name of the coin'
          onChange={setName}
        />
        <ChoiceSelect
          label='Form of money'
          value={form}
          table={MONEY_FORM}
          blocked={gate}
          onPick={setForm}
        />
        <ChoiceSelect
          label='Metal'
          value={metalsAllowed(form) ? metal : ''}
          table={metals}
          blocked={gate ?? metalBlocked}
          placeholder={metalBlocked ?? undefined}
          onPick={setMetal}
        />
        <ChoiceSelect
          label='Backed by'
          value={backing}
          table={MONEY_BACKING}
          blocked={gate}
          onPick={setBacking}
        />
        <SwitchField
          label='Can be exchanged for its backing'
          checked={convertible}
          disabled={gate !== null}
          onChange={setConvertible}
        />
        <NumberField
          label='Purity (0–100)'
          aria='New coin purity'
          value={purity}
          max={PERCENT}
          onChange={setPurity}
        />
        <NumberField
          label='Trust (0–100)'
          aria='New coin trust'
          value={trust}
          max={PERCENT}
          onChange={setTrust}
        />
        <NumberField
          label='Coins abroad'
          aria='New coin supply'
          value={supply}
          onChange={setSupply}
        />
      </div>
      <Button
        act={strike}
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => strike.mutate(undefined)}
      >
        <Coins />
        Strike it
      </Button>
    </div>
  )
}

export function CurrencyCards({ worldId }: { worldId: number | null }) {
  const view = useCurrencies()
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Opener icon={Plus} label='Strike a new coin'>
        {(close) => <CoinForge worldId={worldId} onDone={close} />}
      </Opener>
      {!view.data ? (
        <LoadingBlock label='Loading the coins' />
      ) : view.data.length === 0 ? (
        <EmptyState
          icon={Coins}
          title='No one strikes coins yet'
          description='Peoples with trade knowledge and coin metal begin to mint.'
        />
      ) : (
        <ul
          data-surface='CurrencyCards'
          className='grid min-w-0 grid-cols-1 gap-3 @3xl/eco:grid-cols-2'
        >
          <Paged items={view.data} as='li'>
            {(currency) => (
              <CurrencyCard
                key={`${currency.id}-${currency.held}-${currency.name}-${currency.metal}`}
                currency={currency}
                worldId={worldId}
              />
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}

export function Parties({
  from,
  to,
}: {
  from: { id: number; name: string }
  to: { id: number; name: string }
}) {
  return (
    <Text
      weight='medium'
      className='flex min-w-0 flex-wrap items-center gap-x-1.5'
    >
      <EntityLink kind='entity' id={String(from.id)}>
        {from.name}
      </EntityLink>
      <ArrowRight
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <EntityLink kind='entity' id={String(to.id)}>
        {to.name}
      </EntityLink>
    </Text>
  )
}

export function LoanCard({ loan }: { loan: Loan }) {
  const [principal, setPrincipal] = useState(String(loan.principal))
  const [interest, setInterest] = useState(String(loan.interest_pct))
  const [due, setDue] = useState(String(loan.due_epoch))
  const [repaid, setRepaid] = useState(String(loan.repaid))
  const [state, setState] = useState<string>(loan.status)
  const [hold, setHold] = useState(loan.held)
  const forgive = useGodAction({
    writes: [{ lever: 'loan:forgive' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/loan:forgive', { body: { loan_id: loan.id } })
      ),
  })
  const edit = useGodAction({
    writes: [{ lever: 'loan:edit' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/loan:edit', {
          body: {
            loan_id: loan.id,
            principal: whole(principal, undefined, 1),
            interest_pct: whole(interest, PERCENT),
            due_epoch: whole(due),
            repaid: whole(repaid),
            status: state as LoanStatus,
            hold,
          },
        })
      ),
  })
  const release = useGodAction({
    writes: [{ lever: 'loan:release' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/loan:release', { body: { loan_id: loan.id } })
      ),
  })
  const remove = useGodAction({
    writes: [{ lever: 'loan:delete' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/loan:delete', { body: { loan_id: loan.id } })
      ),
  })
  const busy = useBusy(
    null,
    forgive.isPending,
    edit.isPending,
    release.isPending,
    remove.isPending
  )
  const status = LOAN_STATUS[loan.status]
  const total = loan.repaid + loan.owed
  const realm = loan.borrower_type === 'polity'
  return (
    <li
      data-loan={loan.id}
      className='@container/loan flex h-full min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Landmark} tone={status.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Parties
            from={{ id: loan.lender_id, name: loan.lender_name }}
            to={{ id: loan.borrower_id, name: loan.borrower_name }}
          />
          <Muted variant='caption'>
            {`Lent ${PURPOSE[loan.purpose] ?? plainWords(loan.purpose)} in epoch ${loan.issued_epoch}${loan.currency_name ? `, in ${loan.currency_name}` : ''}`}
          </Muted>
        </div>
        <div className='flex min-w-0 flex-wrap justify-end gap-1.5'>
          <HeldBadge held={loan.held} />
          {realm && (
            <Badge size='sm' variant='info'>
              <Crown />
              Realm
            </Badge>
          )}
          <Badge variant={status.variant}>
            <status.icon />
            {status.label}
          </Badge>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <IconStat
          icon={Coins}
          label='Lent'
          value={`${formatInteger(loan.principal)} lent`}
          tone='gold'
        />
        <IconStat
          icon={Percent}
          label='Interest'
          value={`${loan.interest_pct}% interest`}
          tone='warning'
        />
        <IconStat
          icon={HandCoins}
          label='Still owed'
          value={`${formatInteger(loan.owed)} owed`}
          tone={loan.owed > 0 ? 'danger' : 'success'}
        />
        <IconStat
          icon={CalendarClock}
          label='Due in epoch'
          value={`Due ${loan.due_epoch}`}
          tone='muted'
        />
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Label>Repaid</Label>
          <Stat value={loan.repaid} unit={`/ ${formatInteger(total)}`} />
        </div>
        <Progress
          size='sm'
          tone='success'
          value={total > 0 ? (loan.repaid / total) * PERCENT : 0}
          aria-label='Repaid'
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap gap-2'>
          {loan.status === 'open' && (
            <Button
              act={forgive}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => forgive.mutate(undefined)}
            >
              <HandCoins />
              Forgive
            </Button>
          )}
          <ReleaseButton
            act={release}
            held={loan.held}
            busy={busy}
            onRelease={() => release.mutate(undefined)}
          />
          <ConfirmButton
            act={remove}
            icon={Trash2}
            label='Strike it out'
            title='Strike this loan from the ledgers?'
            description='It is gone as if it never was: nothing is owed and nothing was repaid.'
            confirm='Strike it out'
            busy={busy}
            onConfirm={() => remove.mutate(undefined)}
          />
        </div>
        <AdjustPanel
          acts={[edit]}
          label='Adjust the loan'
          title={`The loan to ${loan.borrower_name}`}
          note='Rewrite what was lent, its interest, when it falls due, how much is repaid and where it stands.'
          hold={hold}
          onHold={setHold}
        >
          <div className={cn(FIELD_GRID, 'grid-cols-2 @lg/loan:grid-cols-4')}>
            <NumberField
              label='Lent'
              aria={`Loan ${loan.id} principal`}
              value={principal}
              min={1}
              onChange={setPrincipal}
            />
            <NumberField
              label='Interest %'
              aria={`Loan ${loan.id} interest`}
              value={interest}
              max={PERCENT}
              onChange={setInterest}
            />
            <NumberField
              label='Due in epoch'
              aria={`Loan ${loan.id} due epoch`}
              value={due}
              onChange={setDue}
            />
            <NumberField
              label='Repaid'
              aria={`Loan ${loan.id} repaid`}
              value={repaid}
              onChange={setRepaid}
            />
          </div>
          <div className='max-w-xs min-w-0'>
            <ChoiceSelect
              label='Standing'
              value={state}
              table={STATUS_CHOICES}
              blocked={busy}
              onPick={setState}
            />
          </div>
          <Button
            act={edit}
            size='sm'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate(undefined)}
          >
            <Save />
            Set the loan
          </Button>
        </AdjustPanel>
      </div>
    </li>
  )
}

export function LoanForge({ onDone }: { onDone?: () => void }) {
  const currencies = useCurrencies()
  const [lender, setLender] = useState<string | null>(null)
  const [borrower, setBorrower] = useState<string | null>(null)
  const [principal, setPrincipal] = useState('500')
  const [interest, setInterest] = useState('10')
  const [term, setTerm] = useState('5')
  const [coin, setCoin] = useState<string>(NONE)
  const [purpose, setPurpose] = useState<string>('trade')
  const grant = useGodAction({
    writes: [{ lever: 'loan:grant' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/loan:grant', {
          body: {
            lender_id: Number(lender),
            borrower_id: Number(borrower),
            principal: whole(principal, undefined, 1),
            interest_pct: whole(interest, PERCENT),
            term_epochs: whole(term, undefined, 1),
            currency_id: coin === NONE ? null : Number(coin),
            purpose,
          },
        })
      ),
    onDone: () => onDone?.(),
  })
  const gate = useBusy(null, grant.isPending)
  const busy =
    gate ??
    (lender === null
      ? 'Choose who lends first.'
      : borrower === null
        ? 'Choose who borrows first.'
        : lender === borrower
          ? 'No one lends to itself.'
          : null)
  const coins: Record<string, Named> = {
    [NONE]: { label: 'In kind, no coin', icon: Scale, tone: 'muted' },
    ...Object.fromEntries(
      (currencies.data ?? []).map((row) => [
        String(row.id),
        { label: row.name, icon: Coins, tone: 'gold' },
      ])
    ),
  }
  return (
    <div data-surface='LoanForge' className={FORM_CARD}>
      <PartHeader
        icon={Landmark}
        title='Make a loan'
        note='An association, people, settlement or realm lends to another. Interest runs each epoch; an unpaid loan defaults when it falls due.'
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-2')}>
        <EntityChoice
          label='Lender'
          types={LENDER_TYPES}
          value={lender}
          blocked={gate}
          placeholder='Choose who lends'
          onChange={setLender}
        />
        <EntityChoice
          label='Borrower'
          types={BORROWER_TYPES}
          value={borrower}
          blocked={gate}
          placeholder='Choose who borrows'
          onChange={setBorrower}
        />
      </div>
      <div className={cn(FIELD_GRID, 'grid-cols-3')}>
        <NumberField
          label='Lent'
          aria='New loan principal'
          value={principal}
          min={1}
          onChange={setPrincipal}
        />
        <NumberField
          label='Interest %'
          aria='New loan interest'
          value={interest}
          max={PERCENT}
          onChange={setInterest}
        />
        <NumberField
          label='Runs for epochs'
          aria='New loan term'
          value={term}
          min={1}
          onChange={setTerm}
        />
      </div>
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-2')}>
        <ChoiceSelect
          label='Coin'
          value={coin}
          table={coins}
          blocked={gate}
          onPick={setCoin}
        />
        <ChoiceSelect
          label='Purpose'
          value={purpose}
          table={PURPOSE_CHOICES}
          blocked={gate}
          onPick={setPurpose}
        />
      </div>
      <Button
        act={grant}
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => grant.mutate(undefined)}
      >
        <HandCoins />
        Lend it
      </Button>
    </div>
  )
}

function DebtCard({
  debt,
  busy,
  onWriteOff,
  act,
}: {
  debt: Debt
  busy: string | null
  onWriteOff: () => void
  act?: ActProp
}) {
  const remedy = debt.remedy ? DEBT_REMEDY[debt.remedy] : null
  const what = debt.currency_name ?? plainWords(debt.what)
  return (
    <li className='flex h-full min-w-0 items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <Medallion icon={Scale} tone='warning' size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Parties
          from={{ id: debt.debtor_id, name: debt.debtor_name }}
          to={{ id: debt.creditor_id, name: debt.creditor_name }}
        />
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <IconStat
            icon={HandCoins}
            label={`Owed in ${what}`}
            value={`${formatInteger(debt.amount)} ${what}`}
            tone='warning'
          />
          {debt.due_epoch !== null && (
            <IconStat
              icon={CalendarClock}
              label='Due in epoch'
              value={`Due ${debt.due_epoch}`}
              tone='muted'
            />
          )}
          {remedy && (
            <Badge size='sm' variant={remedy.variant}>
              <remedy.icon />
              {remedy.label}
            </Badge>
          )}
        </div>
      </div>
      <Button
        act={act}
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={onWriteOff}
      >
        Write it off
      </Button>
    </li>
  )
}

function DebtLawCard({ law }: { law: DebtLaw }) {
  const [remedy, setRemedy] = useState<string>(law.remedy)
  const [jubilee, setJubilee] = useState(String(law.jubilee_epochs))
  const edit = useGodAction({
    writes: [{ lever: 'law:edit' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/law:edit', {
          body: {
            law_id: law.law_id,
            params: { remedy, jubilee_epochs: whole(jubilee, undefined, 1) },
          },
        })
      ),
  })
  const repeal = useGodAction({
    writes: [{ lever: 'law:repeal' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/law:repeal', { body: { law_id: law.law_id } })
      ),
  })
  const busy = useBusy(null, edit.isPending, repeal.isPending)
  const spec = DEBT_REMEDY[law.remedy]
  return (
    <li
      data-law={law.law_id}
      className='@container/law flex h-full min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={spec.icon} tone={spec.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <EntityLink kind='entity' id={String(law.law_id)}>
            {law.name}
          </EntityLink>
          <Muted variant='caption' className='flex min-w-0 flex-wrap gap-x-1'>
            {law.holders.length === 0 ? 'Held by no one now' : 'The law of'}
            {law.holders.map((id, index) => (
              <EntityLink key={id} kind='entity' id={String(id)}>
                {`${law.holder_names[index] ?? `Record ${id}`}${index < law.holders.length - 1 ? ',' : ''}`}
              </EntityLink>
            ))}
          </Muted>
        </div>
        <Badge variant={spec.variant}>
          <spec.icon />
          {spec.label}
        </Badge>
      </div>
      <Muted variant='caption'>
        {law.remedy === 'jubilee'
          ? `Every debt is wiped clean after ${law.jubilee_epochs} ${law.jubilee_epochs === 1 ? 'epoch' : 'epochs'}.`
          : spec.note}
      </Muted>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <IconStat
          icon={ShieldCheck}
          label='How strictly it is enforced'
          value={`${law.enforcement}% enforced`}
          tone={law.enforcement < LOW ? 'warning' : 'success'}
        />
        {law.remedy === 'jubilee' && (
          <IconStat
            icon={CalendarClock}
            label='Epochs to a jubilee'
            value={`Jubilee every ${law.jubilee_epochs}`}
            tone='verdigris'
          />
        )}
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <ConfirmButton
            act={repeal}
            icon={Gavel}
            label='Repeal'
            title={`Repeal ${law.name}?`}
            description='Debtors are no longer bound by it; defaults fall back to the custom of the land.'
            confirm='Repeal it'
            busy={busy}
            onConfirm={() => repeal.mutate(undefined)}
          />
        </div>
        <AdjustPanel
          acts={[edit]}
          label='Adjust the law'
          title={`Rewrite ${law.name}`}
          note='Choose what befalls those who default and, under a jubilee, how many epochs pass before debts are wiped.'
        >
          <div className={cn(FIELD_GRID, '@md/law:grid-cols-2')}>
            <ChoiceSelect
              label='Remedy'
              value={remedy}
              table={REMEDY_CHOICES}
              blocked={busy}
              onPick={setRemedy}
            />
            <NumberField
              label='Epochs to a jubilee'
              aria={`${law.name} jubilee epochs`}
              value={jubilee}
              min={1}
              onChange={setJubilee}
            />
          </div>
          <Muted variant='caption'>
            {DEBT_REMEDY[remedy as DebtRemedy].note}
          </Muted>
          <Button
            act={edit}
            size='sm'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate(undefined)}
          >
            <Save />
            Set the law
          </Button>
        </AdjustPanel>
      </div>
    </li>
  )
}

function DebtLawForge({ onDone }: { onDone?: () => void }) {
  const [holder, setHolder] = useState<string | null>(null)
  const [remedy, setRemedy] = useState<string>('jubilee')
  const [jubilee, setJubilee] = useState(DEFAULT_JUBILEE)
  const enact = useGodAction({
    writes: [{ lever: 'law:enact' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/law:enact', {
          body: {
            holder_id: Number(holder),
            kind: 'debt_law',
            params: { remedy, jubilee_epochs: whole(jubilee, undefined, 1) },
          },
        })
      ),
    onDone: () => onDone?.(),
  })
  const gate = useBusy(null, enact.isPending)
  const busy =
    gate ?? (holder === null ? 'Choose who lays down the law.' : null)
  return (
    <div className={FORM_CARD}>
      <PartHeader
        icon={ScrollText}
        title='Lay down a debt law'
        note='A realm, settlement, people or cult decides what befalls those who cannot pay.'
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-3')}>
        <EntityChoice
          label='Laid down by'
          types={LAW_HOLDER_TYPES}
          value={holder}
          blocked={gate}
          placeholder='Choose a realm or settlement'
          onChange={setHolder}
        />
        <ChoiceSelect
          label='Remedy'
          value={remedy}
          table={REMEDY_CHOICES}
          blocked={gate}
          onPick={setRemedy}
        />
        <NumberField
          label='Epochs to a jubilee'
          aria='New law jubilee epochs'
          value={jubilee}
          min={1}
          onChange={setJubilee}
        />
      </div>
      <Muted variant='caption'>{DEBT_REMEDY[remedy as DebtRemedy].note}</Muted>
      <Button
        act={enact}
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => enact.mutate(undefined)}
      >
        <Gavel />
        Lay it down
      </Button>
    </div>
  )
}

export function DebtLaws() {
  const view = useDebtLaws()
  return (
    <div data-surface='DebtLaws' className='flex min-w-0 flex-col gap-3'>
      <PartHeader
        icon={Gavel}
        title='Debt laws'
        tone='danger'
        note={
          view.data
            ? `${view.data.length} ${view.data.length === 1 ? 'law decides' : 'laws decide'} what befalls those who default`
            : 'What befalls those who default'
        }
      />
      <Opener icon={Plus} label='Lay down a debt law'>
        {(close) => <DebtLawForge onDone={close} />}
      </Opener>
      {!view.data ? (
        <LoadingBlock label='Loading the laws' />
      ) : view.data.length === 0 ? (
        <EmptyState
          icon={Gavel}
          title='No debt law anywhere'
          description='Without one, a default only costs the debtor its name with the lender.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-3 @2xl/eco:grid-cols-2'>
          <Paged items={view.data} as='li'>
            {(law) => (
              <DebtLawCard
                key={`${law.law_id}-${law.remedy}-${law.jubilee_epochs}`}
                law={law}
              />
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}

export function DebtsLedger() {
  const view = useDebtsLedger()
  const writeOff = useGodAction({
    writes: [{ lever: 'market:write_off' }],
    invalidate: ECONOMY_REFRESH,
    run: (bond: number) =>
      unwrap(
        api.POST('/api/actions/market:write_off', { body: { bond_id: bond } })
      ),
  })
  const busy = useBusy(null, writeOff.isPending)
  if (!view.data) return <LoadingBlock label='Loading the ledger' />
  const { loans, debts } = view.data
  return (
    <div data-surface='DebtsLedger' className='flex min-w-0 flex-col gap-6'>
      <div className='flex min-w-0 flex-col gap-3'>
        <PartHeader
          icon={Landmark}
          title='Bank loans'
          note={`${loans.filter((loan) => loan.status === 'open').length} still owed of ${loans.length} lent`}
        />
        <Opener icon={Plus} label='Make a loan'>
          {(close) => <LoanForge onDone={close} />}
        </Opener>
        {loans.length === 0 ? (
          <EmptyState
            icon={Landmark}
            title='No bank has lent yet'
            description='Banks lend once a people knows trade and strikes coin.'
          />
        ) : (
          <PagedList
            items={loans}
            initial={PAGE}
            step={PAGE}
            noun={['loan', 'loans']}
            className='grid min-w-0 grid-cols-1 gap-3 @2xl/eco:grid-cols-2'
            itemKey={(loan) => loan.id}
          >
            {(loan) => (
              <LoanCard
                key={`${loan.id}-${loan.held}-${loan.status}-${loan.principal}-${loan.repaid}-${loan.due_epoch}`}
                loan={loan}
              />
            )}
          </PagedList>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-3'>
        <PartHeader
          icon={Scale}
          title='Debts between peoples'
          tone='warning'
          note={`${debts.length} ${debts.length === 1 ? 'debt' : 'debts'} outstanding`}
        />
        {debts.length === 0 ? (
          <EmptyState
            icon={Scale}
            title='No one owes anyone'
            description='Debts arise from trade on credit, tribute and war.'
          />
        ) : (
          <PagedList
            items={debts}
            initial={PAGE}
            step={PAGE}
            noun={['debt', 'debts']}
            className='grid min-w-0 grid-cols-1 gap-2 @2xl/eco:grid-cols-2'
            itemKey={(debt) => debt.bond_id}
          >
            {(debt) => (
              <DebtCard
                act={writeOff}
                debt={debt}
                busy={busy}
                onWriteOff={() => writeOff.mutate(debt.bond_id)}
              />
            )}
          </PagedList>
        )}
      </div>
      <DebtLaws />
    </div>
  )
}
