import { type KeyboardEvent, useEffect, useId, useState } from 'react'
import { format } from 'date-fns'
import { MapPin, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { ConfirmDialog } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type MapNote } from './api'
import { NOTE_COLORS, NOTE_TOKEN, type NoteColor, noteColor } from './mapScene'

export const NOTE_MAX_LENGTH = 400

const NOTE_COLOR_LABEL: Record<NoteColor, string> = {
  gold: 'Gold',
  red: 'Red',
  blue: 'Blue',
  green: 'Green',
  violet: 'Violet',
}

const POPUP_WIDTH = 288
const EDGE = 12
const ABOVE = 16
const POPUP_HEIGHT = 300

export type NotePopup =
  | { kind: 'new'; x: number; y: number; mapX: number; mapY: number }
  | { kind: 'read'; x: number; y: number; note: MapNote }

type MapNoteOverlayProps = {
  popup: NotePopup
  width: number
  height: number
  saving: boolean
  onSave: (text: string, color: NoteColor) => void
  onDelete: (note: MapNote) => void
  onClose: () => void
}

function Swatch({ color }: { color: NoteColor }) {
  return (
    <span
      aria-hidden='true'
      className='size-icon-sm rounded-full border border-foreground/30'
      style={{ background: `var(--${NOTE_TOKEN[color]})` }}
    />
  )
}

export function MapNoteOverlay({
  popup,
  width,
  height,
  saving,
  onSave,
  onDelete,
  onClose,
}: MapNoteOverlayProps) {
  const fieldId = useId()
  const [text, setText] = useState('')
  const [color, setColor] = useState<NoteColor>('gold')
  const [confirming, setConfirming] = useState(false)
  const left = Math.min(
    Math.max(EDGE, popup.x - POPUP_WIDTH / 2),
    Math.max(EDGE, width - POPUP_WIDTH - EDGE)
  )
  const above = popup.y - ABOVE >= POPUP_HEIGHT + EDGE
  const place = above
    ? { bottom: height - popup.y + ABOVE }
    : {
        top: Math.max(
          EDGE,
          Math.min(popup.y + ABOVE, height - POPUP_HEIGHT - EDGE)
        ),
      }

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const submit = () => onSave(text.trim(), color)
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div
      role='dialog'
      aria-label={popup.kind === 'new' ? 'New note' : 'Your note'}
      className='absolute flex max-h-full w-72 max-w-full min-w-0 flex-col gap-3 overflow-y-auto rounded-lg border bg-popover p-3 text-popover-foreground shadow-lg'
      style={{ left, ...place }}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <MapPin
          aria-hidden='true'
          className='size-icon-md shrink-0 text-primary'
        />
        <Text as='span' weight='semibold' truncate className='flex-1'>
          {popup.kind === 'new'
            ? 'New note'
            : `Your note · ${format(new Date(popup.note.created_at), 'yyyy-MM-dd')}`}
        </Text>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close'
          onClick={onClose}
        >
          <X />
        </Button>
      </div>
      {popup.kind === 'new' ? (
        <>
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label as='label' htmlFor={fieldId}>
              What will happen here?
            </Label>
            <Textarea
              id={fieldId}
              autoFocus
              value={text}
              maxLength={NOTE_MAX_LENGTH}
              placeholder='A reminder to yourself…'
              onChange={(event) => setText(event.target.value)}
              onKeyDown={onKeyDown}
            />
            <Muted variant='caption'>{`${text.length} / ${NOTE_MAX_LENGTH}`}</Muted>
          </div>
          <ToggleGroup
            type='single'
            size='sm'
            variant='outline'
            value={color}
            aria-label='Note colour'
            onValueChange={(value) => value && setColor(value as NoteColor)}
          >
            {NOTE_COLORS.map((option) => (
              <ToggleGroupItem
                key={option}
                value={option}
                aria-label={NOTE_COLOR_LABEL[option]}
              >
                <Swatch color={option} />
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <Button
            size='sm'
            onClick={submit}
            disabled={saving || text.trim().length === 0}
            disabledReason={
              saving ? 'Pinning the note…' : 'A note must have text.'
            }
          >
            <MapPin />
            Pin
          </Button>
        </>
      ) : (
        <>
          <div className='flex min-w-0 items-start gap-2'>
            <Swatch color={noteColor(popup.note)} />
            <Text className='min-w-0 flex-1 whitespace-pre-wrap'>
              {popup.note.text}
            </Text>
          </div>
          <Button
            size='sm'
            variant='destructive'
            onClick={() => setConfirming(true)}
          >
            <Trash2 />
            Delete
          </Button>
          <ConfirmDialog
            open={confirming}
            onOpenChange={setConfirming}
            title='Delete this note?'
            desc='The pin and its text are removed from the map.'
            confirmText='Delete the note'
            destructive
            isLoading={saving}
            handleConfirm={() => {
              setConfirming(false)
              onDelete(popup.note)
            }}
          />
        </>
      )}
    </div>
  )
}
