import { type ReactNode } from 'react'
import {
  Eye,
  Globe,
  HandHeart,
  Hourglass,
  type LucideIcon,
  MessageCircleOff,
  Moon,
  ShieldOff,
  Skull,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { formatDecimal } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import {
  DomainGlyph,
  EntityLink,
  IconStat,
  Portrait,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { type ForeignGodRecord } from '@/features/pantheon/api'
import {
  FOREIGN_STATUS_BADGE,
  FOREIGN_STATUS_LABEL,
  useLabels,
} from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { AttitudeBar } from './AttitudeBar'

type ForeignGodStatus = components['schemas']['ForeignGodStatus']

const FOREIGN_STATUS_ICON: Record<ForeignGodStatus, LucideIcon> = {
  awake: Eye,
  asleep: Moon,
  defeated: ShieldOff,
  dead: Skull,
}

const STATUS_BORDER: Record<ForeignGodStatus, string> = {
  awake: 'border-warning/40',
  asleep: '',
  defeated: 'opacity-80',
  dead: 'border-destructive/30 opacity-80',
}

export function ForeignGodCard({
  god,
  worldName,
  actions,
}: {
  god: ForeignGodRecord
  worldName?: string | null
  actions?: ReactNode
}) {
  const { domain } = useLabels()
  const StatusIcon = FOREIGN_STATUS_ICON[god.status]
  return (
    <Card
      data-foreign-god={god.id}
      data-status={god.status}
      className={cn('h-full', STATUS_BORDER[god.status])}
    >
      <CardHeader>
        <div className='flex min-w-0 items-start gap-3'>
          <Portrait
            name={god.name}
            src={mediaUrl(god.cover)}
            size='lg'
            shape='square'
            rarity='mythic'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
            <div className='flex min-w-0 items-start gap-2'>
              <span className='min-w-0 flex-1 truncate'>
                <EntityLink kind='foreign-god' id={String(god.id)}>
                  {god.name}
                </EntityLink>
              </span>
              <Badge size='sm' variant={FOREIGN_STATUS_BADGE[god.status]}>
                <StatusIcon />
                {FOREIGN_STATUS_LABEL[god.status]}
              </Badge>
            </div>
            {god.title && (
              <Muted variant='caption' truncate={2}>
                {god.title}
              </Muted>
            )}
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {worldName && (
                <Badge size='sm' variant='info'>
                  <Globe />
                  {worldName}
                </Badge>
              )}
              <Badge size='sm' variant='outline'>
                <DomainGlyph domain={god.domain_primary} />
                {domain(god.domain_primary)}
              </Badge>
              {god.domain_secondary && (
                <Badge size='sm' variant='outline'>
                  <DomainGlyph domain={god.domain_secondary} />
                  {domain(god.domain_secondary)}
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className='flex flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <IconStat
            icon={Zap}
            tone='warning'
            label='Power'
            hint='Raises the cost of draining or killing this god'
            value={god.power}
          />
          <IconStat
            icon={HandHeart}
            tone='gold'
            label='Faith'
            hint='Worship gathered from mortals'
            value={formatDecimal(god.faith, 1)}
          />
          {god.status === 'asleep' && (
            <IconStat
              icon={Hourglass}
              tone='info'
              label='Awakening pressure'
              hint='The god wakes when its believers press hard enough'
              value={god.awakening_pressure}
            />
          )}
          {!god.contacted && (
            <Badge size='sm' variant='outline'>
              <MessageCircleOff />
              No contact yet
            </Badge>
          )}
        </div>
        <AttitudeBar stance={god.stance} showText={false} />
        {god.description && (
          <Muted variant='caption' truncate={3}>
            {god.description}
          </Muted>
        )}
      </CardContent>
      {actions && (
        <CardFooter className='mt-auto flex-wrap gap-2 border-t'>
          {actions}
        </CardFooter>
      )}
    </Card>
  )
}
