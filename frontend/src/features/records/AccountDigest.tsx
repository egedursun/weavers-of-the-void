import { History, ScrollText } from 'lucide-react'
import { EmptyState, EntityLink, LoadingBlock } from '@/components/domain'
import { Muted } from '@/components/typography'
import { ChangeList, Steps } from './EventPage'
import { useEventAccount } from './api'
import { useBlocked } from './useBlocked'

export function AccountDigest({ incidentId }: { incidentId: number }) {
  const account = useEventAccount(incidentId)
  const blocked = useBlocked()
  if (account.isPending)
    return <LoadingBlock label='Reading its steps and changes' />
  if (account.isError)
    return (
      <EmptyState
        icon={ScrollText}
        size='inline'
        title='Its account could not be read'
        description={account.error.message}
      />
    )
  return (
    <div
      data-surface='AccountDigest'
      className='@container/event flex min-w-0 flex-col gap-2'
    >
      <EntityLink kind='incident' id={String(incidentId)} showIcon>
        Open the full account
      </EntityLink>
      <Muted variant='caption'>How it unfolded</Muted>
      <Steps account={account.data} blocked={blocked} />
      <Muted variant='caption'>
        <History aria-hidden='true' className='inline size-icon-xs' /> What it
        changed
      </Muted>
      <ChangeList changes={account.data.changes} blocked={blocked} />
    </div>
  )
}
