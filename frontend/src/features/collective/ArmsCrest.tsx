import { Quote, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Label, Muted, Text } from '@/components/typography'
import { Chip, Facts } from '@/features/cosmography/parts'
import { Ref } from '@/features/gatherings/parts'
import { ArmsShield } from './ArmsShield'
import { useNodeArms } from './api'
import { BEARERS, CHARGES, DIVISIONS, TINCTURES } from './labels'

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
              field={row.field}
              division={row.division}
              second={row.second}
              charge={row.charge}
              chargeTincture={row.charge_tincture}
              label={`Arms of ${name}`}
              size='lg'
            />
            <Label variant='overline'>Arms</Label>
          </Button>
        </PopoverTrigger>
        <PopoverContent className='flex w-80 flex-col gap-3'>
          <div className='flex min-w-0 items-center gap-3'>
            <ArmsShield
              field={row.field}
              division={row.division}
              second={row.second}
              charge={row.charge}
              chargeTincture={row.charge_tincture}
              label={`Arms of ${name}, drawn large`}
              size='lg'
            />
            <div className='flex min-w-0 flex-col gap-1'>
              <Text weight='semibold'>{row.blazon}</Text>
              <Chip icon={bearer.icon}>{bearer.label}</Chip>
            </div>
          </div>
          {row.motto ? (
            <div className='flex min-w-0 items-center gap-2'>
              <Quote
                className='size-icon-sm shrink-0 text-muted-foreground'
                aria-hidden='true'
              />
              <Text>{row.motto}</Text>
            </div>
          ) : (
            <Muted variant='caption'>These arms carry no words.</Muted>
          )}
          <Facts
            items={[
              ['Field', TINCTURES[row.field]],
              ['Division', DIVISIONS[row.division]],
              ['Charge', CHARGES[row.charge]],
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
