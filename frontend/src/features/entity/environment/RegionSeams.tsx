import { useState } from 'react'
import { Gem, Layers, Save } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { StatBar } from '@/components/domain'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useWorldMaterials } from '../economy/api'
import { MindPicker } from '../mind/parts'
import { NumberField, SwitchField } from '../wilds/parts'
import { BIOMES, WORLD_SEAM } from './seams'

type RegionEnvironment = components['schemas']['RegionEnvironmentView']
type MaterialKind = components['schemas']['MaterialKind']

const PERCENT = 100
const WORKING = 'Working…'
const DEFAULT_RICHNESS = 50

function percent(raw: string): number {
  const value = Number(raw)
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(PERCENT, Math.round(value)))
}

export function SeamForge({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const materials = useWorldMaterials(ground.world_id)
  const [choice, setChoice] = useState('')
  const [richness, setRichness] = useState(String(DEFAULT_RICHNESS))
  const [hold, setHold] = useState(true)
  const seam = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:mineral', {
          body: {
            region_id: regionId,
            richness: percent(richness),
            lock: hold,
            ...(choice.startsWith(WORLD_SEAM)
              ? { world_material_id: Number(choice.slice(WORLD_SEAM.length)) }
              : { material: choice as MaterialKind }),
          },
        })
      ),
    success: 'The seam is laid down',
  })
  const busy = reason() ?? (seam.isPending ? WORKING : null)
  const table = Object.fromEntries(
    (materials.data?.materials ?? []).map((item) => [
      item.world_material_id != null
        ? `${WORLD_SEAM}${item.world_material_id}`
        : (item.kind ?? ''),
      item.world_material_id != null
        ? `${item.label} (of this world)`
        : item.label,
    ])
  )
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-3'>
      <div className='min-w-48 flex-1'>
        <MindPicker
          label='Lay a seam of'
          value={choice}
          table={table}
          blocked={busy}
          placeholder='Any material, or one born in this world'
          onPick={setChoice}
        />
      </div>
      <div className='w-28'>
        <NumberField
          label='Richness'
          value={richness}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={setRichness}
        />
      </div>
      <SwitchField
        label='Hold against mining'
        checked={hold}
        disabled={busy !== null}
        onChange={setHold}
      />
      <Button
        size='sm'
        disabled={busy !== null || choice === ''}
        disabledReason={
          busy ?? (choice === '' ? 'Choose a material first' : undefined)
        }
        onClick={() => seam.mutate()}
      >
        <Gem />
        Lay it down
      </Button>
    </div>
  )
}

export function BiomeMix({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const [biome, setBiome] = useState('')
  const [share, setShare] = useState('0')
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:biome', {
          body: {
            region_id: regionId,
            biome: Number(biome),
            share: percent(share),
            lock: true,
          },
        })
      ),
    success: 'The land is reshaped',
  })
  const busy = reason() ?? (set.isPending ? WORKING : null)
  const table = Object.fromEntries(
    BIOMES.map((label, index) => [String(index), label])
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {BIOMES.map((label, index) =>
        (ground.biome_mix[index] ?? 0) > 0 ? (
          <StatBar
            key={label}
            label={label}
            value={ground.biome_mix[index] ?? 0}
            max={PERCENT}
            icon={Layers}
            tone='info'
          />
        ) : null
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Biome'
            value={biome}
            table={table}
            blocked={busy}
            placeholder='Choose a biome'
            onPick={(value) => {
              setBiome(value)
              setShare(String(ground.biome_mix[Number(value)] ?? 0))
            }}
          />
        </div>
        <div className='w-28'>
          <NumberField
            label='Share'
            value={share}
            min={0}
            max={PERCENT}
            disabled={busy !== null}
            onChange={setShare}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null || biome === ''}
          disabledReason={
            busy ?? (biome === '' ? 'Choose a biome first' : undefined)
          }
          onClick={() => set.mutate()}
        >
          <Save />
          Set and hold
        </Button>
      </div>
    </div>
  )
}
