import { useMemo, useState } from 'react'
import {
  Cog,
  Cpu,
  Hourglass,
  Layers,
  type LucideIcon,
  Power,
  PowerOff,
  RefreshCw,
  Search,
  Sunrise,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  EmptyState,
  Medallion,
  MiniStat,
  Section,
} from '@/components/domain'
import { type Choice, ChoiceTiles } from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useWorldState } from '@/features/overview/api'
import { IntegrityPanel } from './IntegrityPanel'
import { PhaseRow } from './PhaseRow'
import { SeedPanel } from './SeedPanel'
import {
  type EnginePhase,
  type PhaseStage,
  useEnginePhases,
  useRunPhase,
  useSetPhaseSwitch,
} from './api'
import {
  STAGE_DESCRIPTION,
  STAGE_ORDER,
  STAGE_TITLE,
  matchesQuery,
  phaseLabel,
  phasesByStage,
} from './phaseModel'

const STAGE_ICON: Record<PhaseStage, LucideIcon> = {
  tick: Cog,
  pre_transition: Hourglass,
  transition: RefreshCw,
  post_transition: Sunrise,
}

const VIEWS: readonly Choice<PhaseView>[] = [
  { value: 'all', label: 'Every step', icon: Layers },
  { value: 'off', label: 'Switched off', icon: PowerOff },
  { value: 'heavy', label: 'Heavy steps', icon: TriangleAlert },
]

type PhaseView = 'all' | 'off' | 'heavy'

function fits(phase: EnginePhase, view: PhaseView, query: string) {
  if (!matchesQuery(phase, query)) return false
  if (view === 'off') return !phase.enabled
  if (view === 'heavy') return phase.heavy
  return true
}

export function EnginePage() {
  const state = useWorldState()
  const phases = useEnginePhases()
  const run = useRunPhase()
  const toggle = useSetPhaseSwitch()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<PhaseView>('all')
  const [stage, setStage] = useState<PhaseStage | null>(null)
  const [pending, setPending] = useState<EnginePhase | null>(null)
  const readOnlyReason = state.data?.read_only ? READ_ONLY_REASON : null
  const all = useMemo(() => phases.data?.phases ?? [], [phases.data])
  const grouped = useMemo(() => phasesByStage(all), [all])
  const order = useMemo(() => {
    const map = new Map<string, number>()
    let index = 0
    for (const name of STAGE_ORDER)
      for (const phase of grouped.get(name) ?? []) map.set(phase.name, ++index)
    return map
  }, [grouped])
  const busy = run.isPending || toggle.isPending
  const off = all.filter((phase) => !phase.enabled).length

  const execute = (phase: EnginePhase) => {
    run.mutate(phase.name, {
      onSuccess: (result) => toast.success(result.message),
      onError: (error) => toast.error(error.message),
      onSettled: () => setPending(null),
    })
  }

  const onToggle = (phase: EnginePhase, on: boolean) =>
    toggle.mutate(
      { rule: phase.rule_key, on },
      {
        onSuccess: () =>
          toast.success(
            `${phaseLabel(phase.name)} ${on ? 'will run' : 'is switched off'}.`
          ),
        onError: (error) => toast.error(error.message),
      }
    )

  const stages = STAGE_ORDER.filter((name) => stage === null || name === stage)
  const visible = stages.map(
    (name) =>
      [
        name,
        (grouped.get(name) ?? []).filter((phase) => fits(phase, view, query)),
      ] as const
  )

  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <MiniStat
          icon={Cpu}
          label='Engine steps'
          value={all.length}
          tone='gold'
        />
        <MiniStat
          icon={Power}
          label='Running each epoch'
          value={all.length - off}
          tone='success'
        />
        <MiniStat
          icon={PowerOff}
          label='Switched off'
          value={off}
          tone={off > 0 ? 'warning' : 'muted'}
        />
        <MiniStat
          icon={TriangleAlert}
          label='Heavy steps'
          value={all.filter((phase) => phase.heavy).length}
          tone='danger'
          hint='Steps that change many records at once'
        />
      </div>
      <Section
        title='The epoch, step by step'
        description='The world engine runs these steps every epoch, in this order. Switch a step off to skip it, or run one right now without advancing time.'
        surface='card'
        icon={Cpu}
      >
        <ol className='grid min-w-0 grid-cols-1 items-stretch gap-2 sm:grid-cols-2 xl:grid-cols-5'>
          <li className='min-w-0'>
            <Button
              variant='outline'
              size='tile'
              aria-pressed={stage === null}
              onClick={() => setStage(null)}
              className={cn(
                stage === null && 'border-primary/60 bg-primary/10'
              )}
            >
              <Medallion icon={Layers} tone='gold' size='sm' />
              <span className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' weight='semibold' truncate>
                  Whole epoch
                </Text>
                <Muted as='span' variant='caption'>
                  {`${all.length} steps`}
                </Muted>
              </span>
            </Button>
          </li>
          {STAGE_ORDER.map((name, index) => {
            const members = grouped.get(name) ?? []
            const silent = members.filter((phase) => !phase.enabled).length
            const active = stage === name
            return (
              <li key={name} className='min-w-0'>
                <Button
                  variant='outline'
                  size='tile'
                  aria-pressed={active}
                  onClick={() => setStage(name)}
                  className={cn(active && 'border-primary/60 bg-primary/10')}
                >
                  <Medallion
                    icon={STAGE_ICON[name]}
                    tone={active ? 'gold' : 'verdigris'}
                    size='sm'
                  />
                  <span className='flex min-w-0 flex-1 flex-col'>
                    <Text as='span' weight='semibold' truncate>
                      {`${index + 1}. ${STAGE_TITLE[name]}`}
                    </Text>
                    <Muted as='span' variant='caption' truncate>
                      {silent > 0
                        ? `${members.length} steps · ${silent} off`
                        : `${members.length} steps`}
                    </Muted>
                  </span>
                </Button>
              </li>
            )
          })}
        </ol>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <div className='min-w-0 flex-1 basis-64'>
            <Input
              type='search'
              leadingIcon={Search}
              aria-label='Search engine steps'
              placeholder='Search steps, for example war, plague or migration'
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div className='min-w-0 flex-1 basis-96'>
            <ChoiceTiles
              label='Which steps'
              value={view}
              options={VIEWS}
              onChange={setView}
            />
          </div>
        </div>
      </Section>
      {phases.isPending && <Skeleton className='h-textarea w-full' />}
      {phases.isError && <Text tone='destructive'>{phases.error.message}</Text>}
      {phases.data &&
        visible.map(([name, shown]) =>
          shown.length === 0 ? null : (
            <Section
              key={name}
              title={STAGE_TITLE[name]}
              description={STAGE_DESCRIPTION[name]}
              surface='card'
              level={3}
              icon={STAGE_ICON[name]}
              tone='verdigris'
            >
              <ul className='grid min-w-0 grid-cols-1 gap-2 xl:grid-cols-2'>
                {shown.map((phase) => (
                  <PhaseRow
                    key={phase.name}
                    phase={phase}
                    order={order.get(phase.name) ?? 0}
                    busy={busy}
                    readOnlyReason={readOnlyReason}
                    onToggle={onToggle}
                    onRun={(item) =>
                      item.heavy ? setPending(item) : execute(item)
                    }
                  />
                ))}
              </ul>
            </Section>
          )
        )}
      {phases.data && visible.every(([, shown]) => shown.length === 0) && (
        <EmptyState
          icon={Cpu}
          title='No step matches'
          description='Try another word or filter, or pick the whole epoch.'
        />
      )}
      <IntegrityPanel readOnlyReason={readOnlyReason} />
      <SeedPanel />
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={
          pending ? `Run ${phaseLabel(pending.name).toLowerCase()} now?` : ''
        }
        desc='This step can change many records at once. It runs on top of the current epoch and can be undone from the ledger.'
        confirmText='Run now'
        isLoading={run.isPending}
        handleConfirm={() => pending && execute(pending)}
      />
    </div>
  )
}
