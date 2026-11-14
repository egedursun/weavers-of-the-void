import { Activity, CalendarClock, Mountain, Sprout } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState, KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Facts,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { BAND } from '@/features/entity/environment/labels'
import { Ref } from '@/features/gatherings/parts'
import { type NatureNodeView } from './api'
import { DEFENCES, NATURE_ICON, SLEEP, WARMTH } from './labels'
import { MANY, SPAN, useProfileEdit } from './model'

type View = NatureNodeView

function KindCard({ data, blocked }: { data: View; blocked: string | null }) {
  const kind = data.kind_profile
  const action = useProfileEdit(
    'species:edit',
    { species_id: data.node.id },
    blocked
  )
  if (!kind) return null
  const sleep = SLEEP[kind.dormancy]
  const warmth = WARMTH[kind.thermoregulation]
  return (
    <RecordRow
      icon={sleep.icon}
      tone={kind.asleep_now ? 'info' : warmth.tone}
      title={`How ${data.node.name} lives through the seasons`}
      caption={`${sleep.label} · ${warmth.label.toLowerCase()} · ${kind.activity_pct}% active this season · widest range ${kind.range_peak} lands · ${kind.island_epochs} epochs on islands alone`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1'>
          {kind.asleep_now && (
            <Badge size='sm' variant='secondary'>
              Asleep now
            </Badge>
          )}
          {kind.woken_epoch !== null && (
            <Badge
              size='sm'
              variant='warning'
            >{`Woken in epoch ${kind.woken_epoch}`}</Badge>
          )}
          {kind.endemic && (
            <Badge size='sm' variant='success'>
              Endemic
            </Badge>
          )}
          {kind.relict && (
            <Badge size='sm' variant='warning'>
              Relict
            </Badge>
          )}
        </div>
      }
    >
      <Meter
        label={`Activity this season (${kind.activity_pct}%)`}
        value={kind.activity_pct}
        max={2 * SPAN}
        tone={kind.asleep_now ? 'info' : 'success'}
        icon={Activity}
      />
      <RecordEditor
        title='Set how it lives through the seasons'
        note='A kind that sleeps neither raids nor feeds hunters in its season of sleep, lies open in its lair, and wakes hungry when a crowded land disturbs it. A cold-blooded kind slows in the cold and quickens in the heat; a warm-blooded one needs more food in the cold. Kinds of few lands are endemic, kinds shrunk far below their widest range are relicts, and peoples that revere nature spare both. A kind that lives on islands alone drifts toward middle size.'
        fields={[
          {
            key: 'dormancy',
            label: 'Season of sleep',
            kind: 'pick',
            table: table(SLEEP),
          },
          {
            key: 'thermoregulation',
            label: 'Blood',
            kind: 'pick',
            table: table(WARMTH),
          },
          { key: 'endemic', label: 'Endemic', kind: 'pick', table: YES_NO },
          { key: 'relict', label: 'Relict', kind: 'pick', table: YES_NO },
          {
            key: 'island_epochs',
            label: 'Epochs on islands alone',
            kind: 'number',
            min: 0,
            max: MANY,
          },
          {
            key: 'range_peak',
            label: 'Widest range (lands)',
            kind: 'number',
            min: 0,
            max: MANY,
          },
          {
            key: 'woken_epoch',
            label: 'Woken in epoch',
            kind: 'number',
            min: 0,
            max: MANY,
          },
        ]}
        locked={kind.locked}
        busy={action.busy}
        onSave={(values) => action.onEdit({ values, release: [] })}
        onRelease={(release) => action.onEdit({ values: {}, release })}
      />
    </RecordRow>
  )
}

function FolkCard({ data, blocked }: { data: View; blocked: string | null }) {
  const folk = data.folk_profile
  const action = useProfileEdit(
    'people:edit',
    { people_id: data.node.id },
    blocked
  )
  if (!folk) return null
  const warmth = WARMTH[folk.thermoregulation]
  return (
    <RecordRow
      icon={warmth.icon}
      tone={warmth.tone}
      title={`The blood of ${data.node.name}`}
      caption={`${warmth.label} · ${folk.activity_pct}% active this season`}
    >
      <Meter
        label={`Activity this season (${folk.activity_pct}%)`}
        value={folk.activity_pct}
        max={2 * SPAN}
        tone='success'
        icon={Activity}
      />
      <RecordEditor
        title='Set the blood of the people'
        note='A cold-blooded people works and fights less in a cold season and more in a warm one; a warm-blooded people needs more food in the cold.'
        fields={[
          {
            key: 'thermoregulation',
            label: 'Blood',
            kind: 'pick',
            table: table(WARMTH),
          },
        ]}
        locked={folk.locked}
        busy={action.busy}
        onSave={(values) => action.onEdit({ values, release: [] })}
        onRelease={(release) => action.onEdit({ values: {}, release })}
      />
    </RecordRow>
  )
}

function PlantCard({ data, blocked }: { data: View; blocked: string | null }) {
  const plant = data.plant
  const action = useProfileEdit(
    'plant:edit',
    { species_id: data.node.id },
    blocked
  )
  if (!plant) return null
  const defence = DEFENCES[plant.defence]
  return (
    <RecordRow
      icon={defence.icon}
      tone={defence.tone}
      title={`How ${data.node.name} defends itself`}
      caption={`${defence.label} · potency ${plant.defence_potency} of ${SPAN}`}
    >
      <Meter
        label={`Potency (${plant.defence_potency} of ${SPAN})`}
        value={plant.defence_potency}
        tone='warning'
        icon={Sprout}
      />
      <RecordEditor
        title='Set the defence of the plant'
        note='Thorns slow travellers and spoil grazing, toxins spoil famine foraging and yield medicine to the towns around, plants that poison their neighbours thin the harvest, and flesh-eating plants make a land dangerous. Each counts as far as the plant covers its lands.'
        fields={[
          {
            key: 'defence',
            label: 'Defence',
            kind: 'pick',
            table: table(DEFENCES),
          },
          {
            key: 'defence_potency',
            label: 'Potency',
            kind: 'number',
            min: 0,
            max: SPAN,
          },
        ]}
        locked={plant.locked}
        busy={action.busy}
        onSave={(values) => action.onEdit({ values, release: [] })}
        onRelease={(release) => action.onEdit({ values: {}, release })}
      />
    </RecordRow>
  )
}

export function BodyPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const band = data.season_band ? BAND[data.season_band] : null
  const bodied = data.kind_profile || data.folk_profile || data.plant
  return (
    <div data-surface='BodyPanel' className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <KpiTile
          label='This season here'
          value={band ? band.label : 'No known warmth'}
          icon={band ? band.icon : CalendarClock}
          tone={band ? band.tone : 'muted'}
        />
        <KpiTile
          label='Kinds bound to it'
          value={data.bonds.length}
          icon={Mountain}
          tone='verdigris'
        />
      </div>
      <Facts
        items={[
          ['Land', <Ref key='region' node={data.region} empty='no land' />],
        ]}
      />
      {bodied ? (
        <ul className='flex min-w-0 flex-col gap-3'>
          <KindCard data={data} blocked={blocked} />
          <FolkCard data={data} blocked={blocked} />
          <PlantCard data={data} blocked={blocked} />
        </ul>
      ) : (
        <EmptyState
          icon={NATURE_ICON}
          size='inline'
          title='No body of its own'
          description='Only a kind of creature or plant, or a people, has a season of sleep, blood or a defence. This thing lives by those of the kinds and peoples around it, shown in the other tabs.'
        />
      )}
    </div>
  )
}
