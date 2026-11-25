import {
  type FieldValues,
  type FormField,
  initialValues,
} from '@/features/command-palette/schemaForm'
import {
  type PlanStatus,
  type StepImpact,
  type StepStatus,
  type WillPlan,
  type WillPlanStepInput,
} from './types'

export type DraftStep = {
  key: string
  ordinal: number | null
  title: string
  actionId: string
  input: Record<string, unknown>
  dependsOn: string[]
  impact: StepImpact
  essence: number
  status: StepStatus
  locked: boolean
}

const LOCKED_STEPS: ReadonlySet<StepStatus> = new Set([
  'running',
  'done',
  'skipped',
  'undone',
])

export const EDITABLE_PLANS: ReadonlySet<PlanStatus> = new Set([
  'draft',
  'approved',
  'paused',
  'failed',
])

let nextKey = 0

export function freshKey(): string {
  nextKey += 1
  return `step-${String(nextKey)}`
}

export function draftOf(plan: WillPlan): DraftStep[] {
  const keyOfOrdinal = new Map(
    plan.steps.map((step) => [step.ordinal, `ordinal-${String(step.ordinal)}`])
  )
  return plan.steps.map((step) => ({
    key: keyOfOrdinal.get(step.ordinal) ?? freshKey(),
    ordinal: step.ordinal,
    title: step.title,
    actionId: step.action_id,
    input: step.input,
    dependsOn: step.depends_on.flatMap((ordinal) => {
      const key = keyOfOrdinal.get(ordinal)
      return key ? [key] : []
    }),
    impact: step.declared_impact,
    essence: step.estimated_essence,
    status: step.status,
    locked: LOCKED_STEPS.has(step.status),
  }))
}

export function blankStep(): DraftStep {
  return {
    key: freshKey(),
    ordinal: null,
    title: '',
    actionId: '',
    input: {},
    dependsOn: [],
    impact: 'safe',
    essence: 0,
    status: 'pending',
    locked: false,
  }
}

export function moveStep(
  steps: DraftStep[],
  index: number,
  step: 1 | -1
): DraftStep[] {
  const target = index + step
  if (target < 0 || target >= steps.length) return steps
  if (steps[index].locked || steps[target].locked) return steps
  const next = [...steps]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
}

export function removeStep(steps: DraftStep[], key: string): DraftStep[] {
  return steps
    .filter((step) => step.key !== key)
    .map((step) => ({
      ...step,
      dependsOn: step.dependsOn.filter((item) => item !== key),
    }))
}

export function planProblem(steps: DraftStep[]): string | null {
  if (steps.length === 0) return 'A plan needs at least one step.'
  const seen = new Set<string>()
  for (const [index, step] of steps.entries()) {
    const label = `Step ${String(index + 1)}`
    if (!step.title.trim()) return `${label} needs a title.`
    if (!step.actionId) return `${label} needs an act.`
    if (step.locked && step.ordinal !== index + 1)
      return `Step ${String(step.ordinal)} has already run and keeps its place; move the others around it.`
    if (step.dependsOn.some((key) => !seen.has(key)))
      return `${label} waits on a step that comes after it; move it below.`
    seen.add(step.key)
  }
  return null
}

export function stepInputs(steps: DraftStep[]): WillPlanStepInput[] {
  const ordinal = new Map(steps.map((step, index) => [step.key, index + 1]))
  return steps.map((step) => ({
    title: step.title.trim(),
    action_id: step.actionId,
    input: step.input,
    depends_on: step.dependsOn.flatMap((key) => {
      const value = ordinal.get(key)
      return value === undefined ? [] : [value]
    }),
    declared_impact: step.impact,
    estimated_essence: step.essence,
  }))
}

export function valuesFromInput(
  fields: FormField[],
  input: Record<string, unknown>
): FieldValues {
  const values = initialValues(fields)
  for (const field of fields) {
    if (!(field.name in input)) continue
    const value = input[field.name]
    if (field.kind === 'boolean') values[field.name] = value === true
    else if (field.kind === 'enum-list')
      values[field.name] = Array.isArray(value) ? value.map(String) : []
    else if (field.kind === 'integer-list' || field.kind === 'string-list')
      values[field.name] = Array.isArray(value)
        ? value.map(String).join(', ')
        : String(value ?? '')
    else if (field.kind === 'json')
      values[field.name] = value === undefined ? '' : JSON.stringify(value)
    else
      values[field.name] =
        value === null || value === undefined ? '' : String(value)
  }
  return values
}
