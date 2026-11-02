import { AppearanceSettings } from './AppearanceSettings'
import { FeedSoundSettings } from './FeedSoundSettings'
import { GuideSettings } from './GuideSettings'

export function AppearancePage() {
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <AppearanceSettings />
      <FeedSoundSettings />
      <GuideSettings />
    </div>
  )
}
