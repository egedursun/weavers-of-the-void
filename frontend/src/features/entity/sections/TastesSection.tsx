import { useState } from 'react'
import { Minus, Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  PagedList,
  Section,
  FieldTile,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type CultureMind,
  type Preference,
  type PreferenceKind,
  useCultureMind,
} from '../mind/api'
import { PREFERENCE_KINDS, TASTES_ICON } from '../mind/cultureLabels'
import { named } from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'

const SPAN = 100
const STEP = 20
const WORKING = 'Working on it.'
const STRENGTHS: Record<string, string> = {
  '80': 'Loves it (+80)',
  '40': 'Likes it (+40)',
  '-40': 'Dislikes it (-40)',
  '-80': 'Hates it (-80)',
}

function TasteChip({
  item,
  blocked,
  onSet,
  onRemove,
}: {
  item: Preference
  blocked: string | null
  onSet: (strength: number) => void
  onRemove: () => void
}) {
  const loved = item.strength > 0
  return (
    <div className='flex min-w-0 items-center gap-1 rounded-md border surface-well border-gild/20 bg-muted/60 px-2 py-1'>
      <Badge
        variant={loved ? 'default' : 'outline'}
      >{`${item.strength > 0 ? '+' : ''}${item.strength}`}</Badge>
      {item.target_node ? (
        <EntityLink kind='entity' id={String(item.target_node.id)}>
          {item.target_label}
        </EntityLink>
      ) : (
        <Text as='span' variant='caption' truncate>
          {item.target_label}
        </Text>
      )}
      {item.held && <Muted variant='caption'>held</Muted>}
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label={`Like ${item.target_label} less`}
        disabled={blocked !== null || item.strength <= -SPAN}
        disabledReason={blocked ?? 'It is already hated as much as it can be.'}
        onClick={() => onSet(Math.max(-SPAN, item.strength - STEP))}
      >
        <Minus />
      </Button>
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label={`Like ${item.target_label} more`}
        disabled={blocked !== null || item.strength >= SPAN}
        disabledReason={blocked ?? 'It is already loved as much as it can be.'}
        onClick={() => onSet(Math.min(SPAN, item.strength + STEP))}
      >
        <Plus />
      </Button>
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label={`Forget the feeling for ${item.target_label}`}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={onRemove}
      >
        <X />
      </Button>
    </div>
  )
}

function KindCard({
  kind,
  items,
  blocked,
  onSet,
  onRemove,
}: {
  kind: string
  items: Preference[]
  blocked: string | null
  onSet: (item: Preference, strength: number) => void
  onRemove: (item: Preference) => void
}) {
  const spec = named(PREFERENCE_KINDS, kind)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} size='sm' tone={spec.tone} />
        <Label variant='overline'>{spec.label}</Label>
      </div>
      <PagedList
        items={items}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(item) => item.id}
      >
        {(item) => (
          <TasteChip
            key={item.id}
            item={item}
            blocked={blocked}
            onSet={(strength) => onSet(item, strength)}
            onRemove={() => onRemove(item)}
          />
        )}
      </PagedList>
    </div>
  )
}

function TasteControls({ view }: { view: CultureMind }) {
  const { reason } = useGodGate()
  const names = useNames()
  const [kind, setKind] = useState<string>('food')
  const [target, setTarget] = useState<string | null>(null)
  const [strength, setStrength] = useState<string>('80')
  const spec = view.preference_kinds.find((item) => item.kind === kind)
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/preference:set', {
          body: {
            holder_id: view.node_id,
            kind: kind as PreferenceKind,
            target: target ?? '',
            strength: Number(strength),
            hold: true,
          },
        })
      ),
    onDone: () => setTarget(null),
  })
  const busy = reason() ?? (set.isPending ? WORKING : null)
  const kinds = Object.fromEntries(
    view.preference_kinds.map((item) => [item.kind, item.label])
  )
  const wanted = kind === 'creature' ? 'species' : 'resource'
  const options = spec?.from_records
    ? (names.data ?? [])
        .filter((entry) => entry.type === wanted)
        .map((entry) => ({ value: String(entry.id), label: entry.name }))
    : (spec?.targets ?? []).map((item) => ({
        value: item,
        label: item.replace(/_/g, ' '),
      }))
  return (
    <ControlPanel
      title='Shape tastes'
      note='Give a like or a dislike of any kind; what you set is held until you change it. Raise or lower any taste above, or take it away. Every change goes into the ledger and can be undone.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/taste:grid-cols-4'>
        <MindPicker
          label='Kind of taste'
          value={kind}
          table={kinds}
          blocked={busy}
          onPick={(value) => {
            setKind(value)
            setTarget(null)
          }}
        />
        <FieldTile label='What'>
          <RecordCombobox
            options={options}
            value={target}
            onChange={(next) => setTarget(next)}
            placeholder='Choose what they feel for'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            aria-label='What they feel for'
          />
        </FieldTile>
        <MindPicker
          label='How much'
          value={strength}
          table={STRENGTHS}
          blocked={busy}
          onPick={setStrength}
        />
        <Button
          className='self-end'
          size='sm'
          disabled={busy !== null || target === null}
          disabledReason={busy ?? 'Choose what they feel for first.'}
          onClick={() => set.mutate()}
        >
          <Plus />
          Set the taste
        </Button>
      </div>
    </ControlPanel>
  )
}

export function TastesSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useCultureMind(nodeId)
  const view = query.data
  const set = useGodAction({
    run: ({ item, strength }: { item: Preference; strength: number }) =>
      unwrap(
        api.POST('/api/actions/preference:set', {
          body: {
            holder_id: nodeId,
            kind: item.kind,
            target: item.target,
            strength,
            hold: true,
          },
        })
      ),
  })
  const remove = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/preference:remove', {
          body: { preference_id: id },
        })
      ),
  })
  if (query.isError)
    return (
      <Section
        id='section-tastes'
        title='Likes and dislikes'
        icon={TASTES_ICON}
      >
        <EmptyState
          icon={TASTES_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view || !view.has_preferences) return null
  const busy = reason() ?? (set.isPending || remove.isPending ? WORKING : null)
  const groups = Object.keys(PREFERENCE_KINDS)
    .map((kind) => ({
      kind,
      items: view.preferences.filter((item) => item.kind === kind),
    }))
    .filter((group) => group.items.length > 0)
  const loves = view.preferences.filter((item) => item.strength > 0).length
  return (
    <Section
      id='section-tastes'
      title='Likes and dislikes'
      description='Only mortals and peoples hold tastes. A people loves and hates as its land, gods, art and beliefs lead it; its mortals start from it and drift with their own lives.'
      icon={TASTES_ICON}
    >
      <div className='@container/taste flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/taste:grid-cols-3'>
          <KpiTile
            label='Loves'
            value={loves}
            icon={TASTES_ICON}
            tone='success'
          />
          <KpiTile
            label='Dislikes'
            value={view.preferences.length - loves}
            icon={named(PREFERENCE_KINDS, 'food').icon}
            tone='danger'
          />
          {view.totem ? (
            <KpiTile
              label='Totem'
              value={view.totem.name}
              icon={named(PREFERENCE_KINDS, 'creature').icon}
              tone='verdigris'
              hint='Spared from their hunts'
            />
          ) : (
            <KpiTile
              label='Totem'
              value='None'
              icon={named(PREFERENCE_KINDS, 'creature').icon}
              tone='muted'
              hint='A creature they love dearly becomes one'
            />
          )}
        </div>
        {groups.length === 0 ? (
          <EmptyState
            icon={TASTES_ICON}
            title='No tastes yet'
            description='The next epoch gives them likes and dislikes; you can set some below.'
          />
        ) : (
          <MindCard
            title='Tastes'
            icon={TASTES_ICON}
            hint='Each taste moves prices, renown, mood, taboos or totems.'
            wide
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 @xl/taste:grid-cols-2'>
              <Paged items={groups} initial={6} noun={['kind', 'kinds']}>
                {(group) => (
                  <KindCard
                    key={group.kind}
                    kind={group.kind}
                    items={group.items}
                    blocked={busy}
                    onSet={(item, strength) => set.mutate({ item, strength })}
                    onRemove={(item) => remove.mutate(item.id)}
                  />
                )}
              </Paged>
            </div>
          </MindCard>
        )}
        <TasteControls view={view} />
      </div>
    </Section>
  )
}
