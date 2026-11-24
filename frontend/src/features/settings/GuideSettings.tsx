import { Compass, Keyboard, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Section } from '@/components/domain'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { useOnboarding } from '@/features/onboarding/onboardingStore'

export function GuideSettings() {
  const reopen = useOnboarding((state) => state.reopen)
  const dismissed = useOnboarding((state) => state.dismissed)
  const entryStack = useEntryStack()
  return (
    <Section
      title='Guide and shortcuts'
      description='The first-epochs guide sits at the top of the overview. If you hid it, bring it back here. Press ? anywhere for shortcuts and terms.'
      surface='card'
      icon={Compass}
      tone='info'
    >
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          variant='outline'
          disabled={!dismissed}
          disabledReason='The guide is already shown'
          onClick={() => {
            reopen()
            toast.success('The guide is back on the overview')
          }}
        >
          <RotateCcw />
          Show the guide again
        </Button>
        <Button
          variant='outline'
          onClick={() => void entryStack.open({ kind: 'help' })}
        >
          <Keyboard />
          Shortcuts and terms
        </Button>
      </div>
    </Section>
  )
}
