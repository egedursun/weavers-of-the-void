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
import { type EntryKind } from '@/components/layout/entry/entryStack'
import { Label, Muted, Text } from '@/components/typography'
import { NEED_WORDS } from '@/features/entity/affairs/labels'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { RowAction } from '../actions/RowAction'
import { loreKeys } from '../api/keys'
import {
  CHANGE_SIGNS,
  CHARMS,
  CURES,
  FORGET_SCOPES,
  FORTUNE_SIGNS,
  PACKAGE_LOOKS,
  SLEEP_UNTILS,
  STAT_LABELS,
  TRANSMISSIONS,
  VISIBILITY,
} from '../body/afflictionLabels'
import { CONDITIONS, FUNCTIONS, PLANS, named, plain } from '../body/labels'

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

function linkKind(value: string | null): EntryKind | null {
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
    current.transforms && 'Changes its form',
    current.changes_body && 'Changes the body',
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
          {`Needs ${NEED_WORDS[need].toLowerCase()}`}
        </Badge>
      ))}
      {current.quenches.map((need) => (
        <Badge key={`quench-${need}`} size='sm' variant='outline'>
          {`No longer needs ${NEED_WORDS[need].toLowerCase()}`}
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
    writes: [{ lever: 'affliction:edit' }],
    run: (stage: number) =>
      unwrap(
        api.POST('/api/actions/affliction:edit', {
          body: { affliction_id: row.id, stage, clear_source: false },
        })
      ),
    success: 'The affliction moves to another stage',
  })
  const hold = useGodAction({
    writes: [{ lever: 'affliction:hold' }],
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
      {!cured && <PackageShape row={row} />}
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
              act={move}
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
              act={move}
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
              act={hold}
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
            fortune_sign: row.fortune_sign,
            fortune_strength: row.fortune_strength,
            transform_plan: row.transform_plan,
            transform_species_id: row.transform_species_id,
            transform_substance: row.transform_substance,
            transform_trigger: row.transform_trigger,
            transform_mind_kept: row.transform_mind_kept,
            charm_target_id: row.charm_target_id,
            charm_kind: row.charm_kind,
            charm_strength: row.charm_strength,
            ageing_rate_pct: row.ageing_rate_pct,
            forget_scope: row.forget_scope,
            sleep_until: row.sleep_until,
          }}
          labels={{
            transmission: 'Passed through',
            source_id: 'Source',
            clear_source: 'Forget the source',
            since_epoch: 'Began in epoch',
            stage_since_epoch: 'Stage began in epoch',
            stage: 'Stage',
            fortune_sign: 'Fortune leans to (1 good, -1 ill)',
            fortune_strength: 'Fortune strength',
            transform_plan: 'Changes into a body',
            transform_species_id: 'Changes into the kind',
            transform_substance: 'Changes into the substance',
            transform_trigger: 'Changes again at',
            transform_mind_kept: 'Keeps its own mind',
            charm_target_id: 'Charmed toward',
            charm_kind: 'Charm of',
            charm_strength: 'Charm strength',
            ageing_rate_pct: 'Ageing rate (%)',
            forget_scope: 'What it takes',
            sleep_until: 'Sleeps until',
          }}
          choices={{
            transmission: options(TRANSMISSIONS, Object.keys(TRANSMISSIONS)),
            transform_plan: Object.entries(PLANS).map(([value, item]) => ({
              value,
              label: item.label,
            })),
            transform_trigger: Object.entries(CHANGE_SIGNS).map(
              ([value, item]) => ({ value, label: item.label })
            ),
            charm_kind: Object.entries(CHARMS).map(([value, item]) => ({
              value,
              label: item.label,
            })),
            forget_scope: Object.entries(FORGET_SCOPES).map(
              ([value, item]) => ({
                value,
                label: item.label,
              })
            ),
            sleep_until: Object.entries(SLEEP_UNTILS).map(([value, item]) => ({
              value,
              label: item.label,
            })),
          }}
          pickers={{
            source_id: { source: 'entity' },
            charm_target_id: { source: 'entity' },
            transform_species_id: { source: 'entity' },
          }}
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

function PackageShape({ row }: { row: Affliction }) {
  const lean =
    row.fortune_sign !== null ? FORTUNE_SIGNS[String(row.fortune_sign)] : null
  const plan = row.transform_plan ? PLANS[row.transform_plan] : null
  const sign = row.transform_trigger
    ? CHANGE_SIGNS[row.transform_trigger]
    : null
  const charm = row.charm_kind ? CHARMS[row.charm_kind] : null
  if (!lean && !plan && !charm) return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      {lean && (
        <StatBar
          framed
          label={`${lean.label} at strength ${row.fortune_strength ?? 0}`}
          value={row.fortune_strength ?? 0}
          max={100}
          icon={lean.icon}
          tone={
            row.fortune_sign !== null && row.fortune_sign > 0
              ? 'success'
              : 'destructive'
          }
        />
      )}
      {plan && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='secondary'>
            <plan.icon />
            {`Becomes ${plan.label.toLowerCase()}`}
          </Badge>
          {sign && (
            <Badge size='sm' variant='outline'>
              <sign.icon />
              {sign.label}
            </Badge>
          )}
          <Badge
            size='sm'
            variant={row.transform_mind_kept ? 'success' : 'warning'}
          >
            {row.transform_mind_kept
              ? 'Keeps its own mind'
              : 'Loses its own mind'}
          </Badge>
          {row.changed_from && (
            <Muted variant='caption'>{`Changed now, from ${PLANS[row.changed_from].label.toLowerCase()}`}</Muted>
          )}
        </div>
      )}
      {(row.ageing_rate_pct !== null ||
        row.forget_scope !== null ||
        row.sleep_until !== null) && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {row.ageing_rate_pct !== null && (
            <Badge size='sm' variant='info'>
              {`Ages at ${row.ageing_rate_pct}% of the usual pace`}
            </Badge>
          )}
          {row.forget_scope !== null && (
            <Badge size='sm' variant='warning'>
              {`Takes ${FORGET_SCOPES[row.forget_scope].label.toLowerCase()}`}
            </Badge>
          )}
          {row.sleep_until !== null && (
            <Badge size='sm' variant='secondary'>
              {`Sleeps ${SLEEP_UNTILS[row.sleep_until].label.toLowerCase()}`}
            </Badge>
          )}
        </div>
      )}
      {charm && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant='warning'>
              <charm.icon />
              {`Charm of ${charm.label.toLowerCase()}`}
            </Badge>
            {row.charm_target_id !== null && row.charm_target_name && (
              <>
                <Muted variant='caption'>toward</Muted>
                <EntityLink
                  kind='entity'
                  id={String(row.charm_target_id)}
                  showIcon
                >
                  {row.charm_target_name}
                </EntityLink>
              </>
            )}
          </div>
          <StatBar
            framed
            label={`Charm strength ${row.charm_strength ?? 0}`}
            value={row.charm_strength ?? 0}
            max={100}
            icon={charm.icon}
            tone='warning'
          />
        </div>
      )}
    </div>
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
    writes: [{ lever: 'affliction:give' }],
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
          act={give}
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
