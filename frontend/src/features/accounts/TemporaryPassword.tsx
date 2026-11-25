import { useState } from 'react'
import { Check, Copy, KeyRound, ShieldAlert } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { copyText } from '@/features/images/copyText'
import { AccountAvatar } from './AccountAvatar'
import { type Account } from './types'

export function TemporaryPassword({
  account,
  password,
  onDone,
}: {
  account: Pick<Account, 'display_name' | 'username' | 'avatar_tone'>
  password: string
  onDone: () => void
}) {
  const [copied, setCopied] = useState(false)
  return (
    <div
      className='flex min-w-0 flex-col gap-4'
      data-domain='temporary-password'
    >
      <div className='flex min-w-0 items-center gap-3 rounded-md surface-sheen p-3'>
        <AccountAvatar
          name={account.display_name}
          tone={account.avatar_tone}
          size='md'
        />
        <span className='flex min-w-0 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {account.display_name}
          </Text>
          <Muted as='span' variant='caption' className='font-mono' truncate>
            {`@${account.username}`}
          </Muted>
        </span>
      </div>
      <div className='flex min-w-0 flex-col gap-2 rounded-lg surface-framed p-4'>
        <span className='flex min-w-0 items-center gap-2'>
          <Medallion icon={KeyRound} tone='gold' size='sm' />
          <Label variant='gilded'>Temporary password</Label>
        </span>
        <span className='flex min-w-0 flex-wrap items-center gap-2 rounded-md surface-well px-3 py-2'>
          <Text
            as='span'
            weight='semibold'
            className='min-w-0 flex-1 font-mono break-all select-all'
            aria-label='The temporary password'
          >
            {password}
          </Text>
          <Button
            type='button'
            size='sm'
            variant={copied ? 'outline' : 'default'}
            onClick={() =>
              void copyText(password).then((done) => setCopied(done))
            }
          >
            {copied ? <Check /> : <Copy />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </span>
      </div>
      <Alert>
        <ShieldAlert />
        <AlertTitle>Shown only this once</AlertTitle>
        <AlertDescription>
          Hand it to {account.display_name} yourself. They sign in with it and
          must set their own password before anything else; the server keeps no
          readable copy, so if it is lost, reset the password again.
        </AlertDescription>
      </Alert>
      <Button
        type='button'
        onClick={onDone}
        variant={copied ? 'default' : 'outline'}
      >
        <Check />
        {copied ? 'Done, it is handed over' : 'Done'}
      </Button>
    </div>
  )
}
