import { useMemo, useState } from 'react'
import {
  Castle,
  ChevronsDown,
  ChevronsUp,
  Crosshair,
  GitFork,
  HeartHandshake,
  Layers,
  type LucideIcon,
  Link2,
  Maximize2,
  Minus,
  Plus,
  Search,
  Skull,
  Sprout,
  Users,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  EmptyState,
  FieldTile,
  LoadingBlock,
  MiniStat,
  Paged,
  Portrait,
} from '@/components/domain'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { INK_FILLS } from '@/features/collective/inks'
import { UNION_FORMS, UNION_PURPOSES } from '@/features/cycles/unionLabels'
import { mediaUrl } from '@/features/images/media'
import { useGodAction } from '@/features/pantheon/godAction'
import { ROLE_ICONS } from '../../mind/labels'
import { MindPicker } from '../../mind/parts'
import { named } from '../../realm/labels'
import { Panel, RecordField, RefLink, Tag } from '../../realm/parts'
import {
  type ArmsInk,
  type FamilyReach,
  type CareBond,
  type FamilyTree,
  type TreePerson,
  familyKey,
  profileKey,
  useFamilyTree,
} from '../api'
import { KIN_ICON, KIN_KINDS, MARRIAGE_ENDS, SEXES } from '../labels'
import { FamilyTreeCanvas } from './FamilyTreeCanvas'
import { familyLayout } from './familyLayout'
import { CARE_LOOK, ENDED_DASH, PARTNER_LOOK, generationWord } from './looks'

const REACH_MAX = 12
const START_REACH: FamilyReach = { up: 3, down: 3 }
const CARE_KINDS: CareBond[] = ['fostered_by', 'godparent_of', 'sworn_kin']
const WORKING = 'Working on it.'

const BIND_KINDS = {
  parent_of: 'Is a parent of',
  child_of: 'Is a child of',
  spouse_of: 'Is wed to',
  betrothed_to: 'Is promised to',
  concubine_of: 'Is a concubine of',
  fostered_by: 'Is fostered by',
  sworn_kin: 'Is sworn kin of',
  godparent_of: 'Is a godparent of',
} as const
type BindKind = keyof typeof BIND_KINDS

function LineSample({ stroke, dash }: { stroke: string; dash?: string }) {
  return (
    <svg width={34} height={10} aria-hidden='true' className='shrink-0'>
      <path
        d='M 2 5 H 32'
        strokeWidth={2.5}
        strokeDasharray={dash}
        strokeLinecap='round'
        className={stroke}
      />
    </svg>
  )
}

function Stepper({
  label,
  icon,
  value,
  more,
  onChange,
  blocked,
}: {
  label: string
  icon: LucideIcon
  value: number
  more: boolean
  onChange: (value: number) => void
  blocked: string | null
}) {
  return (
    <FieldTile label={label} icon={icon} group>
      <div className='flex items-center gap-2'>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label={`Fewer ${label.toLowerCase()}`}
          disabled={blocked !== null || value <= 0}
          disabledReason={blocked ?? 'None are shown already.'}
          onClick={() => onChange(value - 1)}
        >
          <Minus />
        </Button>
        <Text className='min-w-8 text-center font-display tabular-nums'>
          {value}
        </Text>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label={`More ${label.toLowerCase()}`}
          disabled={blocked !== null || value >= REACH_MAX || !more}
          disabledReason={
            blocked ??
            (value >= REACH_MAX
              ? `The tree reaches at most ${REACH_MAX} generations each way.`
              : 'No one further is recorded.')
          }
          onClick={() => onChange(value + 1)}
        >
          <Plus />
        </Button>
        {more && (
          <Badge size='sm' variant='outline'>
            More beyond
          </Badge>
        )}
      </div>
    </FieldTile>
  )
}

function PersonDetail({
  tree,
  person,
  kin,
  houses,
  rootId,
  blocked,
  onCentre,
  onClose,
}: {
  tree: FamilyTree
  person: TreePerson
  kin: string
  houses: Map<number, { name: string; ink: ArmsInk | null; id: number }>
  rootId: number
  blocked: string | null
  onCentre: () => void
  onClose: () => void
}) {
  const [bind, setBind] = useState<BindKind>('parent_of')
  const [other, setOther] = useState<number | null>(null)
  const action = useGodAction({
    run: ({ path, body }: { path: string; body: Record<string, unknown> }) => {
      const post = api.POST as unknown as (
        route: string,
        init: { body: Record<string, unknown> }
      ) => Parameters<typeof unwrap>[0]
      return unwrap(post(path, { body }))
    },
    invalidate: [familyKey(rootId), profileKey(rootId), profileKey(person.id)],
  })
  const busy = blocked ?? (action.isPending ? WORKING : null)
  const names = new Map(tree.people.map((entry) => [entry.id, entry.name]))
  const house =
    person.house_id === null ? undefined : houses.get(person.house_id)
  const role = person.role ? ROLE_ICONS[person.role] : undefined
  const ties = tree.ties.filter(
    (tie) => tie.source_id === person.id || tie.target_id === person.id
  )
  const unions = tree.unions.filter(
    (union) => union.first_id === person.id || union.second_id === person.id
  )
  const send = () => {
    if (other === null) return
    if (bind === 'spouse_of')
      void action.mutateAsync({
        path: '/api/actions/kin:marry',
        body: { first_id: person.id, second_id: other, forced: false },
      })
    else
      void action.mutateAsync({
        path: '/api/actions/kin:bond',
        body:
          bind === 'child_of'
            ? { source_id: other, target_id: person.id, kind: 'parent_of' }
            : { source_id: person.id, target_id: other, kind: bind },
      })
  }
  return (
    <Panel
      title='Chosen in the tree'
      icon={KIN_ICON}
      tone='gold'
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Let go of this mortal'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    >
      <div className='@container/chosen flex min-w-0 flex-col gap-4'>
        <div className='flex min-w-0 items-center gap-3'>
          <Portrait
            name={person.name}
            src={person.cover ? mediaUrl(person.cover, 160) : null}
            size='lg'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <SectionTitle level={3} truncate>
              <RefLink
                node={{ id: person.id, kind: 'entity', name: person.name }}
              />
            </SectionTitle>
            {person.title && (
              <Muted variant='caption' truncate>
                {person.title}
              </Muted>
            )}
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <Badge size='sm' variant='secondary'>
                {kin}
              </Badge>
              {person.sex && <Tag spec={named(SEXES, person.sex)} />}
              {role && <Tag spec={role} />}
              <Tag
                spec={{
                  label: generationWord(person.generation),
                  icon: Layers,
                  tone: 'verdigris',
                }}
              />
              {house && (
                <Tag spec={{ label: house.name, icon: Castle, tone: 'gold' }} />
              )}
              <Tag
                spec={
                  person.living
                    ? {
                        label: `Born epoch ${person.birth_epoch}`,
                        icon: Sprout,
                        tone: 'success',
                      }
                    : {
                        label:
                          person.end_epoch === null
                            ? `Born epoch ${person.birth_epoch}, dead`
                            : `Epoch ${person.birth_epoch}–${person.end_epoch}`,
                        icon: Skull,
                        tone: 'muted',
                      }
                }
              />
            </div>
          </div>
          <Button size='sm' variant='outline' onClick={onCentre}>
            <Crosshair />
            Centre
          </Button>
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-4 @2xl/chosen:grid-cols-2'>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Their bonds in this tree</Label>
            <ul className='flex min-w-0 flex-col gap-1.5'>
              <Paged items={unions} as='li'>
                {(union) => {
                  const spouse =
                    union.first_id === person.id
                      ? union.second_id
                      : union.first_id
                  return (
                    <li
                      key={`union-${union.marriage_id}`}
                      className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-2 py-1.5'
                    >
                      <Tag
                        spec={
                          union.cause_end
                            ? MARRIAGE_ENDS[union.cause_end]
                            : { ...KIN_KINDS.spouse_of, label: 'Wed' }
                        }
                      />
                      <Tag spec={UNION_FORMS[union.form]} />
                      <Tag spec={UNION_PURPOSES[union.purpose]} />
                      <span className='min-w-0 flex-1 truncate'>
                        <RefLink
                          node={{
                            id: spouse,
                            kind: 'entity',
                            name: names.get(spouse) ?? '',
                          }}
                        />
                      </span>
                      <Muted variant='caption'>
                        {union.end_epoch === null
                          ? `since epoch ${union.start_epoch}`
                          : `epoch ${union.start_epoch}–${union.end_epoch}`}
                      </Muted>
                      {union.end_epoch === null && (
                        <Button
                          size='sm'
                          variant='outline'
                          disabled={busy !== null}
                          disabledReason={busy ?? undefined}
                          onClick={() =>
                            void action.mutateAsync({
                              path: '/api/actions/kin:end_marriage',
                              body: {
                                marriage_id: union.marriage_id,
                                cause: 'divorce',
                              },
                            })
                          }
                        >
                          End
                        </Button>
                      )}
                      <Button
                        size='icon-sm'
                        variant='ghost'
                        aria-label='Strike this marriage from the record'
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          void action.mutateAsync({
                            path: '/api/actions/kin:delete_marriage',
                            body: { marriage_id: union.marriage_id },
                          })
                        }
                      >
                        <X />
                      </Button>
                    </li>
                  )
                }}
              </Paged>
              <Paged items={ties} as='li'>
                {(tie) => {
                  const outgoing = tie.source_id === person.id
                  const otherId = outgoing ? tie.target_id : tie.source_id
                  const spec = KIN_KINDS[tie.kind]
                  return (
                    <li
                      key={`tie-${tie.bond_id}`}
                      className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-2 py-1.5'
                    >
                      <Tag
                        spec={named(KIN_KINDS, tie.kind)}
                        text={
                          spec ? (outgoing ? spec.out : spec.in) : undefined
                        }
                      />
                      <span className='min-w-0 flex-1 truncate'>
                        <RefLink
                          node={{
                            id: otherId,
                            kind: 'entity',
                            name: names.get(otherId) ?? '',
                          }}
                        />
                      </span>
                      <Muted variant='caption'>
                        {tie.past
                          ? `from epoch ${tie.epoch}, now past`
                          : `since epoch ${tie.epoch}`}
                      </Muted>
                      <Button
                        size='icon-sm'
                        variant='ghost'
                        aria-label='Undo this bond'
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          void action.mutateAsync({
                            path: '/api/actions/kin:unbond',
                            body: { bond_id: tie.bond_id },
                          })
                        }
                      >
                        <X />
                      </Button>
                    </li>
                  )
                }}
              </Paged>
            </ul>
            {unions.length + ties.length === 0 && (
              <Muted variant='caption'>
                No bonds of kin are recorded for them.
              </Muted>
            )}
          </div>
          <div className='flex min-w-0 flex-col gap-3'>
            <Label variant='overline'>Bind them to another</Label>
            <MindPicker
              label='How they are bound'
              value={bind}
              table={BIND_KINDS}
              blocked={busy}
              onPick={(value) => setBind(value as BindKind)}
            />
            <RecordField
              label='To whom'
              types={['mortal']}
              value={other}
              onChange={setOther}
              blocked={busy}
            />
            <div className='flex justify-end'>
              <Button
                size='sm'
                disabled={
                  busy !== null || other === null || other === person.id
                }
                disabledReason={
                  busy ??
                  (other === person.id
                    ? 'A mortal cannot be bound to themself.'
                    : 'Choose who to bind them to.')
                }
                onClick={send}
              >
                <Link2 />
                Bind them
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  )
}

function TreeLegend({
  tree,
  houses,
}: {
  tree: FamilyTree
  houses: Map<number, { name: string; ink: ArmsInk | null; id: number }>
}) {
  const counts = new Map<number, number>()
  for (const person of tree.people)
    if (person.house_id !== null)
      counts.set(person.house_id, (counts.get(person.house_id) ?? 0) + 1)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @3xl/tree:grid-cols-2'>
      <Panel title='Reading the tree' icon={GitFork} tone='verdigris'>
        <ul className='grid min-w-0 grid-cols-1 gap-x-4 gap-y-2 @md/tree:grid-cols-2'>
          <li className='flex min-w-0 items-center gap-2'>
            <LineSample stroke='stroke-gild' />
            <Muted variant='caption'>From parents to their children</Muted>
          </li>
          <li className='flex min-w-0 items-center gap-2'>
            <svg width={34} height={10} aria-hidden='true' className='shrink-0'>
              <path d='M 2 5 H 32' strokeWidth={6} className='stroke-gild/70' />
              <path d='M 2 5 H 32' strokeWidth={2} className='stroke-card' />
            </svg>
            <Muted variant='caption'>A marriage that holds</Muted>
          </li>
          <li className='flex min-w-0 items-center gap-2'>
            <svg width={34} height={10} aria-hidden='true' className='shrink-0'>
              <path
                d='M 2 5 H 32'
                strokeWidth={6}
                className='stroke-muted-foreground/60'
              />
              <path d='M 2 5 H 32' strokeWidth={2} className='stroke-card' />
            </svg>
            <Muted variant='caption'>A marriage that held until a death</Muted>
          </li>
          <li className='flex min-w-0 items-center gap-2'>
            <LineSample stroke='stroke-muted-foreground' dash={ENDED_DASH} />
            <Muted variant='caption'>A marriage or bond that was broken</Muted>
          </li>
          {(['concubine_of', 'betrothed_to'] as const).map((kind) => (
            <li key={kind} className='flex min-w-0 items-center gap-2'>
              <LineSample
                stroke={PARTNER_LOOK[kind].stroke}
                dash={PARTNER_LOOK[kind].dash}
              />
              <Muted variant='caption'>{PARTNER_LOOK[kind].label}</Muted>
            </li>
          ))}
          {(
            ['parent_of', 'fostered_by', 'godparent_of', 'sworn_kin'] as const
          ).map((kind) => (
            <li key={kind} className='flex min-w-0 items-center gap-2'>
              <LineSample
                stroke={CARE_LOOK[kind].stroke}
                dash={CARE_LOOK[kind].dash}
              />
              <Muted variant='caption'>{CARE_LOOK[kind].label}</Muted>
            </li>
          ))}
          <li className='flex min-w-0 items-center gap-2'>
            <svg width={34} height={14} aria-hidden='true' className='shrink-0'>
              <rect
                x={2}
                y={1}
                width={30}
                height={12}
                rx={4}
                strokeDasharray='4 3'
                className='fill-card stroke-gild/70'
              />
            </svg>
            <Muted variant='caption'>
              Kin by marriage or bond, not by blood
            </Muted>
          </li>
          <li className='flex min-w-0 items-center gap-2'>
            <svg width={34} height={14} aria-hidden='true' className='shrink-0'>
              <rect
                x={2}
                y={1}
                width={30}
                height={12}
                rx={4}
                className='fill-muted stroke-gild/55'
              />
            </svg>
            <Muted variant='caption'>† The dead, greyed</Muted>
          </li>
        </ul>
      </Panel>
      <Panel
        title='Houses in the tree'
        icon={Castle}
        tone='gold'
        count={houses.size}
      >
        {houses.size === 0 ? (
          <Muted variant='caption'>No one here belongs to a house.</Muted>
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-2 @md/tree:grid-cols-2'>
            <Paged items={[...houses.values()]} as='li'>
              {(house) => (
                <li key={house.id} className='flex min-w-0 items-center gap-2'>
                  <svg
                    width={14}
                    height={22}
                    aria-hidden='true'
                    className='shrink-0'
                  >
                    <rect
                      width={14}
                      height={22}
                      rx={3}
                      className={
                        house.ink
                          ? INK_FILLS[house.ink]
                          : 'fill-muted-foreground'
                      }
                    />
                  </svg>
                  <span className='min-w-0 flex-1 truncate'>
                    <RefLink
                      node={{ id: house.id, kind: 'entity', name: house.name }}
                    />
                  </span>
                  <Muted variant='caption'>
                    {plural(counts.get(house.id) ?? 0, 'member', 'members')}
                  </Muted>
                </li>
              )}
            </Paged>
          </ul>
        )}
      </Panel>
    </div>
  )
}

export function FamilyTreePanel({
  mortalId,
  blocked,
}: {
  mortalId: number
  blocked: string | null
}) {
  const [reach, setReach] = useState<FamilyReach>(START_REACH)
  const [care, setCare] = useState<CareBond[]>(CARE_KINDS)
  const [selected, setSelected] = useState<number | null>(null)
  const [centred, setCentred] = useState<{ id: number; turn: number } | null>(
    null
  )
  const [query, setQuery] = useState('')
  const [full, setFull] = useState(false)
  const result = useFamilyTree(
    mortalId,
    reach,
    CARE_KINDS.filter((kind) => !care.includes(kind))
  )
  const tree = result.data
  const layout = useMemo(() => (tree ? familyLayout(tree) : null), [tree])
  const houses = useMemo(
    () =>
      new Map(
        (tree?.houses ?? []).map((house) => [
          house.house.id,
          { id: house.house.id, name: house.house.name, ink: house.ink },
        ])
      ),
    [tree]
  )
  const inks = useMemo(
    () => new Map([...houses.values()].map((house) => [house.id, house.ink])),
    [houses]
  )
  if (result.isError)
    return (
      <EmptyState
        icon={KIN_ICON}
        title='The tree could not be read'
        description={result.error.message}
      />
    )
  if (!tree || !layout) return <LoadingBlock label='Tracing the bloodlines' />
  const people = tree.people
  const matches =
    query.trim().length === 0
      ? []
      : people.filter((person) =>
          person.name.toLowerCase().includes(query.trim().toLowerCase())
        )
  const chosen = tree.people.find((person) => person.id === selected)
  const pick = (id: number) => {
    setSelected((current) => (current === id ? null : id))
  }
  const centre = (id: number) => {
    setSelected(id)
    setCentred((current) => ({ id, turn: (current?.turn ?? 0) + 1 }))
  }
  const canvas = (className: string, wheel: 'free' | 'held') => (
    <FamilyTreeCanvas
      tree={tree}
      layout={layout}
      inks={inks}
      selected={selected}
      centred={centred}
      onSelect={pick}
      wheel={wheel}
      className={className}
    />
  )
  return (
    <div className='@container/tree flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/tree:grid-cols-3 @4xl/tree:grid-cols-6'>
        <MiniStat
          icon={Users}
          label='Kin in the tree'
          value={people.length}
          tone='gold'
        />
        <MiniStat
          icon={Layers}
          label='Generations'
          value={layout.rows.length}
          tone='verdigris'
        />
        <MiniStat
          icon={Sprout}
          label='Living'
          value={people.filter((person) => person.living).length}
          tone='success'
        />
        <MiniStat
          icon={Skull}
          label='Dead'
          value={people.filter((person) => !person.living).length}
          tone='muted'
        />
        <MiniStat
          icon={HeartHandshake}
          label='Marriages'
          value={tree.unions.length}
          tone='danger'
        />
        <MiniStat
          icon={Castle}
          label='Houses'
          value={houses.size}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-stretch gap-2'>
        <Stepper
          label='Ancestors'
          icon={ChevronsUp}
          value={tree.up}
          more={tree.deeper_up}
          blocked={result.isFetching ? WORKING : null}
          onChange={(up) => setReach((current) => ({ ...current, up }))}
        />
        <Stepper
          label='Descendants'
          icon={ChevronsDown}
          value={tree.down}
          more={tree.deeper_down}
          blocked={result.isFetching ? WORKING : null}
          onChange={(down) => setReach((current) => ({ ...current, down }))}
        />
        <FieldTile label='Bonds of care' icon={HeartHandshake} group>
          <ToggleGroup
            type='multiple'
            variant='outline'
            size='sm'
            className='flex-wrap justify-start'
            value={care}
            onValueChange={(next) => setCare(next as CareBond[])}
            aria-label='Bonds of care to show'
          >
            {CARE_KINDS.map((kind) => {
              const spec = KIN_KINDS[kind]
              return (
                <ToggleGroupItem
                  key={kind}
                  value={kind}
                  aria-label={spec.label}
                >
                  <spec.icon />
                  {spec.label}
                </ToggleGroupItem>
              )
            })}
          </ToggleGroup>
        </FieldTile>
        <FieldTile
          label='Find in the tree'
          icon={Search}
          group
          className='flex-1'
        >
          <Input
            size='sm'
            leadingIcon={Search}
            value={query}
            placeholder='A name'
            aria-label='Find a mortal in the tree'
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && matches[0]) centre(matches[0].id)
            }}
          />
        </FieldTile>
        <Button
          size='sm'
          variant='outline'
          className='self-end'
          onClick={() => setFull(true)}
        >
          <Maximize2 />
          Full view
        </Button>
      </div>
      {matches.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Muted variant='caption'>
            {plural(matches.length, 'match', 'matches')}
          </Muted>
          <Paged items={matches}>
            {(person) => (
              <Button
                key={person.id}
                size='sm'
                variant='outline'
                onClick={() => centre(person.id)}
              >
                <Crosshair />
                {person.name}
              </Button>
            )}
          </Paged>
        </div>
      )}
      {people.length <= 1 && (
        <Muted variant='caption'>
          No kin are recorded for this mortal yet. Choose them in the tree to
          bind them to a parent, a child, a spouse or sworn kin.
        </Muted>
      )}
      {canvas('h-scene lg:h-scene-lg', 'held')}
      <Muted variant='caption'>
        Drag to move. Hold Ctrl or ⌘ while scrolling, or pinch, to zoom. Choose
        anyone to trace their line and bind them to others.
      </Muted>
      {chosen && (
        <PersonDetail
          tree={tree}
          person={chosen}
          kin={chosen.relation}
          houses={houses}
          rootId={mortalId}
          blocked={blocked}
          onCentre={() => centre(chosen.id)}
          onClose={() => setSelected(null)}
        />
      )}
      <TreeLegend tree={tree} houses={houses} />
      <Dialog open={full} onOpenChange={setFull}>
        <DialogContent className='flex h-entry-tall w-entry max-w-none flex-col gap-0 p-0 sm:max-w-none'>
          <DialogHeader className='border-b border-gild/40 p-4'>
            <DialogTitle>{`Family tree of ${tree.people.find((person) => person.id === tree.root)?.name ?? ''}`}</DialogTitle>
            <DialogDescription>
              {`${plural(people.length, 'kin', 'kin')} across ${plural(layout.rows.length, 'generation', 'generations')}. Drag to move, scroll to zoom, choose anyone to trace their line.`}
            </DialogDescription>
          </DialogHeader>
          {canvas('min-h-0 flex-1', 'free')}
        </DialogContent>
      </Dialog>
    </div>
  )
}
