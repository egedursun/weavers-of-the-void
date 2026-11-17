import { useState } from 'react'
import { Ban, Crown, Link2 } from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import { useNames } from '@/features/entity/api/queries'
import { MindPicker } from '@/features/entity/mind/parts'
import { MIND_SEATS } from '@/features/minds/labels'
import {
  type CosmicBeingRecord,
  type CosmographyCatalog,
  catalogLabel,
  catalogTable,
  useCosmography,
  useCosmographyAction,
} from './api'
import {
  BEING_AGENDAS,
  BEING_PHASES,
  BEING_SCALES,
  BEING_SENSES,
} from './labels'
import { type Ladder, ladderOf, nameTable } from './ladder'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  NodeLink,
  RecordEditor,
  RecordPick,
  RecordRow,
} from './parts'
import { drawerKindOf } from './visual/drawerKind'

const phaseTable = Object.fromEntries(
  Object.entries(BEING_PHASES).map(([key, value]) => [key, value.label])
)

export function BeingCard({
  being,
  ladder,
  catalog,
}: {
  being: CosmicBeingRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction(
    'cosmic_being:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      being_id: being.entity_id,
      ...vars,
    })
  )
  const bind = useCosmographyAction(
    'cosmic_being:bind',
    (_: void) => ({ being_id: being.entity_id }),
    'The being is bound to you'
  )
  const banish = useCosmographyAction(
    'cosmic_being:banish',
    (_: void) => ({ being_id: being.entity_id }),
    'The being is banished'
  )
  const busy =
    edit.isPending || bind.isPending || banish.isPending ? 'Working' : null
  const names = useNames()
  const named = new Map((names.data ?? []).map((row) => [row.id, row]))
  const nameOf = (id: number | null | undefined, none: string) =>
    id === null || id === undefined
      ? none
      : (named.get(id)?.name ??
        ladder.data.world_names[String(id)] ??
        ladder.names.get(id))
  const phase = BEING_PHASES[being.phase]
  const bound = being.phase === 'bound'
  const banished = being.phase === 'banished'
  return (
    <RecordRow
      icon={phase.icon}
      tone={phase.tone}
      title={
        <EntityLink kind='entity' id={String(being.entity_id)}>
          {being.name}
        </EntityLink>
      }
      caption={`${catalogLabel(catalog?.being_kinds, being.being_kind)} · ${BEING_SCALES[being.scale]} scale · ${phase.label} · aim: ${BEING_AGENDAS[being.agenda].toLowerCase()}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || bound}
            disabledReason={busy ?? (bound ? 'It is already bound' : undefined)}
            onClick={() => bind.mutate()}
          >
            <Link2 />
            Bind
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null || banished}
            disabledReason={
              busy ?? (banished ? 'It is already banished' : undefined)
            }
            onClick={() => banish.mutate()}
          >
            <Ban />
            Banish
          </Button>
        </div>
      }
    >
      <Meter label='Might' value={being.might} tone='warning' />
      <Facts
        items={[
          [
            'Home',
            <NodeLink
              key='home'
              kind='dimension'
              id={being.home_dimension_id}
              name={
                being.home_dimension_id !== null
                  ? ladder.names.get(being.home_dimension_id)
                  : 'The great dark'
              }
            />,
          ],
          [
            'Roams',
            <NodeLink
              key='roams'
              kind='galaxy'
              id={being.galaxy_id}
              name={
                being.galaxy_id !== null
                  ? ladder.names.get(being.galaxy_id)
                  : 'No galaxy'
              }
            />,
          ],
          [
            'Now on',
            <NodeLink
              key='on'
              kind='world'
              id={being.world_id}
              name={nameOf(being.world_id, 'No world')}
            />,
          ],
          [
            'Aims at',
            <NodeLink
              key='aim'
              kind='world'
              id={being.target_world_id}
              name={nameOf(being.target_world_id, 'Nothing')}
            />,
          ],
          [
            'Bound by',
            <NodeLink
              key='bound'
              kind={drawerKindOf(named.get(being.bound_by_node_id ?? 0)?.kind)}
              id={being.bound_by_node_id}
              name={nameOf(being.bound_by_node_id, 'No one')}
            />,
          ],
          [
            'Mirrors',
            <NodeLink
              key='mirror'
              kind='entity'
              id={being.mirrored_entity_id}
              name={nameOf(being.mirrored_entity_id, 'No one')}
            />,
          ],
          ['Held in', MIND_SEATS[being.substrate].label],
          ['Shows itself', BEING_SENSES[being.sense]],
          [
            'Through a rift',
            being.rift_id !== null ? 'Yes, an open rift' : 'No',
          ],
          [
            'Manifest',
            being.manifest_epochs > 0
              ? plural(being.manifest_epochs, 'epoch')
              : 'Not yet',
          ],
        ]}
      />
      <RecordEditor
        title='Reshape this being'
        note='Might, phase, aim, scale and home you set are held until you release them.'
        fields={[
          { key: 'might', label: 'Might', kind: 'number', min: 0, max: 100 },
          { key: 'phase', label: 'Phase', kind: 'pick', table: phaseTable },
          { key: 'agenda', label: 'Aim', kind: 'pick', table: BEING_AGENDAS },
          { key: 'scale', label: 'Scale', kind: 'pick', table: BEING_SCALES },
          {
            key: 'home_dimension_id',
            label: 'Home dimension',
            kind: 'pick',
            table: nameTable(ladder.data.dimensions),
          },
          {
            key: 'galaxy_id',
            label: 'Galaxy it roams',
            kind: 'pick',
            table: nameTable(ladder.data.galaxies),
          },
        ]}
        locked={being.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function CallForm({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const [kind, setKind] = useState('')
  const [world, setWorld] = useState('')
  const [region, setRegion] = useState<number | null>(null)
  const call = useCosmographyAction(
    'cosmic_being:call',
    (_: void) => ({
      kind: kind as ActionBody<'cosmic_being:call'>['kind'],
      world_id: Number(world),
      region_id: region,
    }),
    'A cosmic being answers your call'
  )
  const busy = call.isPending ? 'The being is coming' : null
  const missing =
    kind === '' || world === '' ? 'Choose a kind and a world first' : null
  return (
    <ForgeCard
      icon={Crown}
      tone='warning'
      title='Call a cosmic being'
      note='Choose its kind and the world it comes to; a region is where it first stands.'
      columns={3}
      meta={
        <Chip icon={Crown}>{`${ladder.data.beings.length} in the cosmos`}</Chip>
      }
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => call.mutate()}
        >
          <Crown />
          Call it
        </Button>
      }
    >
      <MindPicker
        label='Kind'
        value={kind}
        table={catalogTable(catalog?.being_kinds)}
        blocked={busy}
        onPick={setKind}
      />
      <MindPicker
        label='World'
        value={world}
        table={ladder.data.world_names}
        blocked={busy}
        onPick={setWorld}
      />
      <RecordPick
        label='Region'
        types={['region']}
        value={region}
        onChange={setRegion}
        worldId={world ? Number(world) : undefined}
      />
    </ForgeCard>
  )
}

export function BeingsPanel({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  return (
    <Section
      id='section-cosmic-being'
      title='Cosmic beings'
      description='Beings of galaxies and dimensions, with their scale, phase and aim.'
      icon={Crown}
      tone='warning'
    >
      <div
        data-surface='CosmicBeingSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {ladder.data.beings.length === 0 ? (
          <EmptyState
            icon={Crown}
            size='inline'
            title='No cosmic being walks the cosmos'
            description='Call one below, or wait for the veils to thin.'
          />
        ) : (
          <PagedList
            items={ladder.data.beings}
            initial={5}
            noun={['being', 'beings']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.entity_id}
          >
            {(row) => (
              <BeingCard being={row} ladder={ladder} catalog={catalog} />
            )}
          </PagedList>
        )}
        <CallForm ladder={ladder} catalog={catalog} />
      </div>
    </Section>
  )
}

export function CosmicBeingSection({
  entityId,
  catalog,
}: {
  entityId: number
  catalog?: CosmographyCatalog
}) {
  const view = useCosmography()
  if (!view.data) return null
  const ladder = ladderOf(view.data)
  const being = view.data.beings.find((row) => row.entity_id === entityId)
  return (
    <Section
      id='section-cosmic-being'
      title='As a cosmic being'
      icon={Crown}
      tone='warning'
    >
      {being ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          <BeingCard being={being} ladder={ladder} catalog={catalog} />
        </ul>
      ) : (
        <EmptyState
          icon={Crown}
          size='inline'
          title='No profile yet'
          description='Its profile forms at the next epoch.'
        />
      )}
    </Section>
  )
}
