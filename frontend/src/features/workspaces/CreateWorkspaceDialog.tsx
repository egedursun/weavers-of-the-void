import { type FormEvent, useState } from 'react'
import { LoaderCircle, Users } from 'lucide-react'
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
import { FormRow, Medallion } from '@/components/domain'
import { WorkspaceCrest } from './WorkspaceCrest'
import { useCreateWorkspace } from './api'
import { type Workspace } from './types'
import { WORKSPACE_NAME_MAX, workspaceNameProblem } from './workspaceRules'

export function CreateWorkspaceDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: (workspace: Workspace) => void
}) {
  const create = useCreateWorkspace()
  const [name, setName] = useState('')
  const problem = workspaceNameProblem(name)
  const close = () => {
    setName('')
    onClose()
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || create.isPending) return
    create.mutate(name.trim(), {
      onSuccess: (workspace) => {
        toast.success(`${workspace.name} is founded; you are its administrator`)
        setName('')
        onCreated(workspace)
      },
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) close()
      }}
    >
      <DialogContent className='sm:max-w-lg'>
        <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
          <DialogHeader>
            <div className='flex min-w-0 items-center gap-3'>
              <Medallion icon={Users} />
              <DialogTitle>Found a team workspace</DialogTitle>
            </div>
            <DialogDescription>
              A shared hall with its own Library of Universes. You become its
              administrator and add the team from its settings.
            </DialogDescription>
          </DialogHeader>
          <div className='flex min-w-0 items-center gap-3 rounded-md surface-well p-3'>
            <WorkspaceCrest name={name.trim() || 'A new workspace'} size='md' />
            <FormRow label='Name of the workspace'>
              {(id) => (
                <Input
                  id={id}
                  value={name}
                  maxLength={WORKSPACE_NAME_MAX}
                  onChange={(event) => setName(event.target.value)}
                />
              )}
            </FormRow>
          </div>
          <DialogFooter>
            <Button type='button' variant='outline' onClick={close}>
              Cancel
            </Button>
            <Button
              act={create}
              type='submit'
              disabled={problem !== null || create.isPending}
              disabledReason={problem ?? 'The workspace is being founded.'}
            >
              {create.isPending ? (
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
              ) : (
                <Users />
              )}
              Found it
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
