import { type FormEvent, useEffect, useState } from 'react'
import {
  CornerDownLeft,
  ExternalLink,
  KeyRound,
  LoaderCircle,
  LogIn,
  Send,
  Square,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatSince } from '@/lib/format'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  CodeBlock,
  CopyButton,
  FormRow,
  Medallion,
  PagedList,
} from '@/components/domain'
import { Label, Muted, Stat } from '@/components/typography'
import { TermsNote } from './TermsNote'
import {
  forgetLogin,
  useAnswerLogin,
  useLogin,
  useStartLogin,
  useStopLogin,
} from './api'
import { LOGIN_LOOK } from './providerLook'
import { type ProviderConnection } from './types'

const ANSWER_MAX = 2000

const LINKS_SHOWN = 3

export function LoginDialog({
  workspaceId,
  connection,
  terms,
  open,
  onClose,
}: {
  workspaceId: number
  connection: ProviderConnection
  terms: string | null
  open: boolean
  onClose: () => void
}) {
  const login = useLogin(workspaceId, connection.id, open)
  const start = useStartLogin(workspaceId, connection.id)
  const answer = useAnswerLogin(workspaceId, connection.id)
  const stop = useStopLogin(workspaceId, connection.id)
  const [text, setText] = useState('')
  const view = login.data ?? null
  const running = view?.state === 'running'
  const succeeded = view?.state === 'succeeded'
  useEffect(() => {
    if (open && succeeded) {
      toast.success(`${connection.label} is logged in and ready to think`)
      forgetLogin(workspaceId, connection.id)
      onClose()
    }
  }, [open, succeeded, connection.label, connection.id, workspaceId, onClose])
  const send = (event: FormEvent) => {
    event.preventDefault()
    if (!running || text.trim() === '' || answer.isPending) return
    answer.mutate(text.trim(), {
      onSuccess: () => setText(''),
      onError: (error) => toast.error(error.message),
    })
  }
  const pressEnter = () =>
    answer.mutate('', { onError: (error) => toast.error(error.message) })
  const begin = () =>
    start.mutate(undefined, { onError: (error) => toast.error(error.message) })
  const look = view ? LOGIN_LOOK[view.state] : null
  const StateIcon = look?.icon ?? KeyRound
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose()
      }}
    >
      <DialogContent className='sm:max-w-2xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={LogIn} />
            <DialogTitle>{`Log in to ${connection.label}`}</DialogTitle>
          </div>
          <DialogDescription>
            The official agent of the provider runs its own login here on the
            server. Open the page it gives, sign in, and paste back a code when
            it asks for one.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-4'>
          {terms !== null && <TermsNote terms={terms} />}
          {view && look && (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge variant={look.variant} size='sm'>
                <StateIcon
                  className={
                    running
                      ? 'animate-spin motion-reduce:animate-none'
                      : undefined
                  }
                />
                {look.label}
              </Badge>
              <Muted as='span' variant='caption'>
                {view.ended_at
                  ? `Ended ${formatSince(view.ended_at)}`
                  : `Started ${formatSince(view.started_at)}`}
              </Muted>
            </div>
          )}
          {view?.note && (
            <Alert variant='destructive'>
              <AlertTitle>The login did not finish</AlertTitle>
              <AlertDescription>{view.note}</AlertDescription>
            </Alert>
          )}
          {running && view?.code && (
            <div className='flex min-w-0 flex-col items-center gap-1 rounded-md surface-well p-4'>
              <Label>The code to enter</Label>
              <span className='flex min-w-0 items-center gap-2'>
                <Stat
                  value={view.code}
                  size='kpi'
                  tone='primary'
                  className='font-mono'
                />
                <CopyButton text={view.code} label='Copy the code' />
              </span>
            </div>
          )}
          {running && view && view.links.length > 0 && (
            <PagedList
              items={view.links}
              initial={LINKS_SHOWN}
              noun={['link', 'links']}
              as='div'
              className='flex min-w-0 flex-wrap gap-2'
              itemKey={(link) => link}
            >
              {(link, index) => (
                <Button asChild variant={index === 0 ? 'default' : 'outline'}>
                  <a href={link} target='_blank' rel='noreferrer'>
                    <ExternalLink />
                    {index === 0
                      ? 'Open the sign-in page'
                      : `Open link ${index + 1}`}
                  </a>
                </Button>
              )}
            </PagedList>
          )}
          {view && (
            <CodeBlock
              label='What the agent says'
              text={view.output}
              empty='The agent has said nothing yet.'
            />
          )}
          {running && (
            <form className='flex min-w-0 flex-col gap-2' onSubmit={send}>
              <FormRow
                label='Paste a code back'
                description='Only when the agent asks for one. Press Enter answers a prompt that waits for the key alone.'
              >
                {(id) => (
                  <>
                    <Input
                      id={id}
                      value={text}
                      maxLength={ANSWER_MAX}
                      autoComplete='off'
                      className='min-w-0 flex-1 basis-60'
                      onChange={(event) => setText(event.target.value)}
                    />
                    <Button
                      act={answer}
                      type='submit'
                      variant='outline'
                      disabled={text.trim() === '' || answer.isPending}
                      disabledReason={
                        text.trim() === ''
                          ? 'Paste the code first.'
                          : 'Sending the code.'
                      }
                    >
                      <Send />
                      Send
                    </Button>
                    <Button
                      act={answer}
                      type='button'
                      variant='ghost'
                      disabled={answer.isPending}
                      disabledReason='Sending to the agent.'
                      onClick={pressEnter}
                    >
                      <CornerDownLeft />
                      Press Enter
                    </Button>
                  </>
                )}
              </FormRow>
            </form>
          )}
        </div>
        <DialogFooter>
          {running ? (
            <Button
              act={stop}
              type='button'
              variant='outline'
              disabled={stop.isPending}
              disabledReason='Stopping the login.'
              onClick={() =>
                stop.mutate(undefined, {
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              <Square />
              Stop the login
            </Button>
          ) : (
            <Button type='button' variant='outline' onClick={onClose}>
              Close
            </Button>
          )}
          <Button
            act={start}
            type='button'
            disabled={running || start.isPending}
            disabledReason={
              running ? 'The login is under way.' : 'Starting the login.'
            }
            onClick={begin}
          >
            {start.isPending ? (
              <LoaderCircle className='animate-spin motion-reduce:animate-none' />
            ) : (
              <LogIn />
            )}
            {view ? 'Start again' : 'Start logging in'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
