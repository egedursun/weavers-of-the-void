import { Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AccountAvatar } from './AccountAvatar'
import { AVATAR_TONES } from './accountLook'
import { type AvatarTone } from './types'

const TONES = Object.keys(AVATAR_TONES) as AvatarTone[]

export function TonePicker({
  name,
  value,
  onChange,
  disabled,
}: {
  name: string
  value: AvatarTone
  onChange: (tone: AvatarTone) => void
  disabled: boolean
}) {
  return (
    <div
      role='radiogroup'
      aria-label='Avatar tone'
      className='flex min-w-0 flex-wrap gap-1.5'
    >
      {TONES.map((tone) => {
        const chosen = tone === value
        return (
          <Button
            key={tone}
            type='button'
            variant='outline'
            size='figure'
            role='radio'
            aria-checked={chosen}
            aria-label={AVATAR_TONES[tone]}
            disabled={disabled}
            disabledReason='The profile is being saved.'
            onClick={() => onChange(tone)}
            className='relative'
          >
            <AccountAvatar name={name || '?'} tone={tone} size='sm' />
            {chosen && (
              <Check
                aria-hidden='true'
                className='absolute end-1 top-1 size-icon-sm text-primary'
              />
            )}
          </Button>
        )
      })}
    </div>
  )
}
