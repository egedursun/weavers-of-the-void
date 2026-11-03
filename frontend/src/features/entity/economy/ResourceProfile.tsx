import { useState } from 'react'
import {
  Eye,
  EyeOff,
  Pickaxe,
  Save,
  TriangleAlert,
  UserRoundCog,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, EntityLink, Section, StatBar } from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useResourceProfile } from './api'
import { COMMODITY, type CommodityKind } from './labels'

type Profile = components['schemas']['ResourceProfileView']
type MaterialKind = components['schemas']['MaterialKind']

const WORKING = 'Working…'
const FIELDS = [
  { key: 'richness', label: 'Richness' },
  { key: 'extraction_difficulty', label: 'Difficulty' },
  { key: 'quality', label: 'Quality' },
  { key: 'regeneration', label: 'Regrowth per epoch' },
  { key: 'byproduct_pct', label: 'By-product share' },
  { key: 'initial_reserve', label: 'First reserve' },
] as const
const NO_MATERIAL = 'none'
const COMMODITY_CHOICES = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, item]) => [key, item.label])
)
const MATERIALS: MaterialKind[] = [
  'wood',
  'bone',
  'hide',
  'leather',
  'cloth',
  'stone',
  'flint',
  'obsidian',
  'copper',
  'tin',
  'bronze',
  'iron',
  'steel',
  'silver',
  'gold',
  'glass',
  'crystal',
  'ivory',
  'chitin',
  'dragonbone',
  'star_metal',
  'void_glass',
  'godflesh',
  'living_wood',
  'salt',
  'amber',
  'lead',
  'skysteel',
  'sulfur',
  'clay',
  'gems',
]
const MATERIAL_CHOICES = {
  [NO_MATERIAL]: 'No material',
  ...Object.fromEntries(
    MATERIALS.map((item) => [item, item.replace('_', ' ')])
  ),
}

function ProfileForm({
  profile,
  readOnlyReason,
}: {
  profile: Profile
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const [reserve, setReserve] = useState(String(profile.reserve))
  const [fields, setFields] = useState<Record<string, string>>(
    Object.fromEntries(
      FIELDS.map((field) => [field.key, String(profile[field.key])])
    )
  )
  const [commodity, setCommodity] = useState<string>(profile.commodity)
  const [material, setMaterial] = useState<string>(
    profile.material ?? NO_MATERIAL
  )
  const [owner, setOwner] = useState('')
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:set', {
          body: {
            resource_id: profile.resource_id,
            reserve: Math.max(0, Number(reserve) || 0),
            fields: Object.fromEntries(
              Object.entries(fields).map(([key, value]) => [
                key,
                Math.round(Number(value) || 0),
              ])
            ),
          },
        })
      ),
  })
  const retype = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:commodity', {
          body: {
            resource_id: profile.resource_id,
            commodity: commodity as CommodityKind,
            material:
              material === NO_MATERIAL ? null : (material as MaterialKind),
          },
        })
      ),
  })
  const reveal = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:reveal', {
          body: {
            resource_id: profile.resource_id,
            revealed: !profile.revealed,
          },
        })
      ),
  })
  const give = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:owner', {
          body: {
            resource_id: profile.resource_id,
            owner_id: owner === '' ? null : Number(owner),
          },
        })
      ),
  })
  const pending =
    save.isPending || retype.isPending || reveal.isPending || give.isPending
  const busy = readOnlyReason ?? reason() ?? (pending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Reserve</Label>
          <Input
            type='number'
            min={0}
            value={reserve}
            aria-label='Reserve'
            onChange={(event) => setReserve(event.target.value)}
          />
        </div>
        {FIELDS.map((field) => (
          <div key={field.key} className='flex min-w-0 flex-col gap-1'>
            <Label>{field.label}</Label>
            <Input
              type='number'
              min={0}
              value={fields[field.key]}
              aria-label={field.label}
              onChange={(event) =>
                setFields((current) => ({
                  ...current,
                  [field.key]: event.target.value,
                }))
              }
            />
          </div>
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Save the reserve
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => reveal.mutate(undefined)}
        >
          {profile.revealed ? <EyeOff /> : <Eye />}
          {profile.revealed ? 'Hide the deposit' : 'Reveal the deposit'}
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='It yields'
            value={commodity}
            table={COMMODITY_CHOICES}
            blocked={busy}
            onPick={setCommodity}
          />
        </div>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Material'
            value={material}
            table={MATERIAL_CHOICES}
            blocked={busy}
            onPick={setMaterial}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => retype.mutate(undefined)}
        >
          <Pickaxe />
          Change what it yields
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='flex w-40 flex-col gap-1'>
          <Label>New owner's id</Label>
          <Input
            type='number'
            min={1}
            value={owner}
            placeholder='None'
            aria-label="New owner's id"
            onChange={(event) => setOwner(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => give.mutate(undefined)}
        >
          <UserRoundCog />
          Give it away
        </Button>
      </div>
    </div>
  )
}

export function ResourceProfile({
  resourceId,
  readOnlyReason,
}: {
  resourceId: number
  readOnlyReason?: string | null
}) {
  const view = useResourceProfile(resourceId)
  return (
    <Section
      id='section-resource-profile'
      title='Reserve and extraction'
      description='How much is left, who works it, how hard and dangerous it is, and what each epoch took out.'
      icon={Pickaxe}
    >
      {view.isPending && <Muted>Loading the reserve…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The reserve could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='ResourceProfile'
          className='flex min-w-0 flex-col gap-5'
        >
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Badge variant='info'>{`${view.data.material_label ? `${view.data.material_label} ` : ''}${COMMODITY[view.data.commodity].label.toLowerCase()}`}</Badge>
            {!view.data.revealed && (
              <Badge variant='warning'>Hidden: no one knows of it yet</Badge>
            )}
            {view.data.sealed_until_epoch !== null && (
              <Badge variant='destructive'>{`Sealed after a cave-in until epoch ${view.data.sealed_until_epoch}`}</Badge>
            )}
            {view.data.regeneration > 0 ? (
              <Badge variant='success'>Renewable</Badge>
            ) : (
              <Badge variant='outline'>Finite</Badge>
            )}
            {view.data.byproduct_material && (
              <Badge variant='outline'>{`By-product: ${view.data.byproduct_material.replace('_', ' ')}`}</Badge>
            )}
          </div>
          <StatBar
            label='Reserve'
            value={view.data.reserve}
            max={view.data.initial_reserve}
            tone={
              view.data.reserve * 4 < view.data.initial_reserve
                ? 'destructive'
                : 'default'
            }
          />
          {view.data.workers.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>Who works it</Label>
              {view.data.workers.map((row) => (
                <Text key={row.community_id}>
                  <EntityLink kind='entity' id={String(row.community_id)}>
                    {row.community_name}
                  </EntityLink>
                  {`: ${formatInteger(row.workers)} workers`}
                </Text>
              ))}
            </div>
          )}
          {view.data.runs.length > 1 && (
            <LineChart
              label='Taken out per epoch'
              height={120}
              series={[
                {
                  key: 'output',
                  label: 'Taken out',
                  color: 'var(--chart-1)',
                  points: view.data.runs.map((run) => ({
                    x: run.epoch,
                    y: run.quantity,
                  })),
                },
              ]}
            />
          )}
          <ProfileForm
            key={`${view.data.reserve}-${view.data.commodity}-${view.data.revealed}`}
            profile={view.data}
            readOnlyReason={readOnlyReason}
          />
        </div>
      )}
    </Section>
  )
}
