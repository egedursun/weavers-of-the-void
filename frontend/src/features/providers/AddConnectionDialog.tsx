import { type FormEvent, useState } from 'react'
import {
  ArrowLeft,
  ExternalLink,
  LoaderCircle,
  type LucideIcon,
  Plug,
} from 'lucide-react'
import { toast } from 'sonner'
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
import { FormRow, Medallion, ShowMore, useShowMore } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { TermsNote } from './TermsNote'
import { useAddConnection } from './api'
import { FAMILIES, FAMILY_LOOK } from './providerLook'
import {
  type ProviderConnection,
  type ProviderKindView,
  type ProviderScope,
} from './types'

const LABEL_MAX = 60
const ADDRESS_PATTERN = /^https?:\/\/\S+$/

const KINDS_SHOWN = 14

function FamilyKinds({
  offered,
  icon: Icon,
  onPick,
}: {
  offered: ProviderKindView[]
  icon: LucideIcon
  onPick: (kind: ProviderKindView) => void
}) {
  const page = useShowMore(offered, KINDS_SHOWN)
  return (
    <>
      <ul className='grid min-w-0 grid-cols-1 gap-1.5 sm:grid-cols-2'>
        {page.visible.map((kind) => (
          <li key={kind.kind}>
            <Button
              type='button'
              variant='outline'
              size='tile'
              disabled={kind.refusal !== null}
              disabledReason={kind.refusal ?? undefined}
              onClick={() => onPick(kind)}
            >
              <Icon aria-hidden='true' />
              <Text as='span' weight='semibold' truncate>
                {kind.label}
              </Text>
            </Button>
          </li>
        ))}
      </ul>
      <ShowMore state={page} noun={['provider', 'providers']} />
    </>
  )
}

function KindChooser({
  kinds,
  onPick,
}: {
  kinds: ProviderKindView[]
  onPick: (kind: ProviderKindView) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      {FAMILIES.map((family) => {
        const look = FAMILY_LOOK[family]
        const offered = kinds.filter((kind) => kind.family === family)
        const refusal =
          offered.find((kind) => kind.refusal !== null)?.refusal ?? null
        return (
          <section
            key={family}
            aria-label={look.label}
            className='flex min-w-0 flex-col gap-2'
          >
            <span className='flex min-w-0 items-center gap-2'>
              <Medallion icon={look.icon} tone={look.tone} size='sm' />
              <span className='flex min-w-0 flex-col'>
                <Label>{look.label}</Label>
                <Muted as='span' variant='caption'>
                  {refusal ?? look.lead}
                </Muted>
              </span>
            </span>
            <FamilyKinds offered={offered} icon={look.icon} onPick={onPick} />
          </section>
        )
      })}
    </div>
  )
}

export function AddConnectionDialog({
  scope,
  kinds,
  open,
  onClose,
  onAdded,
}: {
  scope: ProviderScope
  kinds: ProviderKindView[]
  open: boolean
  onClose: () => void
  onAdded: (connection: ProviderConnection, kind: ProviderKindView) => void
}) {
  const add = useAddConnection(scope)
  const [kind, setKind] = useState<ProviderKindView | null>(null)
  const [label, setLabel] = useState('')
  const [secret, setSecret] = useState('')
  const [address, setAddress] = useState('')
  const reset = () => {
    setKind(null)
    setLabel('')
    setSecret('')
    setAddress('')
  }
  const close = () => {
    reset()
    onClose()
  }
  const keyRequired = kind?.family === 'api'
  const problem =
    kind === null
      ? 'Choose what to connect.'
      : keyRequired && secret.trim() === ''
        ? 'Paste the key of this provider.'
        : kind.asks_address && !ADDRESS_PATTERN.test(address.trim())
          ? 'Give the address, starting with http:// or https://.'
          : null
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (kind === null || problem !== null || add.isPending) return
    add.mutate(
      {
        kind: kind.kind,
        label: label.trim(),
        secret: kind.asks_key ? secret.trim() : '',
        base_url: kind.asks_address ? address.trim() : '',
      },
      {
        onSuccess: (connection) => {
          toast.success(`${connection.label} is connected`)
          onAdded(connection, kind)
          close()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !add.isPending) close()
      }}
    >
      <DialogContent className='sm:max-w-2xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={Plug} />
            <DialogTitle>
              {kind === null ? 'Connect a provider' : `Connect ${kind.label}`}
            </DialogTitle>
          </div>
          <DialogDescription>
            {kind === null
              ? 'A subscription you log in to, a key of a cloud provider, or a server of your own.'
              : kind.family === 'subscription'
                ? 'Give it a name; logging in comes right after, in the official agent of the provider.'
                : 'The key is kept sealed on the server and is never shown again; only its last characters are.'}
          </DialogDescription>
        </DialogHeader>
        {kind === null ? (
          <KindChooser kinds={kinds} onPick={setKind} />
        ) : (
          <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
            {kind.terms !== null && <TermsNote terms={kind.terms} />}
            <FormRow
              label='Name of the connection'
              description='How it is listed in the chains.'
            >
              {(id) => (
                <Input
                  id={id}
                  value={label}
                  maxLength={LABEL_MAX}
                  placeholder={kind.label}
                  onChange={(event) => setLabel(event.target.value)}
                />
              )}
            </FormRow>
            {kind.asks_address && (
              <FormRow
                label='Address of the server'
                description='Where it answers, for example http://127.0.0.1:11434'
              >
                {(id) => (
                  <Input
                    id={id}
                    type='url'
                    value={address}
                    onChange={(event) => setAddress(event.target.value)}
                  />
                )}
              </FormRow>
            )}
            {kind.asks_key && (
              <FormRow
                label={keyRequired ? 'Key' : 'Key, if the server asks for one'}
                description='Pasted once, kept sealed.'
              >
                {(id) => (
                  <Input
                    id={id}
                    type='password'
                    autoComplete='off'
                    value={secret}
                    onChange={(event) => setSecret(event.target.value)}
                  />
                )}
              </FormRow>
            )}
            {kind.key_page !== '' && (
              <Button asChild variant='link' className='self-start'>
                <a href={kind.key_page} target='_blank' rel='noreferrer'>
                  <ExternalLink />
                  {`Get a key from ${kind.label}`}
                </a>
              </Button>
            )}
            <DialogFooter>
              <Button type='button' variant='outline' onClick={reset}>
                <ArrowLeft />
                Choose another
              </Button>
              <Button
                act={add}
                type='submit'
                disabled={problem !== null || add.isPending}
                disabledReason={problem ?? 'The connection is being made.'}
              >
                {add.isPending ? (
                  <LoaderCircle className='animate-spin motion-reduce:animate-none' />
                ) : (
                  <Plug />
                )}
                Connect
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
