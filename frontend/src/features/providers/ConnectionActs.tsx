import { type FormEvent, useState } from 'react'
import { Globe, KeyRound, LoaderCircle, PenLine, Save } from 'lucide-react'
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
import { ConfirmDialog, FormRow, Medallion } from '@/components/domain'
import { type ConnectionAct } from './ConnectionCard'
import { useEditConnection, useLogOut, useRemoveConnection } from './api'
import {
  type ConnectionChange,
  type ProviderConnection,
  type ProviderScope,
} from './types'

const LABEL_MAX = 60
const ADDRESS_PATTERN = /^https?:\/\/\S+$/

export type PendingAct = { act: ConnectionAct; connection: ProviderConnection }

type FieldAct = 'rename' | 'key' | 'address'

const FIELD_LOOK: Record<
  FieldAct,
  { title: string; label: string; icon: typeof PenLine; done: string }
> = {
  rename: {
    title: 'Rename',
    label: 'Name of the connection',
    icon: PenLine,
    done: 'The connection is renamed',
  },
  key: {
    title: 'Replace the key of',
    label: 'The new key',
    icon: KeyRound,
    done: 'The new key is sealed',
  },
  address: {
    title: 'Change the address of',
    label: 'Address of the server',
    icon: Globe,
    done: 'The address is changed',
  },
}

function fieldOf(act: ConnectionAct): FieldAct | null {
  return act === 'rename' || act === 'key' || act === 'address' ? act : null
}

function EditDialog({
  scope,
  field,
  connection,
  onDone,
}: {
  scope: ProviderScope
  field: FieldAct | null
  connection: ProviderConnection | null
  onDone: () => void
}) {
  const edit = useEditConnection(scope)
  const [value, setValue] = useState<string | null>(null)
  const look = field ? FIELD_LOOK[field] : null
  const start =
    field === 'rename'
      ? (connection?.label ?? '')
      : field === 'address'
        ? (connection?.base_url ?? '')
        : ''
  const current = value ?? start
  const problem =
    current.trim() === ''
      ? 'Fill it in first.'
      : field === 'address' && !ADDRESS_PATTERN.test(current.trim())
        ? 'Start the address with http:// or https://.'
        : current.trim() === start.trim() && field !== 'key'
          ? 'Nothing has changed.'
          : null
  const close = () => {
    setValue(null)
    onDone()
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!field || !connection || !look || problem !== null) return
    const body: ConnectionChange =
      field === 'rename'
        ? { label: current.trim() }
        : field === 'key'
          ? { secret: current.trim() }
          : { base_url: current.trim() }
    edit.mutate(
      { id: connection.id, body },
      {
        onSuccess: () => {
          toast.success(look.done)
          close()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  const Icon = look?.icon ?? PenLine
  return (
    <Dialog
      open={field !== null && connection !== null}
      onOpenChange={(next) => {
        if (!next && !edit.isPending) close()
      }}
    >
      <DialogContent className='sm:max-w-lg'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={Icon} />
            <DialogTitle>{`${look?.title ?? ''} ${connection?.label ?? ''}`}</DialogTitle>
          </div>
          <DialogDescription>
            {field === 'key'
              ? 'The old key is forgotten the moment the new one is sealed.'
              : 'Chains that use this connection keep it.'}
          </DialogDescription>
        </DialogHeader>
        <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
          <FormRow label={look?.label ?? ''}>
            {(id) => (
              <Input
                id={id}
                type={
                  field === 'key'
                    ? 'password'
                    : field === 'address'
                      ? 'url'
                      : 'text'
                }
                autoComplete='off'
                maxLength={field === 'rename' ? LABEL_MAX : undefined}
                value={current}
                onChange={(event) => setValue(event.target.value)}
              />
            )}
          </FormRow>
          <DialogFooter>
            <Button type='button' variant='outline' onClick={close}>
              Cancel
            </Button>
            <Button
              act={edit}
              type='submit'
              disabled={problem !== null || edit.isPending}
              disabledReason={problem ?? 'Saving.'}
            >
              {edit.isPending ? (
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
              ) : (
                <Save />
              )}
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function LogOutConfirm({
  workspaceId,
  connection,
  onDone,
}: {
  workspaceId: number
  connection: ProviderConnection | null
  onDone: () => void
}) {
  const logOut = useLogOut(workspaceId)
  return (
    <ConfirmDialog
      act={logOut}
      open={connection !== null}
      onOpenChange={(next) => {
        if (!next && !logOut.isPending) onDone()
      }}
      title={`Log out of ${connection?.label ?? ''}?`}
      desc='Its login is forgotten on this server. Chains that use it skip it until you log in again.'
      confirmText='Log out'
      isLoading={logOut.isPending}
      handleConfirm={() => {
        if (!connection) return
        logOut.mutate(connection.id, {
          onSuccess: () => {
            toast.success(`${connection.label} is logged out`)
            onDone()
          },
          onError: (error) => toast.error(error.message),
        })
      }}
    />
  )
}

export function ConnectionActs({
  scope,
  pending,
  onDone,
}: {
  scope: ProviderScope
  pending: PendingAct | null
  onDone: () => void
}) {
  const remove = useRemoveConnection(scope)
  const target = pending?.connection ?? null
  return (
    <>
      <EditDialog
        scope={scope}
        field={pending ? fieldOf(pending.act) : null}
        connection={target}
        onDone={onDone}
      />
      {scope !== 'server' && (
        <LogOutConfirm
          workspaceId={scope.workspaceId}
          connection={pending?.act === 'logout' ? target : null}
          onDone={onDone}
        />
      )}
      <ConfirmDialog
        act={remove}
        open={pending?.act === 'remove'}
        onOpenChange={(next) => {
          if (!next && !remove.isPending) onDone()
        }}
        destructive
        title={`Remove ${target?.label ?? ''}?`}
        desc='Its key or login is forgotten and every chain entry that uses it goes with it.'
        confirmText='Remove'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (!target) return
          remove.mutate(target.id, {
            onSuccess: () => {
              toast.success(`${target.label} is removed`)
              onDone()
            },
            onError: (error) => toast.error(error.message),
          })
        }}
      />
    </>
  )
}
