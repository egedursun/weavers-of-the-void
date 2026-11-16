import { useState } from 'react'
import {
  Building,
  Coins,
  Flame,
  Gavel,
  Home,
  Lamp,
  Tent,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Chip, ForgeCard } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { type Named } from '@/features/entity/environment/labels'
import { ENERGY_KINDS } from '@/features/minds/labels'
import { useGodAction } from '@/features/pantheon/godAction'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type Dwelling, type Household } from '../lineage/api'

type Schema = components['schemas']

const CROWDED = 150
const WORKING = 'Working on it.'

const HOUSEHOLD_FORMS: Record<Schema['HouseholdForm'], Named> = {
  nuclear: { label: 'Partners and their children', icon: Home, tone: 'info' },
  extended: { label: 'Several generations', icon: Users, tone: 'verdigris' },
  stem: { label: 'One wedded heir stays', icon: Home, tone: 'gold' },
  joint: { label: 'Wedded siblings together', icon: Users, tone: 'info' },
  polygamous: { label: 'Several partners', icon: Users, tone: 'warning' },
  communal: { label: 'Communal', icon: Building, tone: 'success' },
  single: { label: 'Living alone', icon: Home, tone: 'muted' },
  institutional: { label: 'An institution', icon: Building, tone: 'muted' },
  mixed: { label: 'Born and made together', icon: Users, tone: 'verdigris' },
  chosen: { label: 'Chosen kin', icon: Users, tone: 'success' },
}

const TENURES: Record<Schema['DwellingTenure'], Named> = {
  owned: { label: 'Owned', icon: Home, tone: 'success' },
  rented: { label: 'Rented', icon: Coins, tone: 'info' },
  granted: { label: 'Granted for service', icon: Gavel, tone: 'warning' },
  squatted: { label: 'Squatted', icon: Tent, tone: 'danger' },
}

function why(blocked: string | null, pending: boolean) {
  return blocked ?? (pending ? WORKING : null)
}

export function HouseholdFormCard({
  household,
  blocked,
  hold,
}: {
  household: Household
  blocked: string | null
  hold: boolean
}) {
  const [form, setForm] = useState<string>(household.form)
  const setting = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/household:edit', {
          body: {
            household_id: household.id,
            form: form as Household['form'],
            hold,
          },
        })
      ),
    success: 'The household’s form is set',
  })
  const named = HOUSEHOLD_FORMS[household.form]
  return (
    <ForgeCard
      icon={named.icon}
      tone={named.tone ?? 'info'}
      title={`Form: ${named.label.toLowerCase()}`}
      note='The form follows who lives together; larger forms share the care of children, elders and the sick. A form you set is held.'
      columns={2}
      action={
        <StepButton
          icon={named.icon}
          label='Set the form'
          busy={why(blocked, setting.isPending)}
          onClick={() => setting.mutate()}
        />
      }
    >
      <ChoiceField
        label='Form'
        value={form}
        table={HOUSEHOLD_FORMS}
        blocked={blocked}
        onPick={setForm}
      />
    </ForgeCard>
  )
}

export function DwellingTenureCard({
  household,
  dwelling,
  blocked,
  hold,
}: {
  household: Household
  dwelling: Dwelling
  blocked: string | null
  hold: boolean
}) {
  const [tenure, setTenure] = useState<string>(dwelling.tenure)
  const [heating, setHeating] = useState<string>(dwelling.heating ?? 'heat')
  const [light, setLight] = useState<string>(dwelling.light ?? 'heat')
  const [crowding, setCrowding] = useState(String(dwelling.crowding))
  const setting = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/dwelling:set', {
          body: {
            household_id: household.id,
            tenure: tenure as Dwelling['tenure'],
            heating: heating as NonNullable<Dwelling['heating']>,
            light: light as NonNullable<Dwelling['light']>,
            crowding: Math.max(0, Number(crowding) || 0),
            clear_district: false,
            hold,
          },
        })
      ),
    success: 'The home is set so',
  })
  const held = TENURES[dwelling.tenure]
  return (
    <ForgeCard
      icon={held.icon}
      tone={held.tone ?? 'info'}
      title='How the home is held, heated and lit'
      note='Renters pay part of their income, squatters may be driven out, those on granted land owe service; heat and light beyond open fire give comfort and rest.'
      columns={2}
      action={
        <StepButton
          icon={Home}
          label='Set the home'
          busy={why(blocked, setting.isPending)}
          onClick={() => setting.mutate()}
        />
      }
    >
      <div className='flex min-w-0 flex-wrap gap-2 sm:col-span-2'>
        <Chip icon={held.icon}>{held.label}</Chip>
        <Chip icon={Flame}>
          {dwelling.heating
            ? `Heated by ${ENERGY_KINDS[dwelling.heating].label.toLowerCase()}`
            : 'Not yet heated'}
        </Chip>
        <Chip icon={Lamp}>
          {dwelling.light
            ? `Lit by ${ENERGY_KINDS[dwelling.light].label.toLowerCase()}`
            : 'Not yet lit'}
        </Chip>
        <Chip
          icon={Users}
        >{`${dwelling.crowding} members per hundred rooms${dwelling.crowding > CROWDED ? ', crowded' : ''}`}</Chip>
      </div>
      <ChoiceField
        label='Held as'
        value={tenure}
        table={TENURES}
        blocked={blocked}
        onPick={setTenure}
      />
      <ChoiceField
        label='Heated by'
        value={heating}
        table={ENERGY_KINDS}
        blocked={blocked}
        onPick={setHeating}
      />
      <ChoiceField
        label='Lit by'
        value={light}
        table={ENERGY_KINDS}
        blocked={blocked}
        onPick={setLight}
      />
      <NumberField
        label='Members per hundred rooms'
        value={crowding}
        min={0}
        max={1000}
        onChange={setCrowding}
      />
    </ForgeCard>
  )
}
