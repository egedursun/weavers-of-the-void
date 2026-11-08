import { useMemo, useState } from 'react'
import {
  CalendarClock,
  Check,
  CircleCheck,
  CircleX,
  Gem,
  Handshake,
  Hourglass,
  ScrollText,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  FormRow,
  IconStat,
  Medallion,
  Section,
  Paged,
} from '@/components/domain'
import {
  type ComboboxOption,
  RecordCombobox,
} from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { AdjustPanel, FIELD_GRID, GoodChip, NumberField } from './EntityEconomy'
import { useResourceProfile } from './api'
import { COMMODITY, type CommodityKind } from './labels'
import { useResourcePacts } from './routeApi'

type Pact = components['schemas']['PactView']

const WORKING = 'Working…'
const NO_GOODS = 'prosperity'
const KEEPERS = ['people', 'settlement', 'faction', 'cult']
const STATUS: Record<
  string,
  {
    label: string
    icon: typeof CircleCheck
    variant: 'success' | 'destructive' | 'outline'
  }
> = {
  in_force: { label: 'In force', icon: CircleCheck, variant: 'success' },
  broken: { label: 'Broken', icon: CircleX, variant: 'destructive' },
  fulfilled: { label: 'Released', icon: Unlock, variant: 'outline' },
  expired: { label: 'Lapsed', icon: Hourglass, variant: 'outline' },
  proposed: { label: 'Proposed', icon: Hourglass, variant: 'outline' },
  rejected: { label: 'Rejected', icon: CircleX, variant: 'destructive' },
}
const GOODS: Record<string, string> = {
  [NO_GOODS]: 'Prosperity, not goods',
  ...Object.fromEntries(
    (Object.keys(COMMODITY) as CommodityKind[]).map((key) => [
      key,
      COMMODITY[key].label,
    ])
  ),
}

function whole(value: string, fallback: number): number {
  const parsed = Math.round(Number(value))
  return Number.isFinite(parsed) ? parsed : fallback
}

function Terms({
  initial,
  busy,
  submit,
  submitLabel,
}: {
  initial: {
    demand: string
    commodity: string
    units: number
    cost: number
    every: number
  }
  busy: string | null
  submit: (terms: Record<string, string | number>) => void
  submitLabel: string
}) {
  const [demand, setDemand] = useState(initial.demand)
  const [commodity, setCommodity] = useState(initial.commodity)
  const [units, setUnits] = useState(String(initial.units))
  const [cost, setCost] = useState(String(initial.cost))
  const [every, setEvery] = useState(String(initial.every))
  return (
    <div className={`${FIELD_GRID} @md/pact:grid-cols-2 @3xl/pact:grid-cols-3`}>
      <FormRow label='What it asks'>
        {(id) => (
          <Input
            id={id}
            value={demand}
            maxLength={120}
            onChange={(event) => setDemand(event.target.value)}
          />
        )}
      </FormRow>
      <MindPicker
        label='Paid in'
        value={commodity}
        table={GOODS}
        blocked={busy}
        onPick={setCommodity}
      />
      {commodity === NO_GOODS ? (
        <NumberField
          label='Prosperity given'
          aria='Prosperity given'
          value={cost}
          max={100}
          onChange={setCost}
        />
      ) : (
        <NumberField
          label='Loads given'
          aria='Loads given'
          value={units}
          onChange={setUnits}
        />
      )}
      <NumberField
        label='Every so many epochs'
        aria='Every so many epochs'
        value={every}
        min={1}
        onChange={setEvery}
      />
      <Button
        size='sm'
        className='justify-self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() =>
          submit({
            demand,
            commodity: commodity === NO_GOODS ? '' : commodity,
            units: whole(units, 0),
            cost: whole(cost, 0),
            every: Math.max(1, whole(every, 1)),
          })
        }
      >
        <Check />
        {submitLabel}
      </Button>
    </div>
  )
}

function PactCard({ pact, busy }: { pact: Pact; busy: string | null }) {
  const status = STATUS[pact.status] ?? STATUS.expired
  const live = pact.status === 'in_force'
  const terms = useGodAction({
    run: (values: Record<string, string | number>) =>
      unwrap(
        api.POST('/api/actions/resource:pact_terms', {
          body: { treaty_id: pact.treaty_id, terms: values },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:pact_end', {
          body: { treaty_id: pact.treaty_id },
        })
      ),
  })
  const blocked =
    busy ?? (terms.isPending || release.isPending ? WORKING : null)
  return (
    <li
      data-pact={pact.treaty_id}
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={Handshake}
          tone={live ? 'verdigris' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <EntityLink kind='entity' id={String(pact.treaty_id)}>
            {pact.name}
          </EntityLink>
          <Muted variant='caption'>
            {'Kept by '}
            {pact.owner_id !== null ? (
              <EntityLink kind='entity' id={String(pact.owner_id)}>
                {pact.owner_name}
              </EntityLink>
            ) : (
              'no one'
            )}
          </Muted>
        </div>
        <Badge variant={status.variant}>
          <status.icon />
          {status.label}
        </Badge>
      </div>
      <Text>{`It asks ${pact.demand || 'its due'}.`}</Text>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {pact.commodity ? (
          <GoodChip kind={pact.commodity} quantity={pact.units} />
        ) : (
          <IconStat
            icon={Gem}
            label='Paid from the prosperity of its keeper'
            value={`${pact.cost} prosperity`}
            tone='gold'
          />
        )}
        <IconStat
          icon={CalendarClock}
          label='Owed on this term'
          value={`Every ${pact.every} ${pact.every === 1 ? 'epoch' : 'epochs'}`}
          tone='info'
        />
        <IconStat
          icon={ScrollText}
          label='Last given in epoch'
          value={`Given ${pact.paid_epoch}`}
          tone='muted'
        />
        {pact.until_epoch !== null && (
          <IconStat
            icon={Hourglass}
            label='Lasts until epoch'
            value={`Until ${pact.until_epoch}`}
            tone='muted'
          />
        )}
        {pact.misread && (
          <Badge size='sm' variant='warning'>
            Misread across tongues
          </Badge>
        )}
      </div>
      {live && (
        <AdjustPanel
          label='Change the terms'
          title='What the pact asks'
          note='Set what the resource is owed, in what and how often. Kept terms bring its gifts; a broken term brings its wrath.'
        >
          <Terms
            initial={{
              demand: pact.demand,
              commodity: pact.commodity ?? NO_GOODS,
              units: pact.units,
              cost: pact.cost,
              every: pact.every,
            }}
            busy={blocked}
            submit={(values) => terms.mutate(values)}
            submitLabel='Set the terms'
          />
          <Button
            size='sm'
            variant='outline'
            className='self-start'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => release.mutate(undefined)}
          >
            <Unlock />
            Release the pact
          </Button>
        </AdjustPanel>
      )}
    </li>
  )
}

function useKeepers(): ComboboxOption[] {
  const names = useNames()
  return useMemo(
    () =>
      (names.data ?? [])
        .filter((row) => row.kind === 'entity' && KEEPERS.includes(row.type))
        .map((row) => ({
          value: String(row.id),
          label: row.name,
          hint: row.type,
        })),
    [names.data]
  )
}

function StrikePact({
  resourceId,
  busy,
}: {
  resourceId: number
  busy: string | null
}) {
  const keepers = useKeepers()
  const [keeper, setKeeper] = useState<string | null>(null)
  const [epochs, setEpochs] = useState('6')
  const strike = useGodAction({
    run: (terms: Record<string, string | number>) =>
      unwrap(
        api.POST('/api/actions/resource:pact', {
          body: {
            resource_id: resourceId,
            owner_id: Number(keeper),
            terms,
            epochs: Math.max(1, whole(epochs, 6)),
          },
        })
      ),
  })
  const blocked =
    busy ??
    (strike.isPending ? WORKING : null) ??
    (keeper === null ? 'Choose who keeps the pact' : null)
  return (
    <AdjustPanel
      label='Strike a pact'
      title='Bind the resource and its keeper'
      note='A living resource that is owed a set tribute on a set term gives of itself while the terms are kept, and turns on its keeper when they are broken.'
    >
      <div className={`${FIELD_GRID} @md/pact:grid-cols-2`}>
        <FormRow label='Keeper'>
          {(id) => (
            <RecordCombobox
              id={id}
              options={keepers}
              value={keeper}
              onChange={(next) => setKeeper(next)}
              placeholder='A people, settlement, faction or cult'
              aria-label='Keeper of the pact'
            />
          )}
        </FormRow>
        <NumberField
          label='Lasts (epochs)'
          aria='Pact length in epochs'
          value={epochs}
          min={1}
          onChange={setEpochs}
        />
      </div>
      <Terms
        initial={{
          demand: 'an offering on each term',
          commodity: NO_GOODS,
          units: 0,
          cost: 8,
          every: 2,
        }}
        busy={blocked}
        submit={(terms) => strike.mutate(terms)}
        submitLabel='Strike the pact'
      />
    </AdjustPanel>
  )
}

export function SentientPacts({
  resourceId,
  readOnlyReason,
}: {
  resourceId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const pacts = useResourcePacts(resourceId)
  const profile = useResourceProfile(resourceId)
  const busy = readOnlyReason ?? reason()
  const live = (pacts.data ?? []).filter((pact) => pact.status === 'in_force')
  const sentient =
    profile.data?.params.some((param) => param.mechanic === 'sentient') ?? false
  if (!sentient && (pacts.data ?? []).length === 0) return null
  return (
    <Section
      id='section-sentient-pacts'
      title='Pacts with the living resource'
      description='A sentient resource bargains through treaties: what it is owed, by whom, how often, and whether the terms were kept.'
      icon={Handshake}
    >
      <div
        data-surface='SentientPact'
        className='@container/pact flex min-w-0 flex-col gap-4'
      >
        {pacts.data && pacts.data.length === 0 && (
          <EmptyState
            icon={Handshake}
            title='No pact binds it yet'
            description='When a skilled negotiator talks down its demands, or you strike one yourself, the terms appear here.'
          />
        )}
        {pacts.data && pacts.data.length > 0 && (
          <ul className='grid min-w-0 grid-cols-1 gap-2 @3xl/pact:grid-cols-2'>
            <Paged items={pacts.data} as='li'>
              {(pact) => (
                <PactCard key={pact.treaty_id} pact={pact} busy={busy} />
              )}
            </Paged>
          </ul>
        )}
        {live.length === 0 && (
          <StrikePact resourceId={resourceId} busy={busy} />
        )}
      </div>
    </Section>
  )
}
