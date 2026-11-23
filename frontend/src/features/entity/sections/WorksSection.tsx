import { useState } from 'react'
import { Eraser, RotateCcw, ShieldAlert, Sparkles, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
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
import { MATERIAL_LABEL, type Named } from '@/features/entity/economy/labels'
import { ChoiceSelect } from '@/features/entity/economy/parts'
import { useKinds } from '@/features/kinds/api'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { named } from '../mind/labels'
import {
  ControlPanel,
  FormBar,
  ItemRow,
  MindCard,
  NodePicker,
} from '../mind/parts'
import {
  type MethodKind,
  type Works,
  type WorksEnergy,
  type WorksMethod,
  type WorksOption,
  type WorksPollution,
  type WorksLedger,
  type WorksSite,
  type WorksStock,
  useWorks,
} from '../works/api'
import {
  ENERGY,
  LAND_ICON,
  LEDGER_ICON,
  LIGHT_ICON,
  OWNER_ICON,
  POLLUTANTS,
  POWER_ICON,
  PROCESSES,
  SHOCK_ICON,
  STORES_ICON,
  TIER_ICON,
  TIER_TONE,
  TOOL_ICON,
  WORKS_ICON,
} from '../works/labels'

const SPAN = 100
const WORKING = 'Working on it.'
const PURIFY = 30
const POLLUTION = [
  'air',
  'water',
  'soil',
  'radiation',
  'noise',
  'light',
] as const

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
    ...(option.labour_pct !== 100
      ? [`${option.labour_pct}% of the hands`]
      : []),
    ...option.inputs,
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
  const kinds = useKinds('production_method', null)
  const authored: Record<string, Named> = {
    '0': { label: 'The way as it is known', icon: spec.icon, tone: 'muted' },
    ...Object.fromEntries(
      (kinds.data ?? [])
        .filter((kind) => !kind.retired && kind.category === row.process)
        .map((kind) => [
          String(kind.id),
          { label: kind.name, icon: spec.icon, tone: 'gold' as const },
        ])
    ),
  }
  const pick = useGodAction({
    run: ({ method, kind }: { method: MethodKind; kind: number | null }) =>
      unwrap(
        api.POST('/api/actions/method:set', {
          body: {
            community_id: view.node_id,
            method,
            method_kind_id: kind,
            hold,
          },
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
          ? `${row.summary} · since epoch ${row.adopted_epoch ?? 0}${row.displaced ? ` · ${plural(row.displaced, 'hand', 'hands')} put out of work` : ''}`
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
        <div className='flex min-w-0 flex-col divide-y rounded-md border surface-sheen border-gild/60 bg-card'>
          {row.options.map((option) => (
            <OptionRow
              key={option.method}
              option={option}
              current={option.method === row.method}
              busy={busy}
              onPick={(method) =>
                pick.mutate({ method, kind: row.method_kind_id ?? null })
              }
            />
          ))}
          <div className='p-3'>
            <ChoiceSelect
              label='Worked in the way of'
              value={String(row.method_kind_id ?? 0)}
              table={authored}
              blocked={
                busy ??
                (Object.keys(authored).length > 1
                  ? null
                  : 'No way of this work has been made in the world yet')
              }
              onPick={(value) =>
                pick.mutate({
                  method: row.method,
                  kind: value === '0' ? null : Number(value),
                })
              }
            />
          </div>
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
      hint={`Each work is done one way at a time; ${plural(view.methods.length, 'way', 'ways')} in all, ${changed} in use. Better ways need techniques, knowledge and power, and those that need fewer hands put some out of work.`}
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
      <ItemRow
        icon={POWER_ICON}
        tone='verdigris'
        title='Set the power by hand'
        meta='Every source can be set and held against the world'
        editLabel='the power each epoch'
        editor={
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
      title={`${lot.label}${lot.material ? ` of ${MATERIAL_LABEL[lot.material].toLowerCase()}` : ''}`}
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
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-3'>
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
          <KpiTile
            label='Drink'
            value={stores.drink}
            icon={STORES_ICON}
            tone='gold'
            meter={{ value: stores.drink, max: SPAN, label: 'Drink' }}
          />
          <KpiTile
            label='Evenings lit'
            value={stores.light}
            icon={LIGHT_ICON}
            tone='gold'
            meter={{ value: stores.light, max: SPAN, label: 'Evenings lit' }}
          />
        </div>
      )}
      {stores !== null && (
        <ItemRow
          icon={STORES_ICON}
          tone='info'
          title='Set the stores by hand'
          meta='Meals, drink, light, spoilage, preserving, tool wear and the heat needed to live'
          editLabel='the figures of this epoch'
          editor={
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
                    {
                      key: 'drink',
                      label: 'Drink',
                      value: stores.drink,
                      min: 0,
                      max: SPAN,
                    },
                    {
                      key: 'light',
                      label: 'Evenings lit',
                      value: stores.light,
                      min: 0,
                      max: SPAN,
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
      title='Air, water, soil, rays, noise and light'
      icon={LAND_ICON}
      hint='Works and crowds foul the land: fouled air and water breed sickness, fouled water thins the catch, fouled soil yields less and at the worst blights; radiation sickens and poisons the ground, noise wears on minds, and light hides the faint sky and drives off night creatures. Forests, sanitation and rites cleanse it.'
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

const ANYONE = [
  'mortal',
  'house',
  'polity',
  'settlement',
  'people',
  'faction',
  'cult',
]

function SiteRow({
  site,
  view,
  blocked,
  hold,
  owned,
}: {
  site: WorksSite
  view: Works
  blocked: string | null
  hold: boolean
  owned: boolean
}) {
  const [owner, setOwner] = useState<number | null>(site.owner?.id ?? null)
  const give = useGodAction({
    run: (to: number | null) =>
      unwrap(
        api.POST('/api/actions/workshop:owner', {
          body: {
            community_id: site.community?.id ?? view.node_id,
            kind: site.kind ?? 'market',
            owner_id: to,
            hold,
          },
        })
      ),
  })
  const busy = why(blocked, give.isPending)
  const profit = site.last_profit
  return (
    <ItemRow
      icon={site.kind ? OWNER_ICON : LAND_ICON}
      tone={
        profit === null || profit === undefined
          ? 'muted'
          : profit >= 0
            ? 'success'
            : 'danger'
      }
      title={
        owned && site.community ? (
          <>
            {`${site.label} of `}
            <EntityLink kind='entity' id={String(site.community.id)}>
              {site.community.name}
            </EntityLink>
          </>
        ) : site.resource ? (
          <EntityLink kind='entity' id={String(site.resource.id)}>
            {site.resource.name}
          </EntityLink>
        ) : (
          site.label
        )
      }
      meta={`${site.kind ? `level ${site.level} · ` : ''}${site.owner ? `owned by ${site.owner.name}` : `${site.owner_class}, not yet given`}`}
      badges={
        <>
          {profit !== null && profit !== undefined && (
            <Badge variant={profit >= 0 ? 'outline' : 'destructive'}>
              {`${profit >= 0 ? 'Profit' : 'Loss'} ${Math.abs(profit)}`}
            </Badge>
          )}
          {site.held && <Badge variant='secondary'>Held</Badge>}
        </>
      }
      actions={
        site.kind && site.owner ? (
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Take the workshop from its owner'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => give.mutate(null)}
          >
            <X />
          </Button>
        ) : undefined
      }
      editLabel={site.kind ? 'who owns it' : undefined}
      editor={
        site.kind ? (
          <FormBar
            action={
              <Button
                size='sm'
                disabled={busy !== null || owner === null}
                disabledReason={
                  busy ?? (owner === null ? 'Pick an owner.' : undefined)
                }
                onClick={() => give.mutate(owner)}
              >
                <OWNER_ICON />
                Give it
              </Button>
            }
          >
            <NodePicker
              label='Owner'
              types={ANYONE}
              value={owner}
              onChange={setOwner}
              blocked={busy}
            />
          </FormBar>
        ) : undefined
      }
    />
  )
}

function SitesCard({ view, blocked, hold }: Props) {
  return (
    <MindCard
      title='Works and their owners'
      icon={OWNER_ICON}
      hint='Associations, merchants, cults, the realm, landed houses or the community own each workshop and take its profit; you may hand any of them to anyone.'
      wide
    >
      {view.sites.length === 0 ? (
        <Muted variant='caption'>No workshops stand here yet.</Muted>
      ) : (
        <Paged items={view.sites} initial={4} noun={['workshop', 'workshops']}>
          {(site) => (
            <SiteRow
              key={site.workshop_id ?? site.resource?.id ?? 0}
              site={site}
              view={view}
              blocked={blocked}
              hold={hold}
              owned={false}
            />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

function HoldingsCard({ view, blocked, hold }: Props) {
  const earned = view.holdings.reduce(
    (sum, site) => sum + (site.last_profit ?? 0),
    0
  )
  return (
    <MindCard
      title='Holdings'
      icon={LEDGER_ICON}
      hint={`The workshops and resources this one owns${view.holdings.length ? `, earning ${earned} at last count` : ''}.`}
      wide
    >
      {view.holdings.length === 0 ? (
        <Muted variant='caption'>
          Owns no works. Give it a workshop from the place where it stands, or a
          resource from that resource’s page.
        </Muted>
      ) : (
        <Paged items={view.holdings} initial={4} noun={['holding', 'holdings']}>
          {(site) => (
            <SiteRow
              key={`${site.workshop_id ?? 'r'}-${site.resource?.id ?? 0}`}
              site={site}
              view={view}
              blocked={blocked}
              hold={hold}
              owned
            />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

function LedgerRow({
  row,
  blocked,
}: {
  row: WorksLedger
  blocked: string | null
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/site_profit:remove', {
          body: { profit_id: row.id },
        })
      ),
  })
  const busy = why(blocked, strike.isPending)
  return (
    <ItemRow
      icon={LEDGER_ICON}
      tone={row.profit >= 0 ? 'success' : 'danger'}
      title={`${row.site} · epoch ${row.epoch}`}
      meta={`sold ${row.revenue} · inputs ${row.inputs} · wages ${row.wages} · upkeep ${row.upkeep} · taxes ${row.taxes} · invested ${row.invested}${row.owner ? ` · to ${row.owner.name}` : ''}`}
      badges={
        <>
          <Badge variant={row.profit >= 0 ? 'outline' : 'destructive'}>
            {`${row.profit >= 0 ? 'Profit' : 'Loss'} ${Math.abs(row.profit)}`}
          </Badge>
          {row.held.length > 0 && <Badge variant='secondary'>Rewritten</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Strike the entry'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel='the figures'
      editor={
        <AdjustStats
          id={`ledger-${row.id}`}
          inline
          groups={[
            {
              title: 'Figures',
              fields: [
                { key: 'revenue', label: 'Sold', value: row.revenue, min: 0 },
                { key: 'inputs', label: 'Inputs', value: row.inputs, min: 0 },
                { key: 'wages', label: 'Wages', value: row.wages, min: 0 },
                { key: 'upkeep', label: 'Upkeep', value: row.upkeep, min: 0 },
                { key: 'taxes', label: 'Taxes', value: row.taxes, min: 0 },
                {
                  key: 'invested',
                  label: 'Invested',
                  value: row.invested,
                  min: 0,
                },
                {
                  key: 'profit',
                  label: 'Profit',
                  value: row.profit,
                  min: -100000,
                },
              ],
            },
          ]}
          run={({ key, value }) =>
            unwrap(
              api.POST('/api/actions/site_profit:edit', {
                body: { profit_id: row.id, [key]: value },
              })
            )
          }
        />
      }
    />
  )
}

function LedgerCard({ view, blocked }: Props) {
  return (
    <MindCard
      title='Ledger of profits'
      icon={LEDGER_ICON}
      hint='What each site sold, what it spent on inputs, wages, upkeep and taxes, and what its owner kept or lost.'
      wide
    >
      {view.ledger.length === 0 ? (
        <Muted variant='caption'>No profits or losses recorded yet.</Muted>
      ) : (
        <Paged items={view.ledger} initial={4} noun={['entry', 'entries']}>
          {(row) => <LedgerRow key={row.id} row={row} blocked={blocked} />}
        </Paged>
      )}
    </MindCard>
  )
}

function ShocksCard({ view }: Props) {
  return (
    <MindCard
      title='Bottlenecks'
      icon={SHOCK_ICON}
      hint='Works that stood idle at the last count for want of an input; a shortage here travels down every chain that needs it.'
    >
      {view.bottlenecks.length === 0 ? (
        <Muted variant='caption'>Nothing stood idle for want of inputs.</Muted>
      ) : (
        <Paged
          items={view.bottlenecks}
          initial={4}
          noun={['bottleneck', 'bottlenecks']}
        >
          {(row) => (
            <ItemRow
              key={`${row.step}-${row.missing}`}
              icon={SHOCK_ICON}
              tone='warning'
              title={row.step}
              meta={`${row.workshop} · short of ${row.missing.toLowerCase()} · epoch ${row.epoch}`}
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
            <ShocksCard view={view} blocked={blocked} hold={hold} />
          )}
          {view.community && (
            <StoresCard view={view} blocked={blocked} hold={hold} />
          )}
          {view.community && (
            <SitesCard view={view} blocked={blocked} hold={hold} />
          )}
          <LedgerCard view={view} blocked={blocked} hold={hold} />
          <HoldingsCard view={view} blocked={blocked} hold={hold} />
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
