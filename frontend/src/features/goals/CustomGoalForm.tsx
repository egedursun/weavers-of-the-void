import { useState } from 'react'
import { WandSparkles } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { goalBasisValues, goalComparatorValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow, Section } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { CountField, DeadlineField, QuotePreview } from './GoalFields'
import {
  BASIS_LABEL,
  COMPARATOR_LABEL,
  type GoalBasis,
  type GoalComparator,
  type GoalMetric,
  type GoalsOverview,
  useGoalQuote,
} from './api'
import {
  DEFAULT_DEADLINE,
  outOfRange,
  parseCount,
  useDeadlineMax,
} from './goalForm'

const FALLBACK_RUNNING = 5
const FALLBACK_HOLD = 200
const FALLBACK_TARGET = 2000000000
const TITLE_MAX = 200

export function CustomGoalForm({ data }: { data: GoalsOverview }) {
  const first = data.metrics[0]
  const [metric, setMetric] = useState<GoalMetric>(first?.metric ?? 'worlds')
  const [comparator, setComparator] = useState<GoalComparator>('at_least')
  const [basis, setBasis] = useState<GoalBasis>('total')
  const [target, setTarget] = useState(String((first?.value ?? 0) + 1))
  const [hold, setHold] = useState('0')
  const [timed, setTimed] = useState(false)
  const [epochs, setEpochs] = useState(String(DEFAULT_DEADLINE))
  const [title, setTitle] = useState('')
  const rule = useRuleLookup()
  const deadlineMax = useDeadlineMax()
  const runningMax = rule('goals.custom_max_running') ?? FALLBACK_RUNNING
  const holdMax = rule('goals.custom_hold_max_epochs') ?? FALLBACK_HOLD
  const targetMax = rule('goals.custom_target_max') ?? FALLBACK_TARGET
  const { reason } = useGodGate()
  const current = data.metrics.find((item) => item.metric === metric)
  const runningCustom = data.running.filter(
    (item) => item.key === 'custom'
  ).length
  const chosen = parseCount(target)
  const held = parseCount(hold)
  const deadline = timed ? parseCount(epochs) : null
  const low = basis === 'gained' ? 1 : 0
  const invalid =
    outOfRange(chosen, low, targetMax, 'target') ??
    outOfRange(held, 0, holdMax, 'hold') ??
    (timed ? outOfRange(deadline, 1, deadlineMax, 'deadline') : null) ??
    (title.trim().length > TITLE_MAX
      ? `A name holds at most ${TITLE_MAX} characters.`
      : null)
  const quote = useGoalQuote(
    invalid === null && chosen !== null
      ? {
          key: 'custom',
          metric,
          comparator,
          basis,
          target: chosen,
          hold_epochs: held ?? 0,
          deadline_epochs: deadline ?? undefined,
        }
      : null
  )
  const start = useGodAction({
    writes: [{ lever: 'scenario:custom' }],
    run: () =>
      unwrap(
        api.POST('/api/scenarios/custom', {
          body: {
            metric,
            comparator,
            basis,
            target: chosen ?? 0,
            hold_epochs: held ?? 0,
            deadline_epochs: deadline,
            title: title.trim() || null,
          },
        })
      ),
    onDone: () => setTitle(''),
  })
  const full =
    runningCustom >= runningMax
      ? `At most ${plural(runningMax, 'goal', 'goals')} of your own may run at once; finish or abandon one first.`
      : null
  const chooseMetric = (value: string) => {
    const next = data.metrics.find((item) => item.metric === value)
    if (!next) return
    setMetric(next.metric)
    setComparator(next.lower_is_better ? 'at_most' : 'at_least')
    setBasis('total')
    setTarget(
      String(
        next.lower_is_better ? Math.max(0, next.value - 1) : next.value + 1
      )
    )
  }
  const chooseBasis = (value: string) => {
    const next = goalBasisValues.find((item) => item === value)
    if (!next) return
    setBasis(next)
    if (next === 'gained') {
      setComparator('at_least')
      setTarget('1')
    }
  }
  return (
    <Section
      title='A goal of your own'
      description='Choose any measure of the cosmos, set the mark it must reach, how long it must hold and by when. The further the mark, the more it is worth.'
      icon={WandSparkles}
      surface='card'
      level={3}
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <FormRow
          label='Measure'
          description={
            current
              ? `Now ${formatInteger(current.value)}${current.lower_is_better ? '; lower is better' : ''}.`
              : undefined
          }
        >
          {(id) => (
            <Select value={metric} onValueChange={chooseMetric}>
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {data.categories.map((category) => (
                  <SelectGroup key={category.category}>
                    <SelectLabel>{category.label}</SelectLabel>
                    {data.metrics
                      .filter((item) => item.category === category.category)
                      .map((item) => (
                        <SelectItem key={item.metric} value={item.metric}>
                          {`${item.label} · ${formatInteger(item.value)}`}
                        </SelectItem>
                      ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow
          label='Counted'
          description='Count all there is, or only what is gained after the goal begins.'
        >
          {(id) => (
            <Select value={basis} onValueChange={chooseBasis}>
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {goalBasisValues.map((item) => (
                  <SelectItem key={item} value={item}>
                    {BASIS_LABEL[item]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow
          label='Bound'
          description={
            basis === 'gained'
              ? 'What is gained can only be asked for at least.'
              : 'Reach the mark from below, or keep the measure under it.'
          }
        >
          {(id) => (
            <Select
              value={comparator}
              onValueChange={(value) => {
                const next = goalComparatorValues.find((item) => item === value)
                if (next) setComparator(next)
              }}
              disabled={basis === 'gained'}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {goalComparatorValues.map((item) => (
                  <SelectItem key={item} value={item}>
                    {COMPARATOR_LABEL[item]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <CountField
          label='Target'
          description={
            basis === 'gained'
              ? 'How many more than at the start.'
              : 'The mark the measure must reach.'
          }
          value={target}
          min={low}
          max={targetMax}
          onChange={setTarget}
        />
        <CountField
          label='Hold'
          description='Epochs in a row the mark must be kept; 0 ends the goal the moment it is reached.'
          value={hold}
          min={0}
          max={holdMax}
          onChange={setHold}
        />
        <FormRow
          label='Name of the goal'
          description='Optional; without a name the goal is called by its measure.'
        >
          {(id) => (
            <Input
              id={id}
              value={title}
              maxLength={TITLE_MAX}
              className='w-full'
              onChange={(event) => setTitle(event.target.value)}
            />
          )}
        </FormRow>
      </div>
      <DeadlineField
        enabled={timed}
        epochs={epochs}
        max={deadlineMax}
        onEnabled={setTimed}
        onEpochs={setEpochs}
      />
      <QuotePreview
        quote={invalid === null ? quote.data : undefined}
        pending={quote.isFetching}
        deadline={deadline}
      />
      <div className='flex min-w-0 flex-wrap items-center justify-end gap-2'>
        <ActionButton
          act={start}
          label='Set the goal'
          icon={WandSparkles}
          variant='default'
          blocked={reason() ?? full ?? invalid}
          pending={start.isPending}
          onRun={() => start.mutate()}
        />
      </div>
    </Section>
  )
}
