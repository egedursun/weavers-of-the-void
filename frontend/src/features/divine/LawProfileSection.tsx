import { useState } from 'react'
import { Orbit, Save, Scale, ShieldAlert, TriangleAlert } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  lawExceptionValues,
  lawScopeValues,
  naturalLawValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Section, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { wordOf } from '@/features/entity/affairs/labels'
import { busyOf } from '@/features/entity/lore/model'
import {
  AdjustPanel,
  Card,
  Held,
  NumberField,
} from '@/features/entity/wilds/parts'
import { useWorldState } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useDivineAction, useLawProfile } from './api'
import { LAW_EXCEPTIONS, LAW_SCOPES, heldLabel } from './labels'
import { useGodTable } from './model'
import { NodeName, PickRow } from './parts'

export function LawProfileSection({ lawId }: { lawId: number }) {
  const view = useLawProfile(lawId)
  const { reason } = useGodGate()
  const edit = useDivineAction(
    'law_profile:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      law_id: lawId,
      ...vars,
    })
  )
  const [effect, setEffect] = useState('')
  const [scope, setScope] = useState('')
  const [world, setWorld] = useState<number | null>(null)
  const [region, setRegion] = useState<number | null>(null)
  const [strength, setStrength] = useState('')
  const [stability, setStability] = useState('')
  const [exception, setException] = useState('')
  const [kind, setKind] = useState<number | null>(null)
  const [author, setAuthor] = useState('')
  const state = useWorldState()
  const authors = useGodTable(
    state.data?.creator
      ? { id: state.data.creator.id, name: state.data.creator.name }
      : null
  )
  const busy = busyOf(reason(), edit.isPending)
  const values: EditValues = {}
  if (effect !== '') values.effect = effect
  if (scope !== '') values.scope = scope
  if (world !== null) values.world_id = world
  if (region !== null) values.region_entity_id = region
  if (strength !== '') values.strength = Number(strength)
  if (stability !== '') values.stability = Number(stability)
  if (exception !== '') values.exception = exception
  if (kind !== null) values.exempt_kind_entity_id = kind
  if (author !== '') values.author_node_id = Number(author)
  const nothing =
    Object.keys(values).length === 0 ? 'Change something first' : null
  const effects = Object.fromEntries(
    naturalLawValues
      .filter((value) => value !== 'none')
      .map((value) => [value, wordOf(naturalLawValues, value)])
  )
  const scopes = Object.fromEntries(
    lawScopeValues.map((value) => [value, LAW_SCOPES[value].label])
  )
  const exceptions = Object.fromEntries(
    lawExceptionValues.map((value) => [value, LAW_EXCEPTIONS[value]])
  )
  return (
    <Section
      id='section-law-profile'
      title='How the law works'
      description='Its scope, strength and stability, its author who keeps it with essence, and those it spares. A law weakens when its author cannot keep it and contests the laws that contradict it.'
      icon={Scale}
      tone='gold'
    >
      {view.isPending && <LoadingBlock label='Reading the law’s working' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its working could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='LawProfile'
          className='@container/wild grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'
        >
          <Card
            title={view.data.effect_label}
            icon={Orbit}
            tone='gold'
            hint={view.data.effect_text}
            wide
          >
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant='default'>
                {LAW_SCOPES[view.data.scope].label}
              </Badge>
              {view.data.world && <NodeName item={view.data.world} />}
              {view.data.region && <NodeName item={view.data.region} />}
              <Badge variant='outline'>
                {LAW_EXCEPTIONS[view.data.exception]}
              </Badge>
              {view.data.exempt_kind && (
                <NodeName item={view.data.exempt_kind} />
              )}
              {view.data.drafted && (
                <Badge variant='outline'>
                  Not yet set by the world; what you set holds at once
                </Badge>
              )}
              {view.data.contested && (
                <Badge variant='warning'>
                  <ShieldAlert aria-hidden='true' />
                  Deadlocked with a contrary law
                </Badge>
              )}
            </div>
            <StatBar
              label='Strength'
              value={view.data.strength}
              max={100}
              tone='default'
            />
            <StatBar
              label='Stability'
              value={view.data.stability}
              max={100}
              tone='success'
            />
            <Muted variant='caption'>
              {view.data.author
                ? 'Kept by its author:'
                : 'No author keeps it; it will weaken.'}
            </Muted>
            {view.data.author && <NodeName item={view.data.author} />}
            <Text
              as='span'
              variant='caption'
            >{`Last weighed in epoch ${view.data.updated_epoch}`}</Text>
            <Held
              keys={view.data.locked}
              label={heldLabel}
              busy={busy}
              onRelease={() =>
                edit.mutate({ values: {}, release: view.data?.locked ?? [] })
              }
            />
            <AdjustPanel
              title='Reshape the law'
              note='What you set is held: the world will not erode or move it until you let it decide again.'
            >
              <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
                <PickRow
                  label='What the law does'
                  table={effects}
                  value={effect}
                  blocked={busy}
                  onPick={setEffect}
                />
                <PickRow
                  label='Scope'
                  table={scopes}
                  value={scope}
                  blocked={busy}
                  onPick={setScope}
                />
                <PickRow
                  label='Exception'
                  table={exceptions}
                  value={exception}
                  blocked={busy}
                  onPick={setException}
                />
                <PickRow
                  label='Author who keeps it'
                  table={authors}
                  value={author}
                  blocked={busy}
                  onPick={setAuthor}
                />
                <EntityPicker
                  types={['species', 'people']}
                  value={kind}
                  onChange={setKind}
                  placeholder='Kind of being it spares'
                />
                <EntityPicker
                  types={['world']}
                  value={world}
                  onChange={setWorld}
                  placeholder='World it covers'
                />
                <EntityPicker
                  types={['region']}
                  value={region}
                  onChange={setRegion}
                  placeholder='Land it covers'
                />
                <NumberField
                  label='Strength'
                  value={strength}
                  min={0}
                  max={100}
                  disabled={busy !== null}
                  onChange={setStrength}
                />
                <NumberField
                  label='Stability'
                  value={stability}
                  min={0}
                  max={100}
                  disabled={busy !== null}
                  onChange={setStability}
                />
              </div>
              <Button
                disabled={busy !== null || nothing !== null}
                disabledReason={busy ?? nothing ?? undefined}
                onClick={() => {
                  edit.mutate({ values, release: [] })
                  setEffect('')
                  setScope('')
                  setWorld(null)
                  setRegion(null)
                  setStrength('')
                  setStability('')
                  setException('')
                  setAuthor('')
                }}
              >
                <Save />
                Hold the law this way
              </Button>
            </AdjustPanel>
          </Card>
        </div>
      )}
    </Section>
  )
}
