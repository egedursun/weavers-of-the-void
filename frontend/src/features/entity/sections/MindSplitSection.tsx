import { useState } from 'react'
import { Check, Lock, RotateCcw, Sprout, Undo2, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type ActProp } from '@/api/mutation'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  AttributeTile,
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { type EntryKind } from '@/components/layout/entry/entryStack'
import { Label, Muted, Text } from '@/components/typography'
import { TRAIT_ICONS } from '@/features/entity/mind/labels'
import { STRAINS } from '@/features/folkways/labels'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type IdeaKind,
  type IdeaSource,
  type IdeaState,
  type MindAttribute,
  type MindFacet,
  type MindIdea,
  type MindIdeaSpec,
  type MindSplit,
  signed,
  useMindSplit,
} from '../mind/api'
import {
  LOCKS,
  SKILL_ICONS,
  VALUE_ICONS,
  labelTable,
  named,
  plain,
} from '../mind/labels'
import { AddBar, ControlPanel, MindCard, MindPicker } from '../mind/parts'
import {
  ATTRIBUTE_ICONS,
  FACET_GROUPS,
  IDEA_ICON,
  IDEA_ICONS,
  IDEA_SOURCES,
  IDEA_STATES,
  SPLIT_ICON,
} from '../mind/splitLabels'

const ATTRIBUTE_MAX = 100
const FACET_MIN = -50
const FACET_MAX = 50
const WORKING = 'Working on it.'
const STRONG_ATTRIBUTE = 70
const WEAK_ATTRIBUTE = 30

function nodeKind(kind: string): EntryKind {
  if (kind === 'son') return 'son'
  if (kind === 'foreign_god') return 'foreign-god'
  return 'entity'
}

function attributeTone(value: number): 'success' | 'destructive' | 'default' {
  if (value >= STRONG_ATTRIBUTE) return 'success'
  if (value <= WEAK_ATTRIBUTE) return 'destructive'
  return 'default'
}

function attributeHint(item: MindAttribute): string {
  const skills = item.governs.map((skill) =>
    named(SKILL_ICONS, skill).label.toLowerCase()
  )
  const parts = [
    skills.length > 0 ? `Governs ${skills.join(', ')}` : 'Governs no skill',
  ]
  if (item.effective !== item.value)
    parts.push(
      `${item.effective} while turning ideas over (${signed(item.effective - item.value)})`
    )
  return parts.join('. ')
}

function SplitHero({ view }: { view: MindSplit }) {
  const best = [...view.attributes].sort((a, b) => b.value - a.value)[0]
  const marked = view.facets.filter(
    (item) => Math.abs(item.value) >= view.trait_threshold
  ).length
  const turning = view.ideas.filter(
    (item) => item.state === 'incubating'
  ).length
  const settled = view.ideas.filter(
    (item) => item.state === 'internalised'
  ).length
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/split:grid-cols-2 @3xl/split:grid-cols-4'>
      {best && (
        <KpiTile
          label='Greatest gift'
          value={`${best.label} ${best.value}`}
          icon={named(ATTRIBUTE_ICONS, best.attribute).icon}
          tone='gold'
          meter={{
            value: best.value,
            max: ATTRIBUTE_MAX,
            label: best.label,
          }}
        />
      )}
      {view.has_facets && (
        <KpiTile
          label='Marked facets'
          value={marked}
          icon={SPLIT_ICON}
          tone='verdigris'
          hint={`At ${signed(view.trait_threshold)} or ${signed(-view.trait_threshold)} a facet becomes a trait`}
        />
      )}
      {view.turns_ideas && (
        <KpiTile
          label='Ideas turning over'
          value={`${turning} / ${view.idea_slots}`}
          icon={IDEA_ICON}
          tone='warning'
          meter={{
            value: turning,
            max: view.idea_slots,
            label: 'Room for ideas',
          }}
        />
      )}
      {view.turns_ideas && (
        <KpiTile
          label='Taken to heart'
          value={settled}
          icon={named(IDEA_STATES, 'internalised').icon}
          tone='success'
        />
      )}
    </div>
  )
}

function Attributes({ view }: { view: MindSplit }) {
  const physical = view.attributes.filter((item) => item.physical)
  const mental = view.attributes.filter((item) => !item.physical)
  return (
    <MindCard
      title='Attributes'
      icon={named(ATTRIBUTE_ICONS, 'strength').icon}
      hint='What this body and mind can do, 0 to 100. They grow with use and wane with age and lasting conditions.'
      wide
    >
      {[
        { title: 'Body', items: physical },
        { title: 'Mind', items: mental },
      ].map((group) =>
        group.items.length > 0 ? (
          <div key={group.title} className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>{group.title}</Label>
            <div className='grid min-w-0 grid-cols-2 gap-2 @md/split:grid-cols-3 @3xl/split:grid-cols-4'>
              {group.items.map((item) => (
                <AttributeTile
                  key={item.attribute}
                  icon={named(ATTRIBUTE_ICONS, item.attribute).icon}
                  abbr={item.label}
                  label={item.label}
                  value={item.effective}
                  max={ATTRIBUTE_MAX}
                  hint={attributeHint(item)}
                  tone={attributeTone(item.effective)}
                />
              ))}
            </div>
          </div>
        ) : null
      )}
      {view.summaries.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Muted variant='caption'>Summed up as</Muted>
          {view.summaries.map((item) => (
            <Badge key={item.name} variant='outline'>
              {`${item.name} ${item.value}`}
            </Badge>
          ))}
        </div>
      )}
    </MindCard>
  )
}

function FacetBar({ item, threshold }: { item: MindFacet; threshold: number }) {
  const trait = item.value >= 0 ? item.high_trait : item.low_trait
  const marked = Math.abs(item.value) >= threshold
  return (
    <div className='flex min-w-0 flex-col gap-0.5'>
      <StatBar
        label={`${item.label} ${signed(item.value)}`}
        value={Math.abs(item.value)}
        max={FACET_MAX}
        tone={marked ? 'warning' : 'default'}
        showMax={false}
      />
      <Muted variant='caption'>
        {`Their people lean ${signed(item.mean)}${marked && trait ? ` · makes them ${TRAIT_ICONS[trait].label.toLowerCase()}` : ''}`}
      </Muted>
    </div>
  )
}

function Facets({ view }: { view: MindSplit }) {
  return (
    <MindCard
      title='Facets'
      icon={SPLIT_ICON}
      hint='How this one reacts, -50 to +50 around what their people lean toward. Facets set how strongly events move them, how stress builds and how a mind breaks.'
      wide
    >
      <div className='grid min-w-0 grid-cols-1 gap-4 @xl/split:grid-cols-2'>
        {Object.entries(FACET_GROUPS).map(([group, spec]) => {
          const items = view.facets
            .filter((item) => item.group === group)
            .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
          return items.length > 0 ? (
            <div key={group} className='flex min-w-0 flex-col gap-2'>
              <div className='flex min-w-0 items-center gap-2'>
                <Medallion icon={spec.icon} size='sm' />
                <Label variant='overline'>{spec.label}</Label>
              </div>
              <Paged items={items} initial={4} noun={['facet', 'facets']}>
                {(item) => (
                  <FacetBar
                    key={item.facet}
                    item={item}
                    threshold={view.trait_threshold}
                  />
                )}
              </Paged>
            </div>
          ) : null
        })}
      </div>
    </MindCard>
  )
}

function shifts(spec: MindIdeaSpec): string[] {
  return [
    ...spec.beliefs.map(
      (item) => `${named(VALUE_ICONS, item.axis).label} ${signed(item.value)}`
    ),
    ...spec.gains.map((item) => `${item.label} +${item.value}`),
    ...spec.costs.map((item) => `${item.label} -${item.value}`),
    ...spec.facets.map((item) => `${item.label} ${signed(item.value)}`),
  ]
}

function IdeaCard({
  idea,
  blocked,
  onSettle,
  onSource,
  onStrain,
  onRemove,
  act,
}: {
  idea: MindIdea
  blocked: string | null
  onSettle: (state: IdeaState) => void
  onSource: (source: IdeaSource) => void
  onStrain: (strain: MindIdea['strain']) => void
  onRemove: () => void
  act?: ActProp
}) {
  const spec = named(IDEA_ICONS, idea.idea)
  const state = named(IDEA_STATES, idea.state)
  const source = named(IDEA_SOURCES, idea.source)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} size='sm' tone={state.tone} />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {idea.label}
          </Text>
          <Muted variant='caption' truncate>
            {`${source.label} · since epoch ${idea.started_epoch}${idea.finished_epoch !== null ? `, settled in epoch ${idea.finished_epoch}` : ''}`}
          </Muted>
        </div>
        <Badge variant={idea.state === 'internalised' ? 'default' : 'outline'}>
          {state.label}
        </Badge>
      </div>
      {idea.source_node && (
        <EntityLink
          kind={nodeKind(idea.source_node.kind)}
          id={String(idea.source_node.id)}
          showIcon
        >
          {idea.source_node.name}
        </EntityLink>
      )}
      <div className='flex min-w-0 items-center gap-2'>
        <Progress
          value={idea.progress}
          size='sm'
          tone={idea.state === 'rejected' ? 'default' : 'success'}
          aria-label={`${idea.label} progress`}
        />
        <Muted variant='caption'>{`${idea.progress}%`}</Muted>
      </div>
      <MindPicker
        act={act}
        label='Where it came from'
        value={idea.source}
        table={labelTable(IDEA_SOURCES)}
        blocked={blocked}
        onPick={(value) => onSource(value as IdeaSource)}
      />
      <MindPicker
        act={act}
        label='How it strains the mind while it turns'
        value={idea.strain}
        table={labelTable(STRAINS)}
        blocked={blocked}
        onPick={(value) => onStrain(value as MindIdea['strain'])}
      />
      <Muted variant='caption'>
        {idea.fit >= 0
          ? `Sits well with their beliefs (${signed(idea.fit)})`
          : `Grates against their beliefs (${signed(idea.fit)})`}
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {idea.state === 'incubating' && (
          <>
            <Button
              act={act}
              size='sm'
              variant='outline'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => onSettle('internalised')}
            >
              <Check />
              Settle it now
            </Button>
            <Button
              act={act}
              size='sm'
              variant='ghost'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => onSettle('rejected')}
            >
              <Undo2 />
              Let it go
            </Button>
          </>
        )}
        {idea.state === 'rejected' && (
          <Button
            act={act}
            size='sm'
            variant='outline'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => onSettle('incubating')}
          >
            <RotateCcw />
            Turn it over again
          </Button>
        )}
        <Button
          act={act}
          size='icon-sm'
          variant='ghost'
          aria-label={`Take away ${idea.label}`}
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onRemove}
        >
          <X />
        </Button>
      </div>
    </div>
  )
}

function Ideas({ view }: { view: MindSplit }) {
  const { reason } = useGodGate()
  const [picked, setPicked] = useState('')
  const settle = useGodAction({
    writes: [{ lever: 'mind:idea_edit' }],
    run: ({ id, state }: { id: number; state: IdeaState }) =>
      unwrap(
        api.POST('/api/actions/mind:idea_edit', {
          body: { idea_id: id, state, clear_source: false },
        })
      ),
  })
  const source = useGodAction({
    writes: [{ lever: 'mind:idea_edit' }],
    run: ({ id, kind }: { id: number; kind: IdeaSource }) =>
      unwrap(
        api.POST('/api/actions/mind:idea_edit', {
          body: { idea_id: id, source: kind, clear_source: false },
        })
      ),
  })
  const strain = useGodAction({
    writes: [{ lever: 'mind:idea_edit' }],
    run: ({ id, kind }: { id: number; kind: MindIdea['strain'] }) =>
      unwrap(
        api.POST('/api/actions/mind:idea_edit', {
          body: { idea_id: id, strain: kind, clear_source: false },
        })
      ),
  })
  const remove = useGodAction({
    writes: [{ lever: 'mind:idea_remove' }],
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/mind:idea_remove', { body: { idea_id: id } })
      ),
  })
  const plant = useGodAction({
    writes: [{ lever: 'mind:idea' }],
    run: (idea: IdeaKind) =>
      unwrap(
        api.POST('/api/actions/mind:idea', {
          body: {
            node_id: view.node_id,
            idea,
            progress: 0,
            state: 'incubating',
            source: 'player',
          },
        })
      ),
    onDone: () => setPicked(''),
  })
  const blocked =
    reason() ??
    (settle.isPending ||
    source.isPending ||
    strain.isPending ||
    remove.isPending ||
    plant.isPending
      ? WORKING
      : null)
  const held = new Set(view.ideas.map((item) => item.idea))
  const choices = Object.fromEntries(
    view.catalogue
      .filter((item) => !held.has(item.idea))
      .map((item) => [item.idea, item.label])
  )
  const preview = view.catalogue.find((item) => item.idea === picked)
  const none = Object.keys(choices).length === 0
  return (
    <MindCard
      title='Ideas'
      icon={IDEA_ICON}
      hint='Ideas met in ideologies, doctrines, what their people know, books and teachers. They incubate for seasons, costing focus, then settle in or are let go.'
      wide
    >
      {view.ideas.length === 0 ? (
        <EmptyState
          icon={IDEA_ICON}
          size='compact'
          title='No ideas yet'
          description='This mind has not met an idea to turn over. Plant one below, or let the world bring one.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/split:grid-cols-2'>
          <Paged items={view.ideas} initial={4} noun={['idea', 'ideas']}>
            {(idea) => (
              <IdeaCard
                act={[settle, source, strain, remove]}
                key={idea.id}
                idea={idea}
                blocked={blocked}
                onSettle={(state) => settle.mutate({ id: idea.id, state })}
                onSource={(kind) => source.mutate({ id: idea.id, kind })}
                onStrain={(kind) => strain.mutate({ id: idea.id, kind })}
                onRemove={() => remove.mutate(idea.id)}
              />
            )}
          </Paged>
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-2 rounded-md p-2 sealed-well'>
        <AddBar
          title='Plant an idea'
          action={
            <Button
              act={plant}
              size='sm'
              disabled={blocked !== null || picked === ''}
              disabledReason={blocked ?? 'Choose an idea first.'}
              onClick={() => plant.mutate(picked as IdeaKind)}
            >
              <Sprout />
              Plant
            </Button>
          }
        >
          <MindPicker
            label='Idea'
            value={picked}
            table={choices}
            blocked={
              blocked ?? (none ? 'This mind already knows every idea.' : null)
            }
            placeholder='Choose an idea'
            onPick={setPicked}
          />
        </AddBar>
        {preview && (
          <div className='flex min-w-0 flex-col gap-1'>
            <Muted variant='caption'>
              {`Once taken to heart it brings: ${shifts(preview).join(', ')}. While it incubates it costs ${plural(preview.distraction, 'focu', 'focus')}.`}
            </Muted>
          </div>
        )}
      </div>
    </MindCard>
  )
}

function splitGroups(view: MindSplit): AdjustGroup[] {
  const groups: AdjustGroup[] = []
  if (view.attributes.length > 0)
    groups.push({
      title: 'Attributes (0 to 100)',
      fields: view.attributes.map((item) => ({
        key: `attribute:${item.attribute}`,
        label: item.label,
        value: item.value,
        min: 0,
        max: ATTRIBUTE_MAX,
      })),
    })
  if (view.facets.length > 0)
    groups.push({
      title: 'Facets (-50 to +50)',
      fields: view.facets.map((item) => ({
        key: `facet:${item.facet}`,
        label: item.label,
        value: item.value,
        min: FACET_MIN,
        max: FACET_MAX,
      })),
    })
  const turning = view.ideas.filter((item) => item.state === 'incubating')
  if (turning.length > 0)
    groups.push({
      title: 'Idea progress (0 to 100)',
      fields: turning.map((item) => ({
        key: `idea:${item.id}`,
        label: item.label,
        value: item.progress,
        min: 0,
        max: ATTRIBUTE_MAX,
      })),
    })
  return groups
}

function SplitControls({ view }: { view: MindSplit }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const set = ({ key, value }: { key: string; value: number }) => {
    const [kind, name] = key.split(':')
    if (kind === 'attribute')
      return unwrap(
        api.POST('/api/actions/mind:attributes', {
          body: {
            node_id: view.node_id,
            values: { [name]: value },
            lock: hold,
          },
        })
      )
    if (kind === 'facet')
      return unwrap(
        api.POST('/api/actions/mind:facets', {
          body: {
            node_id: view.node_id,
            values: { [name]: value },
            lock: hold,
          },
        })
      )
    return unwrap(
      api.POST('/api/actions/mind:idea_edit', {
        body: { idea_id: Number(name), progress: value, clear_source: false },
      })
    )
  }
  const lock = useGodAction({
    writes: [{ lever: 'mind:lock' }],
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/mind:lock', {
          body: { node_id: view.node_id, field },
        })
      ),
  })
  const release = useGodAction({
    writes: [{ lever: 'mind:unlock' }],
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/mind:unlock', {
          body: { node_id: view.node_id, field },
        })
      ),
  })
  const busy =
    reason() ?? (lock.isPending || release.isPending ? WORKING : null)
  const held = new Set(view.locked)
  return (
    <ControlPanel
      title='Shape body, temper and ideas'
      note={
        view.lockable.length > 0
          ? 'Set any attribute, facet or idea. A held part stops changing with the world until you release it. Every change goes into the ledger and can be undone.'
          : 'Set any attribute. Hold this one whole from the mechanics panel to keep the world from changing it. Every change goes into the ledger and can be undone.'
      }
      hold={view.lockable.length > 0 ? hold : undefined}
      onHold={view.lockable.length > 0 ? setHold : undefined}
    >
      {view.lockable.length > 0 && (
        <PagedList
          items={view.lockable}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap items-center gap-2'
          itemKey={(field) => field}
        >
          {(field) =>
            held.has(field) ? (
              <Button
                act={release}
                key={field}
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => release.mutate(field)}
              >
                <Unlock />
                {`Release ${plain(LOCKS, field)}`}
              </Button>
            ) : (
              <Button
                act={lock}
                key={field}
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => lock.mutate(field)}
              >
                <Lock />
                {`Hold ${plain(LOCKS, field)}`}
              </Button>
            )
          }
        </PagedList>
      )}
      <AdjustStats
        id={`split-${view.node_id}`}
        groups={splitGroups(view)}
        note='Attributes run from 0 to 100, facets from -50 to +50 and idea progress from 0 to 100.'
        run={set}
      />
    </ControlPanel>
  )
}

export function MindSplitSection({ nodeId }: { nodeId: number }) {
  const query = useMindSplit(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-mind-split'
        title='Body, temper and ideas'
        icon={SPLIT_ICON}
      >
        <EmptyState
          icon={SPLIT_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view || (!view.has_attributes && !view.has_facets)) return null
  return (
    <Section
      id='section-mind-split'
      title='Body, temper and ideas'
      description='Mortals, beasts, sons and foreign gods have attributes; mortals and gods also have a temperament of facets, and mortals turn ideas over. Places, peoples and things have none of these.'
      icon={SPLIT_ICON}
    >
      <div className='@container/split flex min-w-0 flex-col gap-4'>
        <SplitHero view={view} />
        {view.attributes.length === 0 && view.facets.length === 0 ? (
          <EmptyState
            icon={SPLIT_ICON}
            title='Not measured yet'
            description='The next epoch measures what this one can do and how they react.'
          />
        ) : (
          <div className='grid min-w-0 grid-cols-1 gap-3'>
            {view.attributes.length > 0 && <Attributes view={view} />}
            {view.facets.length > 0 && <Facets view={view} />}
            {view.turns_ideas && <Ideas view={view} />}
          </div>
        )}
        <SplitControls view={view} />
      </div>
    </Section>
  )
}
