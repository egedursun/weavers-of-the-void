import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, Lock, Plus, Save, Trash2, X } from 'lucide-react'
import { toast } from 'sonner'
import { stepImpactValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  FieldTile,
  FormRow,
  LoadingBlock,
  Paged,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { FieldControl } from '@/features/command-palette/ActionDialog'
import {
  type ActionItem,
  useActionCatalogue,
} from '@/features/command-palette/api'
import {
  type FieldValues,
  buildPayload,
  fieldsOf,
} from '@/features/command-palette/schemaForm'
import { useSavePlanSteps } from './api'
import { IMPACT_LOOK, STEP_STATUS_LOOK } from './planLook'
import {
  type DraftStep,
  blankStep,
  moveStep,
  planProblem,
  removeStep,
  stepInputs,
  valuesFromInput,
} from './planModel'
import { type StepImpact } from './types'

const IMPACTS: readonly StepImpact[] = stepImpactValues
const STEPS_SHOWN = 12

function StepInputs({
  action,
  step,
  onInput,
}: {
  action: ActionItem
  step: DraftStep
  onInput: (input: Record<string, unknown>, error: string | null) => void
}) {
  const fields = useMemo(() => fieldsOf(action.input_schema), [action])
  const [values, setValues] = useState<FieldValues>(() =>
    valuesFromInput(fields, step.input)
  )
  const [error, setError] = useState<string | null>(null)
  const change = (name: string, value: string | boolean | string[]) => {
    const next = { ...values, [name]: value }
    setValues(next)
    const built = buildPayload(fields, next)
    const problem = 'error' in built ? built.error : null
    setError(problem)
    onInput('error' in built ? step.input : built.payload, problem)
  }
  if (fields.length === 0)
    return <Muted variant='caption'>This act needs no input.</Muted>
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/will:grid-cols-2'>
        {fields.map((field) => (
          <FormRow
            key={field.name}
            label={field.required ? `${field.label} *` : field.label}
          >
            {(id) => (
              <FieldControl
                field={field}
                id={id}
                value={values[field.name]}
                onChange={(next) => change(field.name, next)}
              />
            )}
          </FormRow>
        ))}
      </div>
      {error && (
        <Text variant='caption' tone='destructive' role='alert'>
          {error}
        </Text>
      )}
    </div>
  )
}

function LockedStep({ step, index }: { step: DraftStep; index: number }) {
  const look = STEP_STATUS_LOOK[step.status]
  const Icon = look.icon
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-md px-3 py-2 sealed-well'>
      <Lock
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <Text as='span' weight='medium' truncate className='flex-1'>
        {`${String(index + 1)}. ${step.title}`}
      </Text>
      <Badge size='sm' variant={look.badge}>
        <Icon />
        {look.label}
      </Badge>
    </li>
  )
}

type EditorProps = {
  planId: number
  title: string
  initial: DraftStep[]
  onDone: () => void
}

export function PlanStepEditor({
  planId,
  title,
  initial,
  onDone,
}: EditorProps) {
  const [steps, setSteps] = useState<DraftStep[]>(initial)
  const [name, setName] = useState(title)
  const [inputErrors, setInputErrors] = useState<Record<string, string>>({})
  const catalogue = useActionCatalogue(true)
  const save = useSavePlanSteps(planId)
  const actions = useMemo(() => catalogue.data ?? [], [catalogue.data])
  const byId = useMemo(
    () => new Map(actions.map((action) => [action.id, action])),
    [actions]
  )
  const options = useMemo(
    () =>
      actions.map((action) => ({
        value: action.id,
        label: action.title,
        hint: action.cost,
        keywords: `${action.id} ${action.group}`,
      })),
    [actions]
  )
  const update = (key: string, change: Partial<DraftStep>) =>
    setSteps((current) =>
      current.map((step) => (step.key === key ? { ...step, ...change } : step))
    )
  const firstInputError = Object.values(inputErrors)[0] ?? null
  const problem = name.trim()
    ? (planProblem(steps) ?? firstInputError)
    : 'The plan needs a title.'
  const block = save.isPending ? 'Saving the steps.' : problem
  const submit = () => {
    if (block) return
    save.mutate(
      { steps: stepInputs(steps), title: name.trim() },
      {
        onSuccess: () => {
          toast.success('The plan is revised.')
          onDone()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  if (catalogue.isPending) return <LoadingBlock label='Loading the acts' />
  if (catalogue.isError)
    return (
      <Text tone='destructive' role='alert'>
        {`The acts could not be loaded: ${catalogue.error.message}`}
      </Text>
    )
  return (
    <div data-domain='will-plan-editor' className='flex min-w-0 flex-col gap-3'>
      <FormRow label='Title of the plan'>
        {(id) => (
          <Input
            id={id}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        )}
      </FormRow>
      <Muted variant='caption'>
        Saving the steps returns the plan to a draft; approve it again before it
        runs.
      </Muted>
      <ol className='flex min-w-0 flex-col gap-2.5'>
        <Paged
          items={steps}
          initial={STEPS_SHOWN}
          as='li'
          noun={['step', 'steps']}
        >
          {(step, index) => {
            if (step.locked)
              return <LockedStep key={step.key} step={step} index={index} />
            const action = byId.get(step.actionId) ?? null
            const earlier = steps.slice(0, index)
            return (
              <li
                key={step.key}
                data-step-key={step.key}
                className='flex min-w-0 flex-col gap-3 rounded-md surface-sheen px-3 py-3'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Badge size='sm' variant='outline'>
                    {String(index + 1)}
                  </Badge>
                  <Input
                    value={step.title}
                    aria-label={`Title of step ${String(index + 1)}`}
                    placeholder='What this step does'
                    onChange={(event) =>
                      update(step.key, { title: event.target.value })
                    }
                    className='min-w-0 flex-1'
                  />
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    aria-label={`Move step ${String(index + 1)} up`}
                    disabled={index === 0 || steps[index - 1].locked}
                    disabledReason={
                      index === 0
                        ? 'This is already the first step.'
                        : 'The step above has already run.'
                    }
                    onClick={() => setSteps(moveStep(steps, index, -1))}
                  >
                    <ArrowUp />
                  </Button>
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    aria-label={`Move step ${String(index + 1)} down`}
                    disabled={index === steps.length - 1}
                    disabledReason='This is already the last step.'
                    onClick={() => setSteps(moveStep(steps, index, 1))}
                  >
                    <ArrowDown />
                  </Button>
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    aria-label={`Delete step ${String(index + 1)}`}
                    onClick={() => {
                      setSteps(removeStep(steps, step.key))
                      setInputErrors((current) => {
                        const rest = { ...current }
                        delete rest[step.key]
                        return rest
                      })
                    }}
                  >
                    <Trash2 />
                  </Button>
                </div>
                <div className='grid min-w-0 grid-cols-1 gap-3 @lg/will:grid-cols-2'>
                  <FormRow label='Act'>
                    {(id) => (
                      <RecordCombobox
                        id={id}
                        options={options}
                        value={step.actionId || null}
                        placeholder='Choose an act'
                        searchPlaceholder='Search the acts'
                        emptyText='No act has this name.'
                        aria-label={`Act of step ${String(index + 1)}`}
                        onChange={(value) => {
                          update(step.key, { actionId: value ?? '', input: {} })
                          setInputErrors((current) => {
                            const rest = { ...current }
                            delete rest[step.key]
                            return rest
                          })
                        }}
                      />
                    )}
                  </FormRow>
                  <FormRow
                    label='Declared impact'
                    description={IMPACT_LOOK[step.impact].hint}
                  >
                    {(id) => (
                      <Select
                        value={step.impact}
                        onValueChange={(value) => {
                          const impact = IMPACTS.find((item) => item === value)
                          if (impact) update(step.key, { impact })
                        }}
                      >
                        <SelectTrigger id={id} className='w-full'>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {IMPACTS.map((impact) => (
                            <SelectItem key={impact} value={impact}>
                              {IMPACT_LOOK[impact].label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </FormRow>
                  <FormRow label='Essence foreseen'>
                    {(id) => (
                      <Input
                        id={id}
                        type='number'
                        inputMode='numeric'
                        min={0}
                        value={String(step.essence)}
                        onChange={(event) => {
                          const value = Number(event.target.value)
                          update(step.key, {
                            essence:
                              Number.isFinite(value) && value >= 0
                                ? Math.round(value)
                                : 0,
                          })
                        }}
                      />
                    )}
                  </FormRow>
                </div>
                <div className='flex min-w-0 flex-col gap-1.5'>
                  <Label>Waits on</Label>
                  {earlier.length === 0 ? (
                    <Muted variant='caption'>
                      The first step waits on nothing.
                    </Muted>
                  ) : (
                    <WaitsOn step={step} earlier={earlier} update={update} />
                  )}
                </div>
                <div className='flex min-w-0 flex-col gap-1.5'>
                  <Label>Input of the act</Label>
                  {action ? (
                    <StepInputs
                      key={action.id}
                      action={action}
                      step={step}
                      onInput={(input, error) => {
                        update(step.key, { input })
                        setInputErrors((current) => {
                          const rest = { ...current }
                          if (error)
                            rest[step.key] =
                              `Step ${String(index + 1)}: ${error}`
                          else delete rest[step.key]
                          return rest
                        })
                      }}
                    />
                  ) : (
                    <Muted variant='caption'>
                      Choose an act to fill in its input.
                    </Muted>
                  )}
                </div>
              </li>
            )
          }}
        </Paged>
      </ol>
      <Button
        variant='outline'
        size='sm'
        className='w-fit'
        onClick={() => setSteps([...steps, blankStep()])}
      >
        <Plus />
        Add a step
      </Button>
      {problem && (
        <Muted variant='caption' role='status'>
          {problem}
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap items-center justify-end gap-2'>
        <Button variant='ghost' size='sm' onClick={onDone}>
          <X />
          Cancel
        </Button>
        <Button
          act={save}
          size='sm'
          disabled={block !== null}
          disabledReason={block ?? undefined}
          onClick={submit}
        >
          <Save />
          Save the steps
        </Button>
      </div>
    </div>
  )
}

const SHOWN_EARLIER = 8

function WaitsOn({
  step,
  earlier,
  update,
}: {
  step: DraftStep
  earlier: readonly DraftStep[]
  update: (key: string, change: Partial<DraftStep>) => void
}) {
  const shown = useShowMore(earlier, SHOWN_EARLIER)
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {shown.visible.map((other, position) => (
          <FieldTile
            key={other.key}
            id={`${step.key}-waits-${other.key}`}
            label={`${String(position + 1)}. ${other.title || 'Untitled step'}`}
          >
            <Checkbox
              id={`${step.key}-waits-${other.key}`}
              checked={step.dependsOn.includes(other.key)}
              onCheckedChange={(checked) =>
                update(step.key, {
                  dependsOn:
                    checked === true
                      ? [...step.dependsOn, other.key]
                      : step.dependsOn.filter((item) => item !== other.key),
                })
              }
            />
          </FieldTile>
        ))}
      </div>
      <ShowMore state={shown} />
    </div>
  )
}
