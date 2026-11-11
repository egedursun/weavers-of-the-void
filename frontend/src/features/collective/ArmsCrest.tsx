import { Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Label, Muted, Text } from '@/components/typography'
import { Chip, Facts } from '@/features/cosmography/parts'
import { Ref } from '@/features/gatherings/parts'
import { Motto } from './ArmsPanels'
import { ArmsShield } from './ArmsShield'
import { useNodeArms } from './api'
import { BEARERS } from './labels'

export function ArmsCrest({ nodeId, name }: { nodeId: number; name: string }) {
  const arms = useNodeArms(nodeId)
  const row = arms.data
  if (!row) return null
  const bearer = BEARERS[row.holder_kind]
  return (
    <div className='shrink-0'>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant='ghost'
            size='figure'
            aria-label={`Arms of ${name}: ${row.blazon}`}
            className='transition-transform motion-safe:hover:scale-105'
          >
            <ArmsShield
              drawing={row.drawing}
              label={`Arms of ${name}`}
              size='lg'
            />
            <Label variant='overline'>Arms</Label>
          </Button>
        </PopoverTrigger>
        <PopoverContent className='flex max-h-144 w-96 flex-col gap-3 overflow-y-auto'>
          <div className='flex min-w-0 items-center gap-3'>
            <ArmsShield
              drawing={row.drawing}
              label={`Arms of ${name}, drawn large`}
              size='xl'
            />
            <div className='flex min-w-0 flex-col gap-1'>
              <Text weight='semibold'>{row.blazon}</Text>
              <Chip icon={bearer.icon}>{bearer.label}</Chip>
            </div>
          </div>
          <Motto motto={row.motto} />
          <Facts
            items={[
              [
                'Differenced from',
                <Ref key='parent' node={row.parent} empty='no parent' />,
              ],
              [
                'Quartered with',
                <Ref key='quartered' node={row.quartered} empty='no one' />,
              ],
              ['Borne since', `Epoch ${row.since_epoch}`],
            ]}
          />
          <Muted variant='caption'>
            <Shield className='size-icon-xs' aria-hidden='true' /> Change them
            in the Arms panel of this record.
          </Muted>
        </PopoverContent>
      </Popover>
    </div>
  )
}
