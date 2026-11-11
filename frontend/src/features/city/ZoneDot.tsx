import { cn } from '@/lib/utils'
import { type ZoneSpec } from './labels'

export function Dot({ fill }: { fill: string }) {
  return (
    <svg
      aria-hidden='true'
      viewBox='0 0 10 10'
      className='size-icon-xs shrink-0'
    >
      <circle cx='5' cy='5' r='4.5' className={cn(fill)} />
    </svg>
  )
}

export function ZoneDot({ spec }: { spec: ZoneSpec }) {
  return <Dot fill={spec.fill} />
}
