import { type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'
import { PackFace } from './PackArt'

export function SealedPack({
  className,
  ...shell
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('sealed-pack', className)} {...shell}>
      <div className='sealed-pack-body'>
        <PackFace still />
      </div>
    </div>
  )
}
