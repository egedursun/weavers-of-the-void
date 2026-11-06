import { useState } from 'react'
import { Eraser, RotateCcw, ShieldAlert, Sparkles, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { named } from '../mind/labels'
import { ControlPanel, ItemRow, MindCard } from '../mind/parts'
import {
  type MethodKind,
  type Works,
  type WorksEnergy,
  type WorksMethod,
  type WorksOption,
  type WorksPollution,
  type WorksStock,
  useWorks,
} from '../works/api'
import {
  ENERGY,
  LAND_ICON,
  POLLUTANTS,
  POWER_ICON,
  PROCESSES,
  STORES_ICON,
  TIER_ICON,
  TIER_TONE,
  TOOL_ICON,
  WORKS_ICON,
} from '../works/labels'

const SPAN = 100
const WORKING = 'Working on it.'
const PURIFY = 30
const POLLUTION = ['air', 'water', 'soil'] as const

type Props = { view: Works; blocked: string | null; hold: boolean }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function Meter({
  label,
  value,
  max,
  tone,
  note,
}: {
  label: string
  value: number
  max: number
  tone: 'success' | 'warning' | 'destructive' | 'info'
  note?: string
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted variant='caption'>{label}</Muted>
        <Text variant='caption' weight='semibold'>
          {note ?? value}
        </Text>
      </div>
      <Progress
        value={max > 0 ? Math.min(SPAN, (value * SPAN) / max) : 0}
        size='sm'
        tone={tone}
        aria-label={`${label} ${note ?? value}`}
      />
    </div>
  )
}

function Chip({ children }: { children: string }) {
  return <Badge variant='outline'>{children}</Badge>
}

function optionChips(option: WorksOption): string[] {
  const fouls = [
    option.air ? `air ${option.air > 0 ? '+' : ''}${option.air}` : '',
    option.water ? `water ${option.water > 0 ? '+' : ''}${option.water}` : '',
    option.soil ? `soil ${option.soil > 0 ? '+' : ''}${option.soil}` : '',
  ].filter(Boolean)
  return [
    `${named(ENERGY, option.energy).label} ${option.energy_need}`,
    `output ${option.output_pct}%`,
    ...(option.quality_bonus ? [`quality +${option.quality_bonus}`] : []),
    ...(option.tool_wear ? [`wear ${option.tool_wear}`] : ['no tool wear']),
    ...(fouls.length ? fouls : ['clean']),
  ]
}

function OptionRow({
  option,
  current,
  busy,
  onPick,
}: {
  option: WorksOption
  current: boolean
  busy: string | null
  onPick: (method: MethodKind) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2 px-3 py-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Text variant='caption' weight='semibold' truncate className='flex-1'>
          {option.label}
        </Text>
        {current ? (
          <Badge>In use</Badge>
        ) : (
          <Button
            size='sm'
            variant={option.blocked ? 'outline' : 'default'}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => onPick(option.method)}
          >
            {option.blocked ? <ShieldAlert /> : <Sparkles />}
            {option.blocked ? 'Impose it' : 'Take it up'}
          </Button>
        )}
      </div>
      <Muted variant='caption'>
        {option.blocked
          ? `${option.summary}. Out of reach on its own: ${option.blocked}.`
          : `${option.summary}.`}
      </Muted>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {optionChips(option).map((chip) => (
          <Chip key={chip}>{chip}</Chip>
        ))}
      </div>
    </div>
  )
}

function MethodRow({
  row,
  view,
  blocked,
  hold,
}: {
  row: WorksMethod
  view: Works
  blocked: string | null
  hold: boolean
}) {
  const spec = named(PROCESSES, row.process)
  const pick = useGodAction({
    run: (method: MethodKind) =>
      unwrap(
        api.POST('/api/actions/method:set', {
          body: { community_id: view.node_id, method, hold },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/method:remove', {
          body: { community_id: view.node_id, process: row.process },
        })
      ),
  })
  const busy = why(blocked, pick.isPending, release.isPending)
  const open = row.options.filter((option) => option.blocked === null).length
  return (
    <ItemRow
      icon={spec.icon}
      tone={spec.tone}
      title={`${row.process_label}: ${row.label}`}
      meta={
        row.chosen
          ? `${row.summary} · since epoch ${row.adopted_epoch ?? 0}${row.displaced ? ` · ${row.displaced} hands put out of work` : ''}`
          : `${row.summary} · the oldest way, until the place chooses`
      }
      badges={
        <>
          {row.held && <Badge variant='secondary'>Held</Badge>}
          <Badge variant='outline'>{`${open} of ${row.options.length} open`}</Badge>
        </>
      }
      actions={
        row.chosen ? (
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Let the place choose again'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => release.mutate()}
          >
            <RotateCcw />
          </Button>
        ) : undefined
      }
      editLabel='the ways this work can be done'
      editor={
        <div className='flex min-w-0 flex-col divide-y rounded-md border bg-background'>
          {row.options.map((option) => (
            <OptionRow
              key={option.method}
              option={option}
              current={option.method === row.method}
              busy={busy}
              onPick={(method) => pick.mutate(method)}
            />
          ))}
        </div>
      }
    />
  )
}

function MethodsCard({ view, blocked, hold }: Props) {
  const changed = view.methods.filter((row) => row.chosen).length
  return (
    <MindCard
      title='Ways of working'
      icon={WORKS_ICON}
      hint={`Each work is done one way at a time; ${changed} of ${view.methods.length} are chosen. Better ways need techniques, knowledge and power, and those that need fewer hands put some out of work.`}
      wide
    >
      <Paged items={view.methods} initial={5} noun={['work', 'works']}>
        {(row) => (
          <MethodRow
            key={row.process}
            row={row}
            view={view}
            blocked={blocked}
            hold={hold}
          />
        )}
      </Paged>
    </MindCard>
  )
}

function energyTone(row: WorksEnergy): 'success' | 'warning' | 'destructive' {
  if (row.short > 0) return 'destructive'
  return row.spent >= row.supply && row.supply > 0 ? 'warning' : 'success'
}

function PowerCard({ view, blocked, hold }: Props) {
  const wipe = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/industry:remove', {
          body: { community_id: view.node_id },
        })
      ),
  })
  const busy = why(blocked, wipe.isPending)
  const top = Math.max(1, ...view.energy.map((row) => row.supply))
  return (
    <MindCard
      title='Power'
      icon={POWER_ICON}
      hint='What the place can draw on each epoch and what its works used. Rivers make mill towns; ley lines and shrines lend stranger power.'
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {view.energy.map((row) => (
          <Meter
            key={row.kind}
            label={`${row.label} · ${row.source}${row.held ? ' · held' : ''}`}
            value={row.supply}
            max={top}
            tone={energyTone(row)}
            note={`${row.spent} of ${row.supply}${row.short ? `, ${row.short} short` : ''}`}
          />
        ))}
      </div>
      <AdjustStats
        id={`power-${view.node_id}`}
        inline
        groups={[
          {
            title: 'Power each epoch',
            fields: view.energy.map((row) => ({
              key: row.kind,
              label: row.label,
              value: row.supply,
              min: 0,
            })),
          },
        ]}
        run={({ key, value }) =>
          unwrap(
            api.POST('/api/actions/industry:set', {
              body: { community_id: view.node_id, [key]: value, hold },
            })
          )
        }
      />
      {view.stores !== null && (
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => wipe.mutate()}
        >
          <Eraser />
          Reckon power and stores anew
        </Button>
      )}
    </MindCard>
  )
}

function StockRow({
  lot,
  view,
  hold,
}: {
  lot: WorksStock
  view: Works
  hold: boolean
}) {
  const tone = TIER_TONE[lot.tier] ?? 'muted'
  return (
    <ItemRow
      icon={TIER_ICON}
      tone={tone}
      title={`${lot.label}${lot.material ? ` of ${lot.material.replaceAll('_', ' ')}` : ''}`}
      meta={`${lot.quantity} held · quality ${lot.quality}${lot.perishable ? ` · ${lot.preserved} preserved` : ''}`}
      badges={
        <>
          <Badge variant={tone === 'danger' ? 'destructive' : 'outline'}>
            {lot.tier_label}
          </Badge>
          {lot.perishable && <Badge variant='secondary'>Perishable</Badge>}
          {lot.held && <Badge variant='secondary'>Held</Badge>}
        </>
      }
      editLabel='this store'
      editor={
        <AdjustStats
          id={`works-lot-${lot.id}`}
          inline
          groups={[
            {
              title: 'This store',
              fields: [
                {
                  key: 'quantity',
                  label: 'Quantity',
                  value: lot.quantity,
                  min: 0,
                },
                {
                  key: 'quality',
                  label: 'Quality',
                  value: lot.quality,
                  min: 0,
                  max: SPAN,
                },
                ...(lot.perishable
                  ? [
                      {
                        key: 'preserved',
                        label: 'Preserved',
                        value: lot.preserved,
                        min: 0,
                        max: lot.quantity,
                      },
                    ]
                  : []),
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/stock:set', {
                body: {
                  community_id: view.node_id,
                  commodity: lot.commodity,
                  material: lot.material,
                  world_material_id: lot.world_material_id,
                  quantity: key === 'quantity' ? value : lot.quantity,
                  quality: key === 'quality' ? value : lot.quality,
                  preserved: key === 'preserved' ? value : lot.preserved,
                  hold,
                },
              })
            )
          }
        />
      }
    />
  )
}

function StoresCard({ view, hold }: Props) {
  const stores = view.stores
  return (
    <MindCard
      title='Stores, wear and fare'
      icon={STORES_ICON}
      hint='Fish, bread, grain and remedies spoil unless preserved; vermin gnaw the grain; work wears out tools; the quality of meals lifts or sours the people.'
      wide
    >
      {stores === null ? (
        <Muted variant='caption'>
          Nothing reckoned yet; the stores are counted at the next epoch.
        </Muted>
      ) : (
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
          <KpiTile
            label='Meals'
            value={stores.meal_tier_label}
            icon={TIER_ICON}
            tone={TIER_TONE[stores.meal_tier] ?? 'muted'}
            meter={{
              value: stores.meal_quality,
              max: SPAN,
              label: 'Meal quality',
            }}
          />
          <KpiTile
            label='Spoiled'
            value={stores.spoiled}
            icon={STORES_ICON}
            tone='danger'
          />
          <KpiTile
            label='Preserved'
            value={stores.preserved}
            icon={STORES_ICON}
            tone='info'
          />
          <KpiTile
            label='Tools worn'
            value={stores.tools_worn}
            icon={TOOL_ICON}
            tone='warning'
          />
        </div>
      )}
      {stores !== null && (
        <AdjustStats
          id={`stores-${view.node_id}`}
          inline
          groups={[
            {
              title: 'This epoch',
              fields: [
                {
                  key: 'meal_quality',
                  label: 'Meal quality',
                  value: stores.meal_quality,
                  min: 0,
                  max: SPAN,
                },
                {
                  key: 'spoiled',
                  label: 'Spoiled',
                  value: stores.spoiled,
                  min: 0,
                },
                {
                  key: 'preserved',
                  label: 'Preserved',
                  value: stores.preserved,
                  min: 0,
                },
                {
                  key: 'tools_worn',
                  label: 'Tools worn',
                  value: stores.tools_worn,
                  min: 0,
                },
                {
                  key: 'heat_need',
                  label: 'Heat needed to live',
                  value: stores.heat_need,
                  min: 0,
                },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/industry:set', {
                body: { community_id: view.node_id, [key]: value, hold },
              })
            )
          }
        />
      )}
      {view.stocks.length === 0 ? (
        <Muted variant='caption'>The stores are empty.</Muted>
      ) : (
        <Paged items={view.stocks} initial={4} noun={['store', 'stores']}>
          {(lot) => <StockRow key={lot.id} lot={lot} view={view} hold={hold} />}
        </Paged>
      )}
    </MindCard>
  )
}

function pollutionTone(value: number): 'success' | 'warning' | 'destructive' {
  if (value >= 60) return 'destructive'
  return value >= 30 ? 'warning' : 'success'
}

function LandRow({
  row,
  blocked,
  hold,
}: {
  row: WorksPollution
  blocked: string | null
  hold: boolean
}) {
  const id = row.region?.id ?? 0
  const purify = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/pollution:purify', {
          body: { region_id: id, amount: PURIFY },
        })
      ),
  })
  const wipe = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/pollution:remove', { body: { region_id: id } })
      ),
  })
  const busy = why(blocked, purify.isPending, wipe.isPending)
  const worst = Math.max(row.air, row.water, row.soil)
  return (
    <ItemRow
      icon={LAND_ICON}
      tone={worst >= 60 ? 'danger' : worst >= 30 ? 'warning' : 'success'}
      title={
        row.region ? (
          <EntityLink kind='entity' id={String(row.region.id)}>
            {row.region.name}
          </EntityLink>
        ) : (
          'Unknown land'
        )
      }
      meta={
        row.polluters.length
          ? `Fouled most by ${row.polluters
              .slice(0, 3)
              .map((item) => item.community?.name ?? 'someone')
              .join(', ')}`
          : worst > 0
            ? 'Fouled by crowds and old works'
            : 'Clean'
      }
      badges={
        <>
          {row.blight > 0 && (
            <Badge variant='destructive'>{`Blight ${row.blight}`}</Badge>
          )}
          {row.held.length > 0 && <Badge variant='secondary'>Held</Badge>}
        </>
      }
      actions={
        <>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Cleanse the land'
            disabled={busy !== null || worst === 0}
            disabledReason={
              busy ?? (worst === 0 ? 'The land is already clean.' : undefined)
            }
            onClick={() => purify.mutate()}
          >
            <Sparkles />
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Wipe the record of its pollution'
            disabled={busy !== null || row.epoch === null}
            disabledReason={
              busy ??
              (row.epoch === null
                ? 'No pollution has been recorded here.'
                : undefined)
            }
            onClick={() => wipe.mutate()}
          >
            <X />
          </Button>
        </>
      }
      editLabel='how fouled the land is'
      editor={
        <AdjustStats
          id={`pollution-${id}`}
          inline
          groups={[
            {
              title: 'Pollution',
              fields: POLLUTION.map((key) => ({
                key,
                label: named(POLLUTANTS, key).label,
                value: row[key],
                min: 0,
                max: SPAN,
              })),
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/pollution:set', {
                body: { region_id: id, [key]: value, hold },
              })
            )
          }
        />
      }
    >
      <div className='grid min-w-0 grid-cols-3 gap-3'>
        {POLLUTION.map((key) => (
          <Meter
            key={key}
            label={named(POLLUTANTS, key).label}
            value={row[key]}
            max={SPAN}
            tone={pollutionTone(row[key])}
          />
        ))}
      </div>
    </ItemRow>
  )
}

function LandCard({ view, blocked, hold }: Props) {
  return (
    <MindCard
      title='Air, water and soil'
      icon={LAND_ICON}
      hint='Works and crowds foul the land: fouled air and water breed sickness, fouled water thins the catch, fouled soil yields less and at the worst blights. Forests, sanitation and rites cleanse it.'
      wide
    >
      {view.pollution.length === 0 ? (
        <Muted variant='caption'>
          No land is fouled here, or this one stands on no land.
        </Muted>
      ) : (
        <Paged items={view.pollution} initial={3} noun={['land', 'lands']}>
          {(row) => (
            <LandRow
              key={row.region?.id ?? 0}
              row={row}
              blocked={blocked}
              hold={hold}
            />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

function Headline({ view }: { view: Works }) {
  const supply = view.energy.reduce((sum, row) => sum + row.supply, 0)
  const short = view.energy.reduce((sum, row) => sum + row.short, 0)
  const worst = Math.max(
    0,
    ...view.pollution.map((row) => Math.max(row.air, row.water, row.soil))
  )
  return (
    <div className='grid min-w-0 grid-cols-2 gap-3 @3xl/mind:grid-cols-4'>
      <KpiTile
        label='Works chosen'
        value={`${view.methods.filter((row) => row.chosen).length} of ${view.methods.length}`}
        icon={WORKS_ICON}
        tone='gold'
      />
      <KpiTile
        label='Power'
        value={supply}
        icon={POWER_ICON}
        tone='verdigris'
      />
      <KpiTile
        label='Power short'
        value={short}
        icon={POWER_ICON}
        tone={short > 0 ? 'danger' : 'success'}
      />
      <KpiTile
        label='Worst pollution'
        value={worst}
        icon={LAND_ICON}
        tone={worst >= 60 ? 'danger' : worst >= 30 ? 'warning' : 'success'}
        meter={{ value: worst, max: SPAN, label: 'Worst pollution' }}
      />
    </div>
  )
}

export function WorksSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useWorks(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section id='section-works' title='Works and land' icon={WORKS_ICON}>
        <EmptyState
          icon={WORKS_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const blocked = reason()
  return (
    <Section
      id='section-works'
      title='Works and land'
      description='How a community works, the power it draws, its stores and the land it fouls. Ways of working, power and stores belong to settlements, peoples and other communities; every other thing sees the land it stands on, worlds and stars every land on them, and gods, who stand on no land, keep none.'
      icon={WORKS_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        {view.community && <Headline view={view} />}
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          {view.community && (
            <MethodsCard view={view} blocked={blocked} hold={hold} />
          )}
          {view.community && (
            <PowerCard view={view} blocked={blocked} hold={hold} />
          )}
          {view.community && (
            <StoresCard view={view} blocked={blocked} hold={hold} />
          )}
          <LandCard view={view} blocked={blocked} hold={hold} />
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Methods, power, stores and pollution you set are held against the world while the switch is on; a held method is never changed by the place. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
