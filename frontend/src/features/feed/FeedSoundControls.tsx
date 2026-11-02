import { AudioWaveform, Volume2, VolumeOff } from 'lucide-react'
import { Toggle } from '@/components/ui/toggle'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { startDrone, stopDrone } from './feedSound'
import { useFeedPreferences } from './feedStore'

export function FeedSoundControls() {
  const sounds = useFeedPreferences((state) => state.sounds)
  const ambient = useFeedPreferences((state) => state.ambient)
  const setSounds = useFeedPreferences((state) => state.setSounds)
  const setAmbient = useFeedPreferences((state) => state.setAmbient)
  return (
    <div className='flex shrink-0 items-center gap-1'>
      <Tooltip>
        <TooltipTrigger asChild>
          <Toggle
            size='sm'
            variant='outline'
            pressed={sounds}
            onPressedChange={setSounds}
            aria-label='Feed sounds'
          >
            {sounds ? <Volume2 /> : <VolumeOff />}
          </Toggle>
        </TooltipTrigger>
        <TooltipContent>
          {sounds ? 'World events play a tone' : 'Feed sounds are off'}
        </TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Toggle
            size='sm'
            variant='outline'
            pressed={ambient}
            onPressedChange={(next) => {
              setAmbient(next)
              if (next) startDrone()
              else stopDrone()
            }}
            aria-label='Ambient sound'
          >
            <AudioWaveform />
          </Toggle>
        </TooltipTrigger>
        <TooltipContent>
          {ambient ? 'A low hum fills the void' : 'Ambient sound is off'}
        </TooltipContent>
      </Tooltip>
    </div>
  )
}
