import {
  type ClipboardEvent,
  type DragEvent,
  type KeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react'
import { EyeOff, Paperclip, SendHorizontal, Square } from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Textarea } from '@/components/ui/textarea'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Muted } from '@/components/typography'
import { AttachmentTrayList } from './AttachmentTray'
import { ModeBar } from './ModeBar'
import { useCancelCycle, useSendCycle } from './api'
import { MODE_LOOK, stepMode } from './modes'
import { type WillCapabilities } from './types'
import { useAttachmentTray } from './useAttachmentTray'
import { useWill } from './willStore'

type ComposerProps = {
  capabilities: WillCapabilities | null
  runningCycleId: number | null
  awaiting: boolean
}

function composerKey(
  event: Pick<
    KeyboardEvent,
    'key' | 'shiftKey' | 'ctrlKey' | 'metaKey' | 'altKey'
  > & {
    composing: boolean
  }
): 'next' | 'previous' | 'send' | null {
  if (event.composing || event.key === 'Process') return null
  if (event.ctrlKey || event.metaKey || event.altKey) return null
  if (event.key === 'Tab') return event.shiftKey ? 'previous' : 'next'
  if (event.key === 'Enter' && !event.shiftKey) return 'send'
  return null
}

function sendBlock({
  text,
  uploading,
  running,
  awaiting,
  capabilities,
}: {
  text: string
  uploading: boolean
  running: boolean
  awaiting: boolean
  capabilities: WillCapabilities | null
}): string | null {
  if (isReadOnly()) return READ_ONLY_MESSAGE
  if (!capabilities) return 'The Divine Will is still waking; wait a moment.'
  if (!capabilities.enabled)
    return (
      capabilities.note || 'The Divine Will cannot answer in this world now.'
    )
  if (awaiting)
    return 'An act waits for your approval above; approve or decline it first.'
  if (running)
    return 'The Divine Will is still at work; stop it or wait for its answer.'
  if (uploading) return 'Wait until every file has been uploaded.'
  if (!text.trim()) return 'Write what you wish first.'
  return null
}

export function Composer({
  capabilities,
  runningCycleId,
  awaiting,
}: ComposerProps) {
  const mode = useWill((state) => state.mode)
  const setMode = useWill((state) => state.setMode)
  const draft = useWill((state) => state.draft)
  const setDraft = useWill((state) => state.setDraft)
  const seed = useWill((state) => state.seed)
  const takeSeed = useWill((state) => state.takeSeed)
  const send = useSendCycle()
  const cancel = useCancelCycle()
  const tray = useAttachmentTray(capabilities)
  const [over, setOver] = useState(false)
  const field = useRef<HTMLTextAreaElement>(null)
  const picker = useRef<HTMLInputElement>(null)
  const hintId = useId()
  const look = MODE_LOOK[mode]
  const running = runningCycleId !== null

  useEffect(() => {
    if (!seed) return
    const planted = takeSeed()
    if (!planted) return
    setDraft(planted.text)
    window.requestAnimationFrame(() => {
      const element = field.current
      if (!element) return
      element.focus()
      element.setSelectionRange(element.value.length, element.value.length)
    })
  }, [seed, takeSeed, setDraft])

  useEffect(() => {
    field.current?.focus()
  }, [])

  const blocked = sendBlock({
    text: draft,
    uploading: tray.uploading,
    running: running || send.isPending,
    awaiting,
    capabilities,
  })
  const attachBlock = isReadOnly()
    ? READ_ONLY_MESSAGE
    : capabilities === null
      ? 'The upload limits are still loading.'
      : tray.accepted >= capabilities.upload_max_files
        ? `Only ${plural(capabilities.upload_max_files, 'file')} fit in one message.`
        : null

  const submit = () => {
    if (blocked) return
    send.mutate(
      { text: draft.trim(), mode, attachment_ids: tray.ids },
      {
        onSuccess: () => {
          setDraft('')
          tray.clear()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    const intent = composerKey({
      key: event.key,
      shiftKey: event.shiftKey,
      ctrlKey: event.ctrlKey,
      metaKey: event.metaKey,
      altKey: event.altKey,
      composing: event.nativeEvent.isComposing,
    })
    if (intent === null) return
    event.preventDefault()
    if (intent === 'send') submit()
    else setMode(stepMode(mode, intent === 'next' ? 1 : -1))
  }

  const take = (list: FileList | null) => {
    if (!list || list.length === 0 || attachBlock) return
    tray.add(Array.from(list))
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setOver(false)
    take(event.dataTransfer.files)
  }

  const onPaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    if (event.clipboardData.files.length === 0) return
    event.preventDefault()
    take(event.clipboardData.files)
  }

  return (
    <div
      data-domain='will-composer'
      className='relative flex min-w-0 flex-col gap-2.5'
      onDragOver={(event) => {
        if (!event.dataTransfer.types.includes('Files') || attachBlock) return
        event.preventDefault()
        setOver(true)
      }}
      onDragLeave={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null))
          return
        setOver(false)
      }}
      onDrop={onDrop}
    >
      <ModeBar mode={mode} onChange={setMode} />
      <AttachmentTrayList tray={tray} vision={capabilities?.images ?? false} />
      <div className='max-h-64 min-w-0 overflow-y-auto'>
        <Textarea
          ref={field}
          value={draft}
          rows={2}
          aria-label={`Your words to the Divine Will, ${look.label} mode`}
          aria-describedby={hintId}
          placeholder={look.placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          type='button'
          variant='outline'
          size='sm'
          disabled={attachBlock !== null}
          disabledReason={attachBlock ?? undefined}
          onClick={() => picker.current?.click()}
        >
          <Paperclip />
          Attach
        </Button>
        {capabilities && !capabilities.images && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge size='sm' variant='warning' tabIndex={0}>
                <EyeOff />
                {capabilities.probed
                  ? 'Cannot see images'
                  : 'Images not yet tried'}
              </Badge>
            </TooltipTrigger>
            <TooltipContent className='max-w-xs'>
              {capabilities.note ||
                `${capabilities.model || 'The model'} reads your documents but cannot see pictures; when you attach one, it is told that you did.`}
            </TooltipContent>
          </Tooltip>
        )}
        <Muted
          id={hintId}
          as='span'
          variant='caption'
          className='hidden min-w-0 flex-1 items-center gap-1 @md/will:flex'
        >
          <Kbd>Tab</Kbd> mode <Kbd>Enter</Kbd> send <Kbd>Shift Enter</Kbd> new
          line
        </Muted>
        <span aria-hidden='true' className='flex-1 @md/will:hidden' />
        {running ? (
          <Button
            type='button'
            variant='destructive'
            size='sm'
            disabled={cancel.isPending}
            disabledReason='Stopping the Divine Will.'
            onClick={() =>
              cancel.mutate(runningCycleId, {
                onError: (error) => toast.error(error.message),
              })
            }
          >
            <Square />
            Stop
          </Button>
        ) : (
          <Button
            type='button'
            size='sm'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={submit}
          >
            <SendHorizontal />
            Send
          </Button>
        )}
      </div>
      <Input
        ref={picker}
        type='file'
        multiple
        hidden
        tabIndex={-1}
        aria-label='Attach files'
        onChange={(event) => {
          take(event.target.files)
          event.target.value = ''
        }}
      />
      {over && <div aria-hidden='true' className='will-drop-veil' />}
    </div>
  )
}
