import { useState } from 'react'
import { BellPlus, EyeOff, MoreHorizontal, PenLine, Save } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog, FormRow } from '@/components/domain'
import { type ChronicleLine } from '@/features/entity/api/types'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

const LINE_MAX = 4000

export function ChronicleLineMenu({ line }: { line: ChronicleLine }) {
  const [editing, setEditing] = useState(false)
  const [hiding, setHiding] = useState(false)
  const [text, setText] = useState(line.text)
  const { reason } = useGodGate()
  const blocked = reason()
  const amend = useGodAction({
    writes: [{ lever: 'chronicle:edit' }],
    run: (body: { text?: string; visible?: boolean }) =>
      unwrap(
        api.POST('/api/actions/chronicle:edit', {
          body: { chronicle_id: line.id, ...body },
        })
      ),
    onDone: () => {
      setEditing(false)
      setHiding(false)
    },
  })
  const pin = useGodAction({
    writes: [
      {
        method: 'POST',
        path: '/api/notifications/from-chronicle/{chronicle_id}',
      },
    ],
    run: () =>
      unwrap(
        api.POST('/api/notifications/from-chronicle/{chronicle_id}', {
          params: { path: { chronicle_id: line.id } },
        })
      ),
    success: 'Pinned to your notifications',
    invalidate: [queryKeys.notifications.all],
  })
  const trimmed = text.trim()
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            act={[amend, pin]}
            variant='ghost'
            size='icon-sm'
            aria-label={`Line actions for epoch ${line.epoch}`}
          >
            <MoreHorizontal />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align='end'>
          <DropdownMenuItem
            disabled={blocked !== null}
            onSelect={() => {
              setText(line.text)
              setEditing(true)
            }}
          >
            <PenLine />
            Amend the line
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={blocked !== null}
            onSelect={() => setHiding(true)}
          >
            <EyeOff />
            Hide from the chronicle
          </DropdownMenuItem>
          <DropdownMenuItem
            act={pin}
            disabled={pin.isPending}
            onSelect={() => pin.mutate()}
          >
            <BellPlus />
            Pin to notifications
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Amend the chronicle</DialogTitle>
            <DialogDescription>
              Fix a leftover word or a slip of the pen. The line keeps its
              epoch, kind and links.
            </DialogDescription>
          </DialogHeader>
          <FormRow label='The line'>
            {(id) => (
              <Textarea
                id={id}
                maxLength={LINE_MAX}
                value={text}
                onChange={(event) => setText(event.target.value)}
              />
            )}
          </FormRow>
          <DialogFooter>
            <Button variant='outline' onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <ActionButton
              act={amend}
              label='Save the line'
              icon={Save}
              variant='default'
              blocked={
                blocked ??
                (trimmed === ''
                  ? 'A line cannot be emptied; hide it instead.'
                  : null) ??
                (trimmed === line.text ? 'Nothing has changed.' : null)
              }
              pending={amend.isPending}
              onRun={() => amend.mutate({ text: trimmed })}
            />
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        act={amend}
        open={hiding}
        onOpenChange={setHiding}
        title='Hide this line?'
        desc='It leaves the chronicle, the book and the search; the record it tells of stays.'
        destructive
        confirmText='Hide the line'
        isLoading={amend.isPending}
        handleConfirm={() => amend.mutate({ visible: false })}
      />
    </>
  )
}
