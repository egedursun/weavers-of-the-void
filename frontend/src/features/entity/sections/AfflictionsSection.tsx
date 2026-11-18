import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronsDown,
  ChevronsUp,
  Hourglass,
  Lock,
  Moon,
  Pencil,
  Plus,
  ShieldCheck,
  Sparkles,
  Trash2,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  EmptyState,
  EntityLink,
  Medallion,
  Paged,
  Section,
  StatBar,
  FieldTile,
} from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { RowAction } from '../actions/RowAction'
import { loreKeys } from '../api/keys'
import {
  CURES,
  PACKAGE_LOOKS,
  STAT_LABELS,
  TRANSMISSIONS,
  VISIBILITY,
} from '../body/afflictionLabels'
import { CONDITIONS, FUNCTIONS, named, plain } from '../body/labels'

type Affliction = components['schemas']['BearerAfflictionView']
type Package = components['schemas']['PackageView']
type PackageKind = components['schemas']['PackageKind']
type Transmission = components['schemas']['Transmission']

const WORKING = 'Working on it.'

function afflictionsKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'afflictions'] as const
}

function usePackages() {
  return useQuery({
    queryKey: ['effect-packages'],
    queryFn: () => unwrap(api.GET('/api/effect-packages')),
    staleTime: Infinity,
  })
}

function linkKind(value: string | null): DrawerKind | null {
  return value === 'entity' ||
    value === 'son' ||
    value === 'foreign-god' ||
    value === 'creator'
    ? value
    : null
}

function options(table: Record<string, string>, keys: readonly string[]) {
  return keys.map((key) => ({ value: key, label: plain(table, key) }))
}

function signed(value: number) {
  return value > 0 ? `+${value}` : String(value)
}

function StageEffects({ spec, stage }: { spec: Package; stage: number }) {
  const current = spec.stages[stage - 1]
  if (!current) return null
  const marks = [
    current.ageless && 'Does not age',
    current.sunlight_harm && 'Burns in sunlight',
    current.transforms && 'Changes under the moon',
    current.recruits && 'Drawn into a hidden cult',
    current.fears_source && 'Dreads its source',
    current.sanity_loss > 0 && `Sanity −${current.sanity_loss} each epoch`,
  ].filter((item): item is string => typeof item === 'string')
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
      {current.condition && (
        <Badge size='sm' variant='secondary'>
          {`${named(CONDITIONS, current.condition).label} · ${current.severity}/5`}
        </Badge>
      )}
      {Object.entries(current.stats).map(([key, value]) => (
        <Badge
          key={key}
          size='sm'
          variant={value >= 0 ? 'success' : 'destructive'}
        >
          {`${plain(STAT_LABELS, key)} ${signed(value)}`}
        </Badge>
      ))}
      {current.needs.map((need) => (
        <Badge key={need} size='sm' variant='outline'>
          {`Needs ${need.replaceAll('_', ' ')}`}
        </Badge>
      ))}
      {current.quenches.map((need) => (
        <Badge key={`quench-${need}`} size='sm' variant='outline'>
          {`No longer needs ${need.replaceAll('_', ' ')}`}
        </Badge>
      ))}
      {current.grants.map((trait) => (
        <Badge key={`grant-${trait}`} size='sm' variant='success'>
          {`Gains ${named(FUNCTIONS, trait).label.toLowerCase()}`}
        </Badge>
      ))}
      {marks.map((mark) => (
        <Badge key={mark} size='sm' variant='info'>
          {mark}
        </Badge>
      ))}
    </div>
  )
}

function AfflictionCard({
  row,
  spec,
  epoch,
  blocked,
}: {
  row: Affliction
  spec: Package | undefined
  epoch: number
  blocked: string | null
}) {
  const look = named(PACKAGE_LOOKS, row.package)
  const visibility = VISIBILITY[row.visibility]
  const source = linkKind(row.source_link)
  const cured = row.cured_epoch !== null
  const move = useGodAction({
    run: (stage: number) =>
      unwrap(
        api.POST('/api/actions/affliction:edit', {
          body: { affliction_id: row.id, stage, clear_source: false },
        })
      ),
    success: 'The affliction moves to another stage',
  })
  const hold = useGodAction({
    run: (held: boolean) =>
      unwrap(
        api.POST('/api/actions/affliction:hold', {
          body: { affliction_id: row.id, hold: held },
        })
      ),
  })
  const reason = blocked ?? (move.isPending || hold.isPending ? WORKING : null)
  const cures = spec ? spec.cures : []
  const nextIn =
    row.next_stage_epoch !== null
      ? Math.max(0, row.next_stage_epoch - epoch)
      : null
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={look.icon}
          tone={cured ? 'muted' : (look.tone ?? 'gold')}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Text weight='semibold'>{row.label}</Text>
            {row.stage_label && !cured && (
              <Badge size='sm' variant='default'>
                {row.stage_label}
              </Badge>
            )}
            {row.stage === 0 && !cured && (
              <Badge size='sm' variant='secondary'>
                Incubating
              </Badge>
            )}
            {visibility && (
              <Badge size='sm' variant={visibility.badge}>
                <visibility.icon />
                {visibility.label}
              </Badge>
            )}
            {row.held && !cured && (
              <Badge size='sm' variant='warning'>
                <Lock />
                Held
              </Badge>
            )}
            {cured && (
              <Badge size='sm' variant='success'>
                {`Cured epoch ${row.cured_epoch}`}
              </Badge>
            )}
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted variant='caption'>
              {`Since epoch ${row.since_epoch} · through ${plain(TRANSMISSIONS, row.transmission).toLowerCase()}`}
            </Muted>
            {source && row.source_node_id !== null && row.source_name && (
              <>
                <Muted variant='caption'>from</Muted>
                <EntityLink
                  kind={source}
                  id={String(row.source_node_id)}
                  showIcon
                >
                  {row.source_name}
                </EntityLink>
              </>
            )}
          </div>
        </div>
      </div>
      {!cured && (
        <StatBar
          label={`Stage ${row.stage} of ${row.stage_count}`}
          value={row.stage}
          max={Math.max(1, row.stage_count)}
          icon={Hourglass}
          tone={look.tone === 'gold' ? 'success' : 'warning'}
        />
      )}
      {!cured && spec && <StageEffects spec={spec} stage={row.stage} />}
      {!cured && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {nextIn !== null ? (
            <Muted variant='caption'>
              {nextIn === 0
                ? 'Deepens at the next epoch'
                : `Deepens in ${nextIn} epoch${nextIn === 1 ? '' : 's'}`}
            </Muted>
          ) : (
            <Muted variant='caption'>
              {row.held ? 'Held where it is' : 'At its last stage'}
            </Muted>
          )}
          {cures.length > 0 && (
            <Muted variant='caption'>
              {`· cured by ${cures.map((item) => plain(CURES, item).toLowerCase()).join(', ')}`}
            </Muted>
          )}
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {!cured && (
          <>
            <Button
              size='sm'
              variant='ghost'
              disabled={reason !== null || row.stage <= 0}
              disabledReason={reason ?? 'It cannot ease further.'}
              onClick={() => move.mutate(row.stage - 1)}
            >
              <ChevronsDown />
              Ease a stage
            </Button>
            <Button
              size='sm'
              variant='ghost'
              disabled={reason !== null || row.stage >= row.stage_count}
              disabledReason={reason ?? 'It is at its deepest stage.'}
              onClick={() => move.mutate(row.stage + 1)}
            >
              <ChevronsUp />
              Deepen a stage
            </Button>
            <Button
              size='sm'
              variant={row.held ? 'outline' : 'ghost'}
              disabled={reason !== null}
              disabledReason={reason ?? undefined}
              onClick={() => hold.mutate(!row.held)}
            >
              {row.held ? <Unlock /> : <Lock />}
              {row.held ? 'Let it run' : 'Hold it here'}
            </Button>
            <RowAction
              path='/api/actions/affliction:cure'
              icon={ShieldCheck}
              label='Cure it'
              fixed={{ affliction_id: row.id }}
              labels={{ how: 'Cured by' }}
              choices={{ how: options(CURES, Object.keys(CURES)) }}
            />
          </>
        )}
        <RowAction
          path='/api/actions/affliction:edit'
          icon={Pencil}
          label='Reshape'
          iconOnly
          fixed={{ affliction_id: row.id }}
          defaults={{
            transmission: row.transmission,
            source_id: row.source_node_id,
            since_epoch: row.since_epoch,
            stage_since_epoch: row.stage_since_epoch,
            stage: null,
          }}
          labels={{
            transmission: 'Passed through',
            source_id: 'Source',
            clear_source: 'Forget the source',
            since_epoch: 'Began in epoch',
            stage_since_epoch: 'Stage began in epoch',
            stage: 'Stage',
          }}
          choices={{
            transmission: options(TRANSMISSIONS, Object.keys(TRANSMISSIONS)),
          }}
          pickers={{ source_id: { source: 'entity' } }}
        />
        <RowAction
          path='/api/actions/affliction:delete'
          icon={Trash2}
          label='Unmake'
          iconOnly
          destructive
          fixed={{ affliction_id: row.id }}
          confirm={`Unmake ${row.label.toLowerCase()} as if it never was? Its effects are taken back.`}
        />
      </div>
    </li>
  )
}

function PackagePreview({ spec }: { spec: Package }) {
  const look = named(PACKAGE_LOOKS, spec.kind)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={look.icon} tone={look.tone ?? 'gold'} size='sm' />
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='medium'>{spec.label}</Text>
          <Muted variant='caption'>{spec.description}</Muted>
        </div>
      </div>
      <ol className='flex min-w-0 flex-col gap-2'>
        <Paged items={spec.stages} as='li'>
          {(stage) => (
            <li key={stage.number} className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>
                {`${stage.number}. ${stage.label}${stage.epochs !== null ? ` · ${stage.epochs} epoch${stage.epochs === 1 ? '' : 's'}` : ''}`}
              </Label>
              <StageEffects spec={spec} stage={stage.number} />
            </li>
          )}
        </Paged>
      </ol>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {spec.onset > 0 && (
          <Badge size='sm' variant='outline'>
            {`Takes hold after ${spec.onset} epoch${spec.onset === 1 ? '' : 's'}`}
          </Badge>
        )}
        {spec.contagion.map((item) => (
          <Badge key={item} size='sm' variant='warning'>
            {`Spreads by ${plain(TRANSMISSIONS, item).toLowerCase()}`}
          </Badge>
        ))}
        {spec.hereditary && (
          <Badge size='sm' variant='info'>
            Passes to children
          </Badge>
        )}
      </div>
    </div>
  )
}

function GiveForm({
  nodeId,
  packages,
  blocked,
  borne,
}: {
  nodeId: number
  packages: Package[]
  blocked: string | null
  borne: Set<string>
}) {
  const free = packages.filter((item) => !borne.has(item.kind))
  const [kind, setKind] = useState('')
  const chosen = free.find((item) => item.kind === kind) ?? free[0]
  const [transmission, setTransmission] = useState('')
  const route =
    chosen && chosen.transmissions.includes(transmission as Transmission)
      ? transmission
      : (chosen?.transmissions[0] ?? '')
  const give = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/affliction:give', {
          body: {
            bearer_id: nodeId,
            package: (chosen?.kind ?? '') as PackageKind,
            transmission: route as Transmission,
          },
        })
      ),
  })
  const reason =
    blocked ??
    (give.isPending ? WORKING : null) ??
    (chosen ? null : 'They already bear every affliction there is.')
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md p-3 sealed-well'>
      <div className='flex min-w-0 flex-col gap-0.5'>
        <Text weight='semibold'>Lay an affliction or a blessing</Text>
        <Muted variant='caption'>
          Each runs its stages on its own, takes back what it gave when cured,
          and can be held, reshaped or unmade from its card.
        </Muted>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/afflictions:grid-cols-2'>
        <FieldTile label='Affliction'>
          <Select
            value={chosen?.kind ?? ''}
            onValueChange={setKind}
            disabled={!chosen || blocked !== null}
          >
            <SelectTrigger aria-label='Affliction'>
              <SelectValue placeholder='None left to give' />
            </SelectTrigger>
            <SelectContent>
              {free.map((item) => (
                <SelectItem key={item.kind} value={item.kind}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldTile>
        <FieldTile label='Passed through'>
          <Select
            value={route}
            onValueChange={setTransmission}
            disabled={!chosen || blocked !== null}
          >
            <SelectTrigger aria-label='Passed through'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(chosen?.transmissions ?? []).map((item) => (
                <SelectItem key={item} value={item}>
                  {plain(TRANSMISSIONS, item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldTile>
      </div>
      {chosen && <PackagePreview spec={chosen} />}
      <div className='flex justify-end'>
        <Button
          size='sm'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => give.mutate()}
        >
          <Plus />
          Lay it on them
        </Button>
      </div>
    </div>
  )
}

export function AfflictionsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const packages = usePackages()
  const view = useQuery({
    queryKey: afflictionsKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/bodies/{node_id}/afflictions', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
  const data = view.data
  const specs = new Map(
    (packages.data ?? []).map((item) => [item.kind, item] as const)
  )
  const live = (data?.afflictions ?? []).filter(
    (row) => row.cured_epoch === null
  )
  const past = (data?.afflictions ?? []).filter(
    (row) => row.cured_epoch !== null
  )
  return (
    <Section
      id='section-afflictions'
      title='Afflictions and blessings'
      description='Venoms, dependences, curses, blessings, possessions and traumas, each running its stages until cured.'
      icon={Moon}
      tone='verdigris'
    >
      {view.isError ? (
        <EmptyState
          icon={Moon}
          title='Afflictions could not be read'
          description='Try again after the next epoch.'
        />
      ) : !data ? (
        <Muted>Reading what they bear.</Muted>
      ) : (
        <div className='@container/afflictions flex min-w-0 flex-col gap-4'>
          {live.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title='Bears nothing'
              description='No venom, curse, blessing or dependence holds them.'
            />
          ) : (
            <ul className='grid min-w-0 grid-cols-1 gap-3 @2xl/afflictions:grid-cols-2'>
              <Paged items={live} as='li'>
                {(row) => (
                  <AfflictionCard
                    key={row.id}
                    row={row}
                    spec={specs.get(row.package)}
                    epoch={data.epoch}
                    blocked={reason()}
                  />
                )}
              </Paged>
            </ul>
          )}
          {past.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Cured</Label>
              <ul className='grid min-w-0 grid-cols-1 gap-3 @2xl/afflictions:grid-cols-2'>
                <Paged items={past} as='li'>
                  {(row) => (
                    <AfflictionCard
                      key={row.id}
                      row={row}
                      spec={specs.get(row.package)}
                      epoch={data.epoch}
                      blocked={reason()}
                    />
                  )}
                </Paged>
              </ul>
            </div>
          )}
          {data.bearable ? (
            <GiveForm
              nodeId={nodeId}
              packages={packages.data ?? []}
              blocked={reason()}
              borne={new Set(live.map((row) => row.package))}
            />
          ) : (
            <Muted variant='caption'>
              Only the living can be given an affliction.
            </Muted>
          )}
        </div>
      )}
    </Section>
  )
}
