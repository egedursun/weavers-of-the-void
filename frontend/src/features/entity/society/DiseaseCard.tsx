import { useState } from 'react'
import {
  Biohazard,
  CircleSlash,
  HeartPulse,
  Lock,
  Save,
  ShieldCheck,
  Skull,
  TriangleAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useDisease } from './api'
import { VECTOR_SPEC, choices, words } from './labels'

type Disease = components['schemas']['DiseaseView']

const WORKING = 'Working…'
const PERCENT = 100
const NUMBERS = [
  { key: 'virulence', label: 'Virulence' },
  { key: 'lethality', label: 'Lethality' },
  { key: 'chronic_rate', label: 'Lasting illness' },
  { key: 'incubation', label: 'Incubation (years)' },
  { key: 'immunity_epochs', label: 'Immunity lasts (epochs)' },
  { key: 'mutation_rate', label: 'Mutation' },
  { key: 'stigma', label: 'Stigma' },
  { key: 'cure_level', label: 'Medicine to cure' },
] as const
const AFFINITIES = ['warm', 'wet', 'cold', 'dry', 'any'] as const

function NatureForm({ view, blocked }: { view: Disease; blocked: string | null }) {
  const [numbers, setNumbers] = useState<Record<string, string>>(() =>
    Object.fromEntries(NUMBERS.map((field) => [field.key, String(view[field.key])]))
  )
  const [vector, setVector] = useState<string>(view.vector)
  const [affinity, setAffinity] = useState<string>(view.climate_affinity)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/disease:edit', {
          body: {
            disease_id: view.entity_id,
            values: {
              ...Object.fromEntries(Object.entries(numbers).map(([key, value]) => [key, Math.round(Number(value) || 0)])),
              vector,
              climate_affinity: affinity,
            },
          },
        })
      ),
  })
  const busy = blocked ?? (save.isPending ? WORKING : null)
  const vectors = Object.fromEntries(Object.entries(VECTOR_SPEC).map(([key, spec]) => [key, spec.label]))
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {NUMBERS.map((field) => (
          <div key={field.key} className='flex min-w-0 flex-col gap-1'>
            <Label>{field.label}</Label>
            <Input
              type='number'
              min={0}
              value={numbers[field.key]}
              aria-label={field.label}
              onChange={(event) => setNumbers((current) => ({ ...current, [field.key]: event.target.value }))}
            />
          </div>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-3'>
        <MindPicker label='Spreads by' value={vector} table={vectors} blocked={busy} onPick={setVector} />
        <MindPicker label='Thrives where it is' value={affinity} table={choices(AFFINITIES)} blocked={busy} onPick={setAffinity} />
        <div className='flex items-end'>
          <Button size='sm' disabled={busy !== null} disabledReason={busy ?? undefined} onClick={() => save.mutate(undefined)}>
            <Save />
            Reshape the disease
          </Button>
        </div>
      </div>
    </div>
  )
}

function Levers({ view, blocked }: { view: Disease; blocked: string | null }) {
  const [target, setTarget] = useState(String(view.origin_region_id ?? ''))
  const [community, setCommunity] = useState('')
  const [severity, setSeverity] = useState('60')
  const [epochs, setEpochs] = useState('2')
  const loose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/disease:loose', {
          body: { target_id: Number(target), disease_id: view.entity_id, severity: Math.max(1, Math.min(PERCENT, Number(severity) || 60)) },
        })
      ),
  })
  const cure = useGodAction({
    run: (revoke: boolean) =>
      unwrap(api.POST('/api/actions/disease:cure', { body: { disease_id: view.entity_id, community_id: Number(community), revoke } })),
  })
  const immunity = useGodAction({
    run: () =>
      unwrap(api.POST('/api/actions/disease:immunity', { body: { disease_id: view.entity_id, community_id: Number(community), immune_pct: PERCENT } })),
  })
  const quarantine = useGodAction({
    run: (span: number) =>
      unwrap(api.POST('/api/actions/disease:quarantine', { body: { region_id: Number(target), epochs: span } })),
  })
  const pending = loose.isPending || cure.isPending || immunity.isPending || quarantine.isPending
  const busy = blocked ?? (pending ? WORKING : null)
  const noTarget = busy ?? (target === '' ? 'Name a land or community first' : null)
  const noCommunity = busy ?? (community === '' ? 'Name a community first' : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border border-dashed bg-muted/20 p-3'>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='flex w-40 flex-col gap-1'>
          <Label>Land or community id</Label>
          <Input type='number' min={1} value={target} aria-label='Land or community id' onChange={(event) => setTarget(event.target.value)} />
        </div>
        <div className='flex w-28 flex-col gap-1'>
          <Label>Severity</Label>
          <Input type='number' min={1} max={PERCENT} value={severity} aria-label='Severity' onChange={(event) => setSeverity(event.target.value)} />
        </div>
        <Button size='sm' variant='destructive' disabled={noTarget !== null} disabledReason={noTarget ?? undefined} onClick={() => loose.mutate(undefined)}>
          <Biohazard />
          Loose it there
        </Button>
        <div className='flex w-28 flex-col gap-1'>
          <Label>Epochs</Label>
          <Input type='number' min={0} value={epochs} aria-label='Quarantine epochs' onChange={(event) => setEpochs(event.target.value)} />
        </div>
        <Button size='sm' variant='outline' disabled={noTarget !== null} disabledReason={noTarget ?? undefined} onClick={() => quarantine.mutate(Math.max(0, Number(epochs) || 0))}>
          <Lock />
          Seal the land
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='flex w-40 flex-col gap-1'>
          <Label>Community id</Label>
          <Input type='number' min={1} value={community} aria-label='Community id' onChange={(event) => setCommunity(event.target.value)} />
        </div>
        <Button size='sm' variant='outline' disabled={noCommunity !== null} disabledReason={noCommunity ?? undefined} onClick={() => cure.mutate(false)}>
          <HeartPulse />
          Give the cure
        </Button>
        <Button size='sm' variant='outline' disabled={noCommunity !== null} disabledReason={noCommunity ?? undefined} onClick={() => cure.mutate(true)}>
          <CircleSlash />
          Take the cure away
        </Button>
        <Button size='sm' variant='outline' disabled={noCommunity !== null} disabledReason={noCommunity ?? undefined} onClick={() => immunity.mutate(undefined)}>
          <ShieldCheck />
          Make them immune
        </Button>
      </div>
    </div>
  )
}

export function DiseaseSection({ diseaseId, readOnlyReason }: { diseaseId: number; readOnlyReason?: string | null }) {
  const view = useDisease(diseaseId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const end = useGodAction({
    run: (outbreakId: number) => unwrap(api.POST('/api/actions/outbreak:end', { body: { outbreak_id: outbreakId } })),
  })
  return (
    <Section
      id='section-disease'
      title='The sickness'
      description='How it spreads and kills, where it rose and raged, its strains, and who knows its cure or has grown immune.'
      icon={Biohazard}
      tone='danger'
    >
      {view.isPending && <Muted>Reading the sickness…</Muted>}
      {view.isError && <EmptyState icon={TriangleAlert} title='Not yet studied' description={view.error.message} />}
      {view.data && (
        <div data-surface='DiseaseCard' className='flex min-w-0 flex-col gap-5'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Badge variant='destructive'>{VECTOR_SPEC[view.data.vector].label}</Badge>
            <Badge variant='outline'>{`Thrives ${words(view.data.climate_affinity)}`}</Badge>
            {view.data.target_functions.map((item) => (
              <Badge key={item} variant='outline'>{`Strikes the ${words(item)}`}</Badge>
            ))}
            {view.data.parent_id !== null && (
              <Badge variant='warning'>{`Strain of generation ${view.data.generation}`}</Badge>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
            <KpiTile label='Outbreaks' value={formatInteger(view.data.outbreaks.length)} icon={Biohazard} tone='danger' />
            <KpiTile label='Dead' value={formatInteger(view.data.outbreaks.reduce((sum, item) => sum + item.dead, 0))} icon={Skull} tone='danger' />
            <KpiTile label='Endemic in' value={formatInteger(view.data.endemic.length)} icon={TriangleAlert} tone='warning' />
            <KpiTile label='Cured in' value={formatInteger(view.data.cures.length)} icon={HeartPulse} tone='success' />
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
            <StatBar label='Virulence' value={view.data.virulence} max={PERCENT} tone='warning' />
            <StatBar label='Lethality' value={view.data.lethality} max={PERCENT} tone='destructive' />
          </div>
          {view.data.parent_id !== null && (
            <Text>
              {'A strain of '}
              <EntityLink kind='entity' id={String(view.data.parent_id)}>
                its parent sickness
              </EntityLink>
            </Text>
          )}
          {view.data.strains.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>Strains</Label>
              {view.data.strains.map((strain) => (
                <Text key={strain.id}>
                  <EntityLink kind='entity' id={String(strain.id)}>
                    {strain.name}
                  </EntityLink>
                  {` · spreads ${strain.virulence}, kills ${strain.lethality}`}
                </Text>
              ))}
            </div>
          )}
          {view.data.outbreaks.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>History</Label>
              <Timeline label='Outbreaks'>
                {view.data.outbreaks.map((item, index) => (
                  <TimelineItem
                    key={item.id}
                    icon={Biohazard}
                    title={`${item.region} (${words(item.path)})`}
                    timestamp={`Epoch ${item.started_epoch}`}
                    tone={item.status === 'ended' ? 'default' : 'destructive'}
                    last={index === view.data.outbreaks.length - 1}
                  >
                    <div className='flex min-w-0 flex-wrap items-center gap-2'>
                      <Muted variant='caption'>{`${formatInteger(item.infected)} fell sick, ${formatInteger(item.dead)} died${item.ended_epoch !== null ? `; over by epoch ${item.ended_epoch}` : ''}`}</Muted>
                      {item.quarantined && <Badge variant='info'>Quarantined</Badge>}
                      {item.status !== 'ended' && (
                        <Button size='sm' variant='ghost' disabled={blocked !== null} disabledReason={blocked ?? undefined} onClick={() => end.mutate(item.id)}>
                          End it
                        </Button>
                      )}
                    </div>
                  </TimelineItem>
                ))}
              </Timeline>
            </div>
          )}
          {view.data.endemic.length > 0 && (
            <div className='flex min-w-0 flex-wrap gap-2'>
              {view.data.endemic.map((item) => (
                <Badge key={item.region_id} variant='warning'>{`Endemic in ${item.region} (${item.load})`}</Badge>
              ))}
            </div>
          )}
          {view.data.cures.length > 0 && (
            <div className='flex min-w-0 flex-wrap gap-2'>
              {view.data.cures.map((item) => (
                <Badge key={item.community_id} variant='success'>{`${item.community} knows the cure`}</Badge>
              ))}
            </div>
          )}
          <NatureForm key={JSON.stringify(view.data.locked) + view.data.virulence + view.data.lethality} view={view.data} blocked={blocked} />
          <Levers view={view.data} blocked={blocked} />
        </div>
      )}
    </Section>
  )
}
