import { useEffect, useRef, useState } from 'react'
import {
  BookOpen,
  CircleAlert,
  FileDown,
  Files,
  Hourglass,
  LoaderCircle,
  PackageCheck,
  ShieldCheck,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatInteger, formatPercent } from '@/lib/format'
import { formatBytes } from '@/lib/units'
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
import { Progress } from '@/components/ui/progress'
import {
  FormRow,
  KeyValueList,
  LoadingBlock,
  Medallion,
  MiniStat,
} from '@/components/domain'
import { FilePicker } from '@/components/domain/FilePicker'
import { Muted, SectionTitle, Text } from '@/components/typography'
import { LibraryJobProgress } from './LibraryJobProgress'
import { UniverseCrest } from './UniverseCrest'
import {
  cancelImport,
  jobSettled,
  uploadUniverse,
  useConfirmImport,
  useLibraryJob,
} from './api'
import { readPackageManifest } from './packageManifest'
import { type PackagePreview, type UniverseManifest } from './types'
import { NAME_MAX, nameProblem, timeLine } from './universeModel'
import { useEnterUniverse } from './useEnterUniverse'

const PACKAGE_ACCEPT = '.aerona'
const PERCENT = 100
const PACKAGE_SUFFIX = /\.aerona$/i

type Reading =
  | { state: 'idle' }
  | { state: 'reading' }
  | { state: 'read'; manifest: UniverseManifest }
  | { state: 'unreadable'; message: string }

type Shown = {
  name: string
  summary: string
  notes: string
  tags: string[]
  sourceId: string
  createdAt: string | null
  exportedAt: string | null
  appVersion: string
  schemaRevision: string
  formatLine: string
  epoch: number
  year: number
  counts: [string, number][]
  fileCount: number
  fileBytes: number
  verified: boolean
  dropped: number
}

function spoken(key: string): string {
  const words = key.replace(/_/g, ' ').trim()
  return words.charAt(0).toLocaleUpperCase() + words.slice(1)
}

function fromManifest(manifest: UniverseManifest): Shown {
  return {
    name: manifest.name,
    summary: manifest.summary ?? '',
    notes: manifest.notes ?? '',
    tags: manifest.tags,
    sourceId: manifest.universe_id ?? '',
    createdAt: manifest.created_at,
    exportedAt: manifest.exported_at,
    appVersion: manifest.app_version ?? '',
    schemaRevision: manifest.schema_revision ?? '',
    formatLine:
      manifest.format_version === null
        ? 'World file from before the library'
        : `Library format ${formatInteger(manifest.format_version)}`,
    epoch: manifest.epoch ?? 0,
    year: manifest.year ?? 0,
    counts: Object.entries(manifest.counts)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, count]) => [spoken(key), count]),
    fileCount: manifest.files.length,
    fileBytes: manifest.files.reduce((sum, item) => sum + item.size, 0),
    verified: false,
    dropped: 0,
  }
}

function fromPreview(preview: PackagePreview): Shown {
  return {
    name: preview.name,
    summary: preview.summary,
    notes: preview.notes,
    tags: preview.tags,
    sourceId: preview.source_id,
    createdAt: preview.created_at,
    exportedAt: preview.exported_at,
    appVersion: preview.app_version,
    schemaRevision: preview.schema_revision,
    formatLine: preview.legacy
      ? 'World file from before the library'
      : 'Library file',
    epoch: preview.epoch,
    year: preview.year,
    counts: [
      ['Population', preview.population],
      ['Sons', preview.sons],
    ],
    fileCount: preview.files,
    fileBytes: preview.size_bytes,
    verified: true,
    dropped: preview.dropped,
  }
}

function ManifestPreview({ shown, file }: { shown: Shown; file: File }) {
  return (
    <section
      aria-label='What the file holds'
      data-domain='import-manifest'
      className='flex min-w-0 flex-col gap-3 rounded-md surface-sheen p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <UniverseCrest name={shown.name || file.name} size='md' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <SectionTitle level={3} truncate={2} className='text-gilded'>
            {shown.name || 'A universe with no name'}
          </SectionTitle>
          <Muted variant='caption' truncate={3}>
            {shown.summary || 'The file carries no summary.'}
          </Muted>
        </div>
        <Badge variant={shown.verified ? 'success' : 'outline'} size='sm'>
          {shown.verified ? (
            <ShieldCheck aria-hidden='true' />
          ) : (
            <Hourglass aria-hidden='true' />
          )}
          {shown.verified ? 'Checked' : 'Not checked yet'}
        </Badge>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={Hourglass}
          label='Time'
          value={timeLine(shown)}
          tone='gold'
        />
        <MiniStat
          icon={Files}
          label='Images and files'
          value={formatInteger(shown.fileCount)}
          hint={formatBytes(shown.fileBytes)}
          tone='info'
        />
        <MiniStat
          icon={PackageCheck}
          label='File size'
          value={formatBytes(file.size)}
          tone='verdigris'
        />
      </div>
      <KeyValueList
        items={[
          {
            label: 'Exported',
            value: shown.exportedAt
              ? formatDateTime(shown.exportedAt)
              : 'Not recorded',
          },
          {
            label: 'First made',
            value: shown.createdAt
              ? formatDateTime(shown.createdAt)
              : 'Not recorded',
          },
          { label: 'App version', value: shown.appVersion || 'Not recorded' },
          {
            label: 'Schema revision',
            value: shown.schemaRevision || 'Not recorded',
          },
          { label: 'File format', value: shown.formatLine },
          {
            label: 'Universe id there',
            value: shown.sourceId ? (
              <Text as='span' className='font-mono'>
                {shown.sourceId}
              </Text>
            ) : (
              'Not recorded'
            ),
          },
          { label: 'Notes', value: shown.notes || 'No notes.' },
          {
            label: 'Tags',
            value:
              shown.tags.length === 0 ? (
                'No tags.'
              ) : (
                <span className='flex min-w-0 flex-wrap gap-1'>
                  {shown.tags.map((tag) => (
                    <Badge key={tag} variant='outline' size='sm'>
                      {tag}
                    </Badge>
                  ))}
                </span>
              ),
          },
          ...(shown.verified
            ? [
                {
                  label: 'Files left out',
                  value:
                    shown.dropped === 0
                      ? 'None: every file passed its check'
                      : `${formatInteger(shown.dropped)} failed their check and stay out`,
                },
              ]
            : []),
          ...shown.counts.map(([label, count]) => ({
            key: `count-${label}`,
            label,
            value: formatInteger(count),
          })),
        ]}
      />
      <Muted variant='caption'>
        {shown.verified
          ? 'The server checked every hash, path and the database. The universe gets a new id of its own here.'
          : 'This is read on your device. The server checks every hash, path and the database before anything is kept.'}
      </Muted>
    </section>
  )
}

function UploadProgress({ fraction }: { fraction: number }) {
  return (
    <div
      role='status'
      aria-live='polite'
      className='flex min-w-0 flex-col gap-2 rounded-md surface-well p-3'
    >
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Text as='span' weight='semibold'>
          Uploading the file
        </Text>
        <Muted as='span' variant='caption'>
          {formatPercent(fraction)}
        </Muted>
      </div>
      <Progress
        size='sm'
        value={fraction * PERCENT}
        aria-label={`Uploading the file: ${formatPercent(fraction)}`}
      />
    </div>
  )
}

export function ImportUniverseDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [reading, setReading] = useState<Reading>({ state: 'idle' })
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState<number | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const abort = useRef<AbortController | null>(null)
  const job = useLibraryJob('imports', jobId)
  const confirm = useConfirmImport()
  const { enter, opening } = useEnterUniverse()
  const status = job.data?.status
  const confirmed = confirm.isSuccess || confirm.isPending
  const checking =
    jobId !== null &&
    !confirmed &&
    (status === undefined || status === 'running')
  const placing =
    confirmed &&
    (status === undefined || status === 'running' || status === 'waiting')
  const waiting = status === 'waiting' && !confirmed
  const done = status === 'done'
  const stopped = jobSettled(job.data) && !done
  const problem = nameProblem(name)
  const preview = job.data?.preview ?? null
  const shown =
    preview !== null
      ? fromPreview(preview)
      : reading.state === 'read'
        ? fromManifest(reading.manifest)
        : null

  useEffect(() => () => abort.current?.abort(), [])

  const upload = (chosen: File) => {
    const controller = new AbortController()
    abort.current = controller
    setFailure(null)
    setJobId(null)
    confirm.reset()
    setUploading(0)
    uploadUniverse(chosen, setUploading, controller.signal).then(
      (started) => {
        setUploading(null)
        setJobId(started.id)
      },
      (error: unknown) => {
        setUploading(null)
        if (error instanceof DOMException && error.name === 'AbortError') return
        setFailure(
          error instanceof Error ? error.message : 'The upload failed.'
        )
      }
    )
  }

  const reset = () => {
    abort.current?.abort()
    abort.current = null
    if (jobId !== null && !jobSettled(job.data)) void cancelImport(jobId)
    setFile(null)
    setReading({ state: 'idle' })
    setName('')
    setUploading(null)
    setJobId(null)
    setFailure(null)
    confirm.reset()
  }

  const choose = (next: File | null) => {
    reset()
    setFile(next)
    if (!next) return
    setReading({ state: 'reading' })
    readPackageManifest(next).then(
      (manifest) => {
        setReading({ state: 'read', manifest })
        setName(manifest.name || next.name.replace(PACKAGE_SUFFIX, ''))
        upload(next)
      },
      (error: unknown) =>
        setReading({
          state: 'unreadable',
          message:
            error instanceof Error
              ? error.message
              : 'The file could not be read.',
        })
    )
  }

  const bring = () => {
    if (jobId === null || problem !== null) return
    confirm.mutate(
      { jobId, name: name.trim() },
      {
        onSuccess: () => void job.refetch(),
        onError: (error) => toast.error(error.message),
      }
    )
  }

  const blocker =
    reading.state === 'idle'
      ? 'Drop a .aerona file first.'
      : reading.state === 'reading'
        ? 'The file is being read.'
        : reading.state === 'unreadable'
          ? 'Choose a file whose contents can be read.'
          : uploading !== null
            ? 'The file is still uploading.'
            : checking
              ? 'The server is still checking the file.'
              : placing
                ? 'The universe is being placed on the shelf.'
                : !waiting
                  ? 'The file is not ready yet.'
                  : problem

  const importedId = done ? (job.data?.universe_id ?? null) : null
  const shownName = job.data?.universe_name || name.trim()

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (placing) return
        if (!next) reset()
        onOpenChange(next)
      }}
    >
      <DialogContent className='sm:max-w-2xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={FileDown} tone='info' />
            <DialogTitle>Import a universe</DialogTitle>
          </div>
          <DialogDescription>
            Bring in a .aerona file exported from a library, yours or someone
            else&apos;s. You see what it holds before anything is kept.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-4'>
          <FilePicker
            file={file}
            onChange={choose}
            accept={PACKAGE_ACCEPT}
            label='Drop a .aerona file here'
            hint='It is checked in full before it joins the library.'
            disabledReason={
              placing ? 'The universe is being placed on the shelf.' : null
            }
          />
          {reading.state === 'reading' && (
            <LoadingBlock label='Reading what the file holds' />
          )}
          {reading.state === 'unreadable' && (
            <Alert variant='destructive'>
              <CircleAlert />
              <AlertTitle>This file cannot be shown</AlertTitle>
              <AlertDescription>{reading.message}</AlertDescription>
            </Alert>
          )}
          {shown && file && (
            <>
              <ManifestPreview shown={shown} file={file} />
              <FormRow
                label='Name on your shelf'
                description='If the name is taken, the library adds a number unless you change it here.'
              >
                {(id) => (
                  <div className='flex w-full min-w-0 flex-col gap-1'>
                    <Input
                      id={id}
                      value={name}
                      maxLength={NAME_MAX}
                      disabled={placing || done}
                      aria-invalid={problem !== null || undefined}
                      onChange={(event) => setName(event.target.value)}
                    />
                    {problem && (
                      <Text variant='caption' tone='destructive'>
                        {problem}
                      </Text>
                    )}
                  </div>
                )}
              </FormRow>
            </>
          )}
          {uploading !== null && <UploadProgress fraction={uploading} />}
          {job.data && (
            <LibraryJobProgress
              job={job.data}
              title={
                placing || done
                  ? 'Placing the universe on the shelf'
                  : 'Checking the file'
              }
            />
          )}
          {failure && (
            <Alert variant='destructive'>
              <CircleAlert />
              <AlertTitle>The upload failed</AlertTitle>
              <AlertDescription>{failure}</AlertDescription>
            </Alert>
          )}
          {done && (
            <Alert>
              <BookOpen />
              <AlertTitle>{`${shownName} stands on the shelf`}</AlertTitle>
              <AlertDescription>
                Every check passed. Open it now or find it among the shelves.
              </AlertDescription>
            </Alert>
          )}
        </div>
        <DialogFooter>
          <Button
            type='button'
            variant='outline'
            disabled={placing}
            disabledReason='The universe is being placed on the shelf.'
            onClick={() => {
              reset()
              onOpenChange(false)
            }}
          >
            {done ? 'Close' : 'Cancel'}
          </Button>
          {importedId !== null ? (
            <Button
              type='button'
              disabled={opening !== null}
              disabledReason='The universe is being opened.'
              onClick={() => {
                const universe = {
                  id: importedId,
                  name: shownName,
                  origin: 'imported' as const,
                }
                reset()
                onOpenChange(false)
                enter(universe)
              }}
            >
              <BookOpen />
              Open it
            </Button>
          ) : stopped || failure ? (
            <Button
              type='button'
              disabled={file === null}
              disabledReason='Drop a .aerona file first.'
              onClick={() => {
                if (file) upload(file)
              }}
            >
              <FileDown />
              Try again
            </Button>
          ) : (
            <Button
              act={confirm}
              type='button'
              disabled={blocker !== null}
              disabledReason={blocker ?? undefined}
              onClick={bring}
            >
              {checking || placing || uploading !== null ? (
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
              ) : (
                <FileDown />
              )}
              {placing ? 'Bringing it in' : 'Bring it into the library'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
