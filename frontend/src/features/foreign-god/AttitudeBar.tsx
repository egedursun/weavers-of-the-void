import { Label, Muted, Stat } from '@/components/typography'
import { DivergingBar } from '@/features/pantheon/DivergingBar'
import { useRuleLookup } from '@/features/pantheon/gate'
import { signed } from '@/features/pantheon/relations'
import { attitudeBand } from './attitude'

export function AttitudeBar({
  stance,
  showText = true,
}: {
  stance: number
  showText?: boolean
}) {
  const rule = useRuleLookup()
  const band = attitudeBand(
    stance,
    rule('pantheon.son_war_max_attitude'),
    rule('pantheon.foreign_friend_min_attitude')
  )
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 items-baseline justify-between gap-2'>
        <Label>Enemy</Label>
        <span className='flex min-w-0 items-baseline gap-1.5'>
          <Label>{band.label}</Label>
          <Stat value={signed(stance)} />
        </span>
        <Label>Friend</Label>
      </div>
      <DivergingBar value={stance} label='Attitude to the pantheon' />
      {showText && <Muted variant='caption'>{band.text}</Muted>}
    </div>
  )
}
