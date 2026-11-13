import { useState } from 'react'
import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Medallion } from '@/components/domain'
import { Muted, SectionTitle, Text } from '@/components/typography'
import { useRuleValue } from '@/features/world-rules/api'
import { GenesisPreview } from './GenesisPreview'
import { GenesisStepper } from './GenesisStepper'
import { CreatorStep, SonsStep, TemplateStep, WorldStep } from './WizardSteps'
import { useStartGenesis, useWizardOptions } from './api'
import {
  STEP_TITLE,
  WIZARD_STEPS,
  type WizardDefaults,
  type WizardDraft,
  type WizardStep,
  applyTemplate,
  initialDraft,
  stepProblem,
  toRequest,
} from './wizardModel'
import { type StepProps } from './wizardTypes'
import { STEP_HINT, STEP_ICON } from './wizardVisuals'

const FALLBACK_DEFAULTS: WizardDefaults = {
  magic: 50,
  danger: 50,
  peoples: 2,
}
const FALLBACK_PEOPLES_MAX = 5

type GenesisWizardProps = {
  llmEnabled: boolean
}

export function GenesisWizard({ llmEnabled }: GenesisWizardProps) {
  const options = useWizardOptions()
  const magic = useRuleValue('setup_wizard.magic')
  const danger = useRuleValue('setup_wizard.danger')
  const peoples = useRuleValue('setup_wizard.peoples')
  const peoplesMax =
    useRuleValue('setup_wizard.peoples_max') ?? FALLBACK_PEOPLES_MAX
  const defaults: WizardDefaults = {
    magic: magic ?? FALLBACK_DEFAULTS.magic,
    danger: danger ?? FALLBACK_DEFAULTS.danger,
    peoples: peoples ?? FALLBACK_DEFAULTS.peoples,
  }
  const start = useStartGenesis()
  const [stepIndex, setStepIndex] = useState(0)
  const [draft, setDraft] = useState<WizardDraft | null>(null)
  const current = draft ?? initialDraft(defaults)
  const step: WizardStep = WIZARD_STEPS[stepIndex]
  const problem = stepProblem(step, current, peoplesMax)
  const last = stepIndex === WIZARD_STEPS.length - 1
  const update = (next: Partial<WizardDraft>) =>
    setDraft({ ...current, ...next })
  const reachable = (index: number) =>
    WIZARD_STEPS.slice(0, index).every(
      (item) => stepProblem(item, current, peoplesMax) === null
    )
  const go = (index: number) => {
    setStepIndex(index)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (options.isPending)
    return (
      <div className='grid min-w-0 grid-cols-1 gap-6 lg:grid-cols-3'>
        <Skeleton className='h-160 w-full lg:col-span-2' />
        <Skeleton className='h-96 w-full' />
      </div>
    )
  if (options.isError)
    return <Text tone='destructive'>{options.error.message}</Text>

  const props: StepProps = {
    draft: current,
    update,
    options: options.data,
    peoplesMax,
  }
  const onPick = (key: string | null) => {
    const template =
      key === null || current.template === key
        ? null
        : (options.data.templates.find((item) => item.key === key) ?? null)
    setDraft(applyTemplate(current, template, defaults))
  }
  const submit = () => {
    const blocking = WIZARD_STEPS.map((item) =>
      stepProblem(item, current, peoplesMax)
    ).find(Boolean)
    if (blocking) {
      toast.error(blocking)
      return
    }
    start.mutate(
      toRequest(current, current.firstSons ?? options.data.first_sons.default),
      {
        onSuccess: () => toast.success('The world is being thought'),
        onError: (error) => toast.error(error.message),
      }
    )
  }
  const createBlocked = !llmEnabled
    ? 'Genesis needs the language model, which is turned off'
    : start.isPending
      ? 'The world is being thought'
      : null

  return (
    <div
      data-onboarding='wizard'
      className='grid min-w-0 grid-cols-1 items-start gap-6 lg:grid-cols-3'
    >
      <section
        aria-label='Genesis wizard'
        className='flex min-w-0 flex-col gap-6 rounded-xl border bg-card p-4 shadow-sm sm:p-6 lg:col-span-2'
      >
        <GenesisStepper current={stepIndex} reachable={reachable} onPick={go} />
        <div className='flex min-w-0 items-center gap-3'>
          <Medallion icon={STEP_ICON[step]} />
          <div className='flex min-w-0 flex-col'>
            <SectionTitle level={2}>{STEP_TITLE[step]}</SectionTitle>
            <Muted variant='caption'>{STEP_HINT[step]}</Muted>
          </div>
        </div>
        {step === 'template' && <TemplateStep {...props} onPick={onPick} />}
        {step === 'creator' && <CreatorStep {...props} />}
        {step === 'world' && <WorldStep {...props} />}
        {step === 'review' && <SonsStep {...props} />}
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-3 border-t pt-4'>
          <Button
            variant='outline'
            disabled={stepIndex === 0}
            disabledReason='This is the first step'
            onClick={() => go(stepIndex - 1)}
          >
            <ArrowLeft />
            Back
          </Button>
          <div className='flex min-w-0 flex-1 flex-col items-center'>
            <Muted variant='caption'>{`Step ${stepIndex + 1} of ${WIZARD_STEPS.length}`}</Muted>
            {problem && (
              <Text variant='caption' tone='warning' role='status' truncate>
                {problem}
              </Text>
            )}
          </div>
          {last ? (
            <Button
              size='lg'
              disabled={createBlocked !== null}
              disabledReason={createBlocked ?? undefined}
              onClick={submit}
              className='shadow-lg shadow-primary/25'
            >
              <Sparkles />
              Create the world
            </Button>
          ) : (
            <Button
              disabled={problem !== null}
              disabledReason={problem ?? ''}
              onClick={() => go(stepIndex + 1)}
            >
              {`Next: ${STEP_TITLE[WIZARD_STEPS[stepIndex + 1]]}`}
              <ArrowRight />
            </Button>
          )}
        </div>
      </section>
      <div className='min-w-0 lg:sticky lg:top-6'>
        <GenesisPreview
          draft={current}
          options={options.data}
          peoplesMax={peoplesMax}
        />
      </div>
    </div>
  )
}
