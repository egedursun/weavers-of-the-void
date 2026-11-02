import { Link } from '@tanstack/react-router'
import { Check, Circle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  ONBOARDING_HIDE_AFTER_EPOCH,
  ONBOARDING_STEPS,
  type OnboardingStep,
  useOnboarding,
} from './onboardingStore'

type StepCopy = {
  title: string
  detail: string
  to:
    | '/pantheon'
    | '/map'
    | '/prayers'
    | '/chronicle'
    | '/settings/world-rules'
    | '/epoch'
}

const STEP_COPY: Record<OnboardingStep, StepCopy> = {
  son: {
    title: 'Open the card of a son',
    detail: 'Each son is an agent with his own powers, mood and plans.',
    to: '/pantheon',
  },
  map: {
    title: 'Look at the map',
    detail: 'Regions, peoples and wars of the first world.',
    to: '/map',
  },
  prayers: {
    title: 'Read the prayers',
    detail: 'Sons and mortals ask you for things; answers shape loyalty.',
    to: '/prayers',
  },
  chronicle: {
    title: 'Read the chronicle',
    detail: 'Fate writes the history of each epoch here.',
    to: '/chronicle',
  },
  rules: {
    title: 'Glance at the world rules',
    detail: 'Every cost and threshold of the world can be tuned.',
    to: '/settings/world-rules',
  },
  epoch: {
    title: 'Complete the first epoch',
    detail: 'The sons act, the world turns, and Fate judges.',
    to: '/epoch',
  },
}

type FirstEpochsGuideProps = {
  epoch: number
}

export function FirstEpochsGuide({ epoch }: FirstEpochsGuideProps) {
  const done = useOnboarding((state) => state.done)
  const dismissed = useOnboarding((state) => state.dismissed)
  const dismiss = useOnboarding((state) => state.dismiss)
  if (dismissed || epoch > ONBOARDING_HIDE_AFTER_EPOCH) return null
  const finished = ONBOARDING_STEPS.filter((step) => done.includes(step)).length
  return (
    <Section
      title='The first epochs'
      description={`${finished} of ${ONBOARDING_STEPS.length} steps taken. You can reopen this guide from Settings.`}
      surface='card'
      actions={
        <Button variant='outline' size='sm' onClick={dismiss}>
          Got it, hide
        </Button>
      }
    >
      <ol className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3'>
        {ONBOARDING_STEPS.map((step) => {
          const copy = STEP_COPY[step]
          const complete = done.includes(step)
          const Icon = complete ? Check : Circle
          return (
            <li key={step} className='flex min-w-0 items-start gap-3'>
              <Icon
                aria-hidden='true'
                className={
                  complete
                    ? 'size-icon-md shrink-0 text-success'
                    : 'size-icon-md shrink-0 text-muted-foreground'
                }
              />
              <div className='flex min-w-0 flex-col gap-0.5'>
                <Text weight='medium'>
                  <Link
                    to={copy.to}
                    className='text-primary underline-offset-4 hover:underline'
                  >
                    {copy.title}
                  </Link>
                </Text>
                <Muted variant='caption'>
                  {complete ? 'Done.' : copy.detail}
                </Muted>
              </div>
            </li>
          )
        })}
      </ol>
    </Section>
  )
}
