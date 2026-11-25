import { useMemo, useState } from 'react'
import { Download, Save, X } from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { FormRow, ShowMore, useShowMore } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted } from '@/components/typography'
import { NODE_KIND_WORDS } from '@/features/entity/affairs/labels'
import { useNames } from '@/features/entity/api/queries'
import { artifactExportUrl, usePatchArtifact } from '../api'
import {
  type ArtifactKind,
  type ArtifactStatus,
  type WillArtifactSummary,
} from '../types'
import {
  CATEGORY_LOOK,
  CATEGORY_ORDER,
  EXPORT_LOOK,
  EXPORT_ORDER,
  KIND_LOOK,
  KIND_ORDER,
  STATUS_LOOK,
  STATUS_ORDER,
} from './artifactLook'

export function KindSelectItems() {
  return CATEGORY_ORDER.map((category) => {
    const look = CATEGORY_LOOK[category]
    return (
      <SelectGroup key={category}>
        <SelectLabel>{look.label}</SelectLabel>
        {KIND_ORDER.filter((kind) => KIND_LOOK[kind].category === category).map(
          (kind) => {
            const Icon = KIND_LOOK[kind].icon
            return (
              <SelectItem key={kind} value={kind}>
                <Icon />
                {KIND_LOOK[kind].label}
              </SelectItem>
            )
          }
        )}
      </SelectGroup>
    )
  })
}

export function ExportMenu({
  artifact,
  version,
}: {
  artifact: WillArtifactSummary
  version: number | null
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant='outline' size='sm'>
          <Download />
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align='end'>
        <DropdownMenuLabel>
          {version === null
            ? 'Save the current version as'
            : `Save version ${String(version)} as`}
        </DropdownMenuLabel>
        {EXPORT_ORDER.map((format) => {
          const look = EXPORT_LOOK[format]
          const Icon = look.icon
          const unfit = format === 'fountain' && artifact.format !== 'fountain'
          return (
            <DropdownMenuItem key={format} asChild disabled={unfit}>
              <a
                href={
                  unfit
                    ? undefined
                    : artifactExportUrl(artifact.id, format, version)
                }
                download
                aria-disabled={unfit || undefined}
                title={
                  unfit
                    ? 'Only a screenplay script exports as Fountain.'
                    : undefined
                }
              >
                <Icon />
                {look.label}
              </a>
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function splitTags(text: string): string[] {
  return [
    ...new Set(
      text
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
    ),
  ]
}

function MetaForm({
  artifact,
  onDone,
}: {
  artifact: WillArtifactSummary
  onDone: () => void
}) {
  const patch = usePatchArtifact(artifact.id)
  const names = useNames()
  const [title, setTitle] = useState(artifact.title)
  const [kind, setKind] = useState<ArtifactKind>(artifact.kind)
  const [status, setStatus] = useState<ArtifactStatus>(artifact.status)
  const [tags, setTags] = useState(artifact.tags.join(', '))
  const [subjects, setSubjects] = useState(
    artifact.subjects.map((subject) => ({
      id: subject.node_id,
      name: subject.name,
    }))
  )
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter((entry) => !subjects.some((subject) => subject.id === entry.id))
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: NODE_KIND_WORDS[entry.kind],
        })),
    [names.data, subjects]
  )
  const block = isReadOnly()
    ? READ_ONLY_MESSAGE
    : !title.trim()
      ? 'A writing needs a title.'
      : patch.isPending
        ? 'Saving.'
        : null
  const submit = () => {
    if (block) return
    patch.mutate(
      {
        title: title.trim(),
        kind,
        status,
        tags: splitTags(tags),
        node_ids: subjects.map((subject) => subject.id),
      },
      {
        onSuccess: () => {
          toast.success('The details are saved.')
          onDone()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <form
      className='flex min-w-0 flex-col gap-4'
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <FormRow label='Title'>
        {(id) => (
          <Input
            id={id}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        )}
      </FormRow>
      <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2'>
        <FormRow label='Kind'>
          {(id) => (
            <Select
              value={kind}
              onValueChange={(value) => {
                const next = KIND_ORDER.find((item) => item === value)
                if (next) setKind(next)
              }}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <KindSelectItems />
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow label='Status'>
          {() => (
            <ToggleGroup
              type='single'
              variant='outline'
              size='sm'
              value={status}
              aria-label='Status'
              onValueChange={(value) => {
                const next = STATUS_ORDER.find((item) => item === value)
                if (next) setStatus(next)
              }}
            >
              {STATUS_ORDER.map((item) => (
                <ToggleGroupItem key={item} value={item}>
                  {STATUS_LOOK[item].label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          )}
        </FormRow>
      </div>
      <FormRow label='Tags' description='Separate tags with commas.'>
        {(id) => (
          <Input
            id={id}
            value={tags}
            onChange={(event) => setTags(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Subjects'
        description='The records this writing is about.'
      >
        {(id) => (
          <div className='flex w-full min-w-0 flex-col gap-2'>
            {subjects.length > 0 ? (
              <SubjectBadges
                subjects={subjects}
                remove={(gone) =>
                  setSubjects(subjects.filter((item) => item.id !== gone))
                }
              />
            ) : (
              <Muted variant='caption'>No subject yet.</Muted>
            )}
            <RecordCombobox
              id={id}
              options={options}
              value={null}
              placeholder={
                names.isPending ? 'Loading the names' : 'Add a subject'
              }
              searchPlaceholder='Type a name'
              disabled={names.isPending}
              disabledReason='The names of the world are still loading.'
              onChange={(value, option) => {
                if (value === null || option === null) return
                setSubjects([
                  ...subjects,
                  { id: Number(value), name: option.label },
                ])
              }}
            />
          </div>
        )}
      </FormRow>
      <DialogFooter>
        <Button type='button' variant='ghost' onClick={onDone}>
          Cancel
        </Button>
        <Button
          type='submit'
          disabled={block !== null}
          disabledReason={block ?? undefined}
        >
          <Save />
          Save
        </Button>
      </DialogFooter>
    </form>
  )
}

export function MetaDialog({
  artifact,
  open,
  onOpenChange,
}: {
  artifact: WillArtifactSummary
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Details of the writing</DialogTitle>
          <DialogDescription>
            Rename it, file it under another kind, mark it final, tag it or name
            what it is about. The text itself changes only by a new version.
          </DialogDescription>
        </DialogHeader>
        {open && (
          <MetaForm artifact={artifact} onDone={() => onOpenChange(false)} />
        )}
      </DialogContent>
    </Dialog>
  )
}

const SHOWN_SUBJECTS = 12

function SubjectBadges({
  subjects,
  remove,
}: {
  subjects: readonly { id: number; name: string }[]
  remove: (id: number) => void
}) {
  const shown = useShowMore(subjects, SHOWN_SUBJECTS)
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {shown.visible.map((subject) => (
          <Badge key={subject.id} variant='secondary'>
            {subject.name}
            <Button
              type='button'
              variant='ghost'
              size='icon-sm'
              aria-label={`Remove ${subject.name}`}
              onClick={() => remove(subject.id)}
            >
              <X />
            </Button>
          </Badge>
        ))}
      </div>
      <ShowMore state={shown} />
    </div>
  )
}
