import { Eye, Heart, RefreshCw, Skull } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { ReputationGauges } from '@/features/creator/ReputationPanel'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type SonRecord } from '@/features/pantheon/api'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  REPUTATION_BADGE,
  REPUTATION_LABEL,
  plural,
} from '@/features/pantheon/labels'
import { type SonDetail } from './api'

const RULE_MISSING = 'The world rule for this push is not loaded.'

type Nudge = { love: number; fear: number; forgotten: number }

export function SonReputation({
  son,
  reputation,
}: {
  son: SonRecord
  reputation: SonDetail['reputation']
}) {
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const cap = rule('reputation.manual_push_cap')
  const loveStep = rule('reputation.manual_love_click')
  const fearStep = rule('reputation.manual_fear_click')
  const neglectStep = rule('reputation.manual_neglect_click')
  const keep = rule('reputation.manual_push_keep_pct')
  const path = { params: { path: { son_id: son.id } } }
  const nudge = useGodAction({
    run: (body: Nudge) =>
      unwrap(
        api.POST('/api/sons/{son_id}/reputation-nudge', { ...path, body })
      ),
  })
  const drift = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/reputation:drift', { body: { son_id: son.id } })
      ),
    success: 'His view of you was recomputed',
  })
  if (!reputation || son.status === 'dead') return null
  const atCap = (value: number) =>
    cap !== undefined && Math.abs(value) >= cap
      ? `Your push is at its cap (${cap}); it fades each epoch.`
      : null
  const pushes = [son.manual_love, son.manual_fear, son.manual_forgotten]
  return (
    <Section title='How he sees his father' surface='card' level={3}>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Badge variant={REPUTATION_BADGE[reputation.label]}>
          {REPUTATION_LABEL[reputation.label]}
        </Badge>
        {reputation.unanswered > 0 && (
          <Badge size='sm' variant='warning'>
            {plural(reputation.unanswered, 'unanswered prayer')}
          </Badge>
        )}
        <Badge
          size='sm'
          variant='outline'
        >{`Last contact: Epoch ${reputation.last_contact}`}</Badge>
      </div>
      <ReputationGauges
        love={reputation.love}
        fear={reputation.fear}
        forgotten={reputation.forgotten}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <ActionButton
          label='Win his heart'
          icon={Heart}
          blocked={
            reason() ??
            atCap(son.manual_love) ??
            (loveStep === undefined ? RULE_MISSING : null)
          }
          pending={nudge.isPending}
          onRun={() =>
            nudge.mutate({ love: loveStep ?? 0, fear: 0, forgotten: 0 })
          }
        />
        <ActionButton
          label='Spread fear'
          icon={Skull}
          blocked={
            reason() ??
            atCap(son.manual_fear) ??
            (fearStep === undefined ? RULE_MISSING : null)
          }
          pending={nudge.isPending}
          onRun={() =>
            nudge.mutate({ love: 0, fear: fearStep ?? 0, forgotten: 0 })
          }
        />
        <ActionButton
          label='Remind him of you'
          icon={Eye}
          blocked={
            reason() ??
            atCap(son.manual_forgotten) ??
            (neglectStep === undefined ? RULE_MISSING : null)
          }
          pending={nudge.isPending}
          onRun={() =>
            nudge.mutate({ love: 0, fear: 0, forgotten: -(neglectStep ?? 0) })
          }
        />
        <ActionButton
          label='Recompute now'
          icon={RefreshCw}
          variant='ghost'
          blocked={reason()}
          pending={drift.isPending}
          onRun={() => drift.mutate()}
        />
      </div>
      <Muted variant='caption'>
        {pushes.some((value) => value !== 0)
          ? `Your nudges: love ${son.manual_love}, fear ${son.manual_fear}, forgottenness ${son.manual_forgotten}${keep !== undefined ? `; ${keep}% of each remains every epoch` : ''}.`
          : 'Nudges fade each epoch; his view also changes with your deeds.'}
      </Muted>
    </Section>
  )
}
