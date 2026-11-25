import { Badge } from '@/components/ui/badge'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { personTone } from './teamLook'

export function AuthorMark({
  name,
  verb = 'By',
}: {
  name: string | null | undefined
  verb?: string
}) {
  if (!name) return null
  return (
    <Badge variant='secondary' size='sm' data-domain='author-mark'>
      <AccountAvatar name={name} tone={personTone(name)} size='xs' />
      {`${verb} ${name}`}
    </Badge>
  )
}
