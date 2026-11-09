import { useId, useState } from 'react'
import { Layers, Orbit, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { AdjustPanel } from '@/features/entity/wilds/parts'
import {
  type CosmographyCatalog,
  catalogTable,
  useCosmographyAction,
} from './api'
import { ELEMENTS } from './labels'
import { type Ladder, nameTable } from './ladder'

function NameInput({
  value,
  onChange,
  disabled,
}: {
  value: string
  onChange: (value: string) => void
  disabled: boolean
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id}>
        Name
      </Label>
      <Input
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

export function CreateDimensionForm({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState('')
  const [parent, setParent] = useState('')
  const [element, setElement] = useState('')
  const create = useCosmographyAction<void>(
    'dimension:create',
    () => ({
      name: name.trim(),
      kind,
      parent_dimension_id: parent ? Number(parent) : null,
      element: kind === 'elemental' && element ? element : null,
    }),
    'A new dimension came into being'
  )
  const busy = create.isPending ? 'The dimension is forming' : null
  const missing =
    name.trim() === ''
      ? 'Name the dimension first'
      : kind === ''
        ? 'Choose its kind first'
        : null
  return (
    <AdjustPanel
      title='Bring a dimension into being'
      note='A dimension is a whole layer of existence with its own time, magic, veil and laws.'
      label='Create'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <NameInput value={name} onChange={setName} disabled={busy !== null} />
        <MindPicker
          label='Kind'
          value={kind}
          table={catalogTable(catalog?.dimension_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <MindPicker
          label='Lies within'
          value={parent}
          table={nameTable(ladder.data.dimensions)}
          blocked={
            busy ??
            (ladder.data.dimensions.length === 0
              ? 'No dimension exists yet to hold it'
              : null)
          }
          onPick={setParent}
        />
        <MindPicker
          label='Element'
          value={element}
          table={ELEMENTS}
          blocked={
            busy ??
            (kind === 'elemental'
              ? null
              : 'Only an elemental plane has an element')
          }
          onPick={setElement}
        />
      </div>
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => {
          create.mutate()
          setName('')
        }}
      >
        <Layers />
        Bring it into being
      </Button>
    </AdjustPanel>
  )
}

export function CreateClusterForm({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState('')
  const [dimension, setDimension] = useState('')
  const [parent, setParent] = useState('')
  const create = useCosmographyAction<void>(
    'cluster:create',
    () => ({
      name: name.trim(),
      kind,
      dimension_id: parent ? null : dimension ? Number(dimension) : null,
      parent_cluster_id: parent ? Number(parent) : null,
    }),
    'Galaxies gathered into a new cluster'
  )
  const busy = create.isPending ? 'The cluster is gathering' : null
  const missing =
    name.trim() === ''
      ? 'Name the cluster first'
      : kind === ''
        ? 'Choose its kind first'
        : null
  return (
    <AdjustPanel
      title='Gather a cluster'
      note='Clusters hold galaxies; a group may lie inside a supercluster or a filament.'
      label='Create'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <NameInput value={name} onChange={setName} disabled={busy !== null} />
        <MindPicker
          label='Kind'
          value={kind}
          table={catalogTable(catalog?.cluster_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <MindPicker
          label='Dimension'
          value={dimension}
          table={nameTable(ladder.data.dimensions)}
          blocked={
            busy ??
            (parent ? 'A cluster inside another lies in its dimension' : null)
          }
          onPick={setDimension}
        />
        <MindPicker
          label='Inside cluster'
          value={parent}
          table={nameTable(ladder.data.clusters)}
          blocked={
            busy ??
            (ladder.data.clusters.length === 0
              ? 'No cluster exists yet to hold it'
              : null)
          }
          onPick={setParent}
        />
      </div>
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => {
          create.mutate()
          setName('')
        }}
      >
        <Workflow />
        Gather it
      </Button>
    </AdjustPanel>
  )
}

export function CreateGalaxyForm({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState('')
  const [cluster, setCluster] = useState('')
  const [dimension, setDimension] = useState('')
  const create = useCosmographyAction<void>(
    'galaxy:create',
    () => ({
      name: name.trim(),
      galaxy_type: kind,
      cluster_id: cluster ? Number(cluster) : null,
      dimension_id: cluster ? null : dimension ? Number(dimension) : null,
    }),
    'A new galaxy was set among the others'
  )
  const busy = create.isPending ? 'The galaxy is taking shape' : null
  const missing =
    name.trim() === ''
      ? 'Name the galaxy first'
      : kind === ''
        ? 'Choose its type first'
        : null
  return (
    <AdjustPanel
      title='Set a new galaxy'
      note='A galaxy is laid out with its core, bulge, arms and halo; nurseries in it bear new stars over the epochs.'
      label='Create'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <NameInput value={name} onChange={setName} disabled={busy !== null} />
        <MindPicker
          label='Type'
          value={kind}
          table={catalogTable(catalog?.galaxy_types)}
          blocked={busy}
          onPick={setKind}
        />
        <MindPicker
          label='Cluster'
          value={cluster}
          table={nameTable(ladder.data.clusters)}
          blocked={
            busy ??
            (ladder.data.clusters.length === 0
              ? 'No cluster exists yet; the galaxy can lie straight in a dimension'
              : null)
          }
          onPick={setCluster}
        />
        <MindPicker
          label='Dimension'
          value={dimension}
          table={nameTable(ladder.data.dimensions)}
          blocked={
            busy ??
            (cluster ? 'A galaxy in a cluster lies in its dimension' : null)
          }
          onPick={setDimension}
        />
      </div>
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => {
          create.mutate()
          setName('')
        }}
      >
        <Orbit />
        Set it among the galaxies
      </Button>
    </AdjustPanel>
  )
}
