import { CloudFog, Heart, HeartCrack, Skull } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  IconStat,
  Portrait,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import { Label } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { STAT_SCALE } from '@/features/pantheon/constants'
import { REPUTATION_BADGE, REPUTATION_LABEL } from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { PassionsForm } from './PassionsForm'
import { type CreatorReputation } from './api'

export function ReputationGauges({
  love,
  fear,
  forgotten,
}: {
  love: number
  fear: number
  forgotten: number
}) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
      <StatBar
        label='Love'
        icon={Heart}
        value={love}
        max={STAT_SCALE}
        tone='success'
      />
      <StatBar
        label='Fear'
        icon={Skull}
        value={fear}
        max={STAT_SCALE}
        tone='destructive'
      />
      <StatBar
        label='Forgottenness'
        icon={CloudFog}
        value={forgotten}
        max={STAT_SCALE}
        tone='muted'
      />
    </div>
  )
}

export function ReputationPanel({
  reputation,
}: {
  reputation: CreatorReputation
}) {
  const sons = useSons()
  const sonOf = (sonId: number) =>
    (sons.data ?? []).find((view) => view.son.id === sonId)
  return (
    <Section
      title='Reputation and passions'
      description='How your sons see you, and what you are known to love.'
      surface='card'
      level={3}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label>In your sons' eyes</Label>
        <Badge variant={REPUTATION_BADGE[reputation.label]}>
          {REPUTATION_LABEL[reputation.label]}
        </Badge>
      </div>
      <ReputationGauges
        love={reputation.love}
        fear={reputation.fear}
        forgotten={reputation.forgotten}
      />
      {reputation.sons.length === 0 ? (
        <EmptyState
          icon={HeartCrack}
          size='compact'
          title='No son has an opinion yet'
          description='Sons form a view of their Creator as epochs pass.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <Paged items={reputation.sons} as='li'>
            {(son) => {
              const view = sonOf(son.son_id)
              return (
                <li
                  key={son.son_id}
                  className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'
                >
                  <Portrait
                    name={son.name}
                    src={mediaUrl(view?.cover)}
                    size='sm'
                    rarity={view?.son.rarity}
                  />
                  <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
                    <div className='flex min-w-0 items-center gap-2'>
                      <span className='min-w-0 flex-1 truncate'>
                        <EntityLink
                          kind='son'
                          id={String(son.son_id)}
                          rarity={view?.son.rarity}
                        >
                          {son.name}
                        </EntityLink>
                      </span>
                      <Badge size='sm' variant={REPUTATION_BADGE[son.label]}>
                        {REPUTATION_LABEL[son.label]}
                      </Badge>
                    </div>
                    <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                      <IconStat
                        icon={Heart}
                        tone='success'
                        label='Love'
                        value={son.love}
                      />
                      <IconStat
                        icon={Skull}
                        tone='danger'
                        label='Fear'
                        value={son.fear}
                      />
                      <IconStat
                        icon={CloudFog}
                        label='Forgotten'
                        value={son.forgotten}
                      />
                      {son.unanswered > 0 && (
                        <Badge size='sm' variant='warning'>
                          {plural(son.unanswered, 'unanswered prayer')}
                        </Badge>
                      )}
                    </div>
                  </div>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      <PassionsForm reputation={reputation} />
    </Section>
  )
}
