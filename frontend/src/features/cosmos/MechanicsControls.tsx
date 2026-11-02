import {
  BookOpen,
  Coins,
  Feather,
  Ghost,
  type LucideIcon,
  Scale,
  Sparkles,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Muted } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type ActionResponse } from './api'
import { useCosmicAction } from './useCosmicAction'

type MechanicRun = {
  id: string
  label: string
  icon: LucideIcon
  run: () => Promise<ActionResponse>
}

const RUNS: MechanicRun[] = [
  {
    id: 'knowledge:run',
    label: 'Let the masters work',
    icon: BookOpen,
    run: () => unwrap(api.POST('/api/actions/knowledge:run')),
  },
  {
    id: 'market:run',
    label: 'Open the markets',
    icon: Coins,
    run: () => unwrap(api.POST('/api/actions/market:run')),
  },
  {
    id: 'language:contact_run',
    label: 'Let tongues meet',
    icon: Feather,
    run: () => unwrap(api.POST('/api/actions/language:contact_run')),
  },
  {
    id: 'faith:native_run',
    label: 'Stir the old native gods',
    icon: Ghost,
    run: () => unwrap(api.POST('/api/actions/faith:native_run')),
  },
  {
    id: 'mechanics:weigh',
    label: 'Weigh unweighed resources and laws',
    icon: Scale,
    run: () => unwrap(api.POST('/api/actions/mechanics:weigh')),
  },
  {
    id: 'records:living_stats',
    label: 'Move mysteries, works and prophecies',
    icon: Sparkles,
    run: () => unwrap(api.POST('/api/actions/records:living_stats')),
  },
]

export function MechanicsControls() {
  const action = useCosmicAction({
    run: (call: () => Promise<ActionResponse>) => call(),
  })
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted>
        Each runs on its own at every epoch end; run one now to see its effect
        at once.
      </Muted>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {RUNS.map((item) => (
          <CosmicActionButton
            key={item.id}
            actionId={item.id}
            label={item.label}
            icon={item.icon}
            size='sm'
            pending={action.isPending}
            onRun={() => action.mutate(item.run)}
          />
        ))}
      </div>
    </div>
  )
}
