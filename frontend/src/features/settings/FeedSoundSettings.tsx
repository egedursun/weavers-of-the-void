import {
  AudioLines,
  BellRing,
  CloudLightning,
  DoorOpen,
  Ghost,
  Globe2,
  Landmark,
  type LucideIcon,
  Radio,
  Sailboat,
  Sparkles,
  Sprout,
  Swords,
  Volume2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Section } from '@/components/domain'
import { SettingGroup, SwitchRow } from '@/components/domain/SettingsKit'
import {
  type FeedCategory,
  FEED_CATEGORIES,
  FEED_CATEGORY_LABEL,
} from '@/features/feed/feedModel'
import { playTone, startDrone, stopDrone } from '@/features/feed/feedSound'
import { useFeedPreferences } from '@/features/feed/feedStore'
import { useFeedDock } from '@/features/feed/useFeedDock'

const CATEGORY_ICON: Record<FeedCategory, LucideIcon> = {
  voyage: Sailboat,
  gate: DoorOpen,
  leak: Ghost,
  war: Swords,
  disaster: CloudLightning,
  sky: Sparkles,
  life: Sprout,
  civilization: Landmark,
  world: Globe2,
}

export function FeedSoundSettings() {
  const preferences = useFeedPreferences()
  const dock = useFeedDock()
  return (
    <Section
      title='Live feed and sound'
      description='Remembered in this browser.'
      surface='card'
      icon={AudioLines}
      tone='verdigris'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-3'>
        <SwitchRow
          icon={Radio}
          tone='verdigris'
          label='Live feed open'
          description='The event feed slides in from the right.'
          checked={dock.open}
          onChange={dock.setOpen}
        />
        <SwitchRow
          icon={AudioLines}
          tone='verdigris'
          label='Ambient sound'
          description='A low hum; it starts after your next click.'
          checked={preferences.ambient}
          onChange={(checked) => {
            preferences.setAmbient(checked)
            if (checked) startDrone()
            else stopDrone()
          }}
        />
        <SwitchRow
          icon={BellRing}
          tone='verdigris'
          label='Feed sounds'
          description='Each kind of world event plays a short tone.'
          checked={preferences.sounds}
          onChange={preferences.setSounds}
        />
      </div>
      {preferences.sounds && (
        <SettingGroup
          label='Which events make a sound'
          description='Listen to each tone before you choose.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3'>
            {FEED_CATEGORIES.map((category) => (
              <SwitchRow
                key={category}
                icon={CATEGORY_ICON[category]}
                tone='info'
                label={FEED_CATEGORY_LABEL[category]}
                checked={!preferences.muted.includes(category)}
                onChange={() => preferences.toggleMuted(category)}
                extra={
                  <Button
                    variant='ghost'
                    size='icon-sm'
                    onClick={() => playTone(category, true)}
                    aria-label={`Listen to ${FEED_CATEGORY_LABEL[category]}`}
                    title='Listen'
                  >
                    <Volume2 />
                  </Button>
                }
              />
            ))}
          </div>
        </SettingGroup>
      )}
    </Section>
  )
}
