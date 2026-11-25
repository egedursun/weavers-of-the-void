import { useState } from 'react'
import {
  ArrowLeftRight,
  BookOpenText,
  CalendarClock,
  FileX2,
  GitCommitVertical,
  Languages,
  ListChecks,
  PencilLine,
  RefreshCw,
  Sparkles,
  Tag,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { formatDateTime, formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  ConfirmDialog,
  EmptyState,
  FormRow,
  KeyValueList,
  LoadingBlock,
  Medallion,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ShareToggle } from '@/features/team/share'
import { NodeRef } from '../NodeRef'
import { PlanCard } from '../PlanCard'
import {
  useArtifact,
  useArtifactDiff,
  useArtifactVersion,
  useDeleteArtifact,
} from '../api'
import { MODE_LOOK } from '../modes'
import { type WillArtifact } from '../types'
import { ExportMenu, MetaDialog } from './ArtifactMeta'
import { ArtifactPreview, DiffView } from './ArtifactPreview'
import {
  CATEGORY_LOOK,
  FORMAT_LOOK,
  KIND_LOOK,
  STATUS_LOOK,
} from './artifactLook'
import { useReviseArtifact } from './revise'

const VERSIONS_SHOWN = 8

function Versions({
  found,
  viewing,
  onView,
}: {
  found: WillArtifact
  viewing: number | null
  onView: (version: number | null) => void
}) {
  const artifact = found.artifact
  const newestFirst = [...found.versions].sort(
    (left, right) => right.version - left.version
  )
  const [a, setA] = useState<number | null>(newestFirst[1]?.version ?? null)
  const [b, setB] = useState<number | null>(newestFirst[0]?.version ?? null)
  const version = useArtifactVersion(artifact.id, viewing)
  const diff = useArtifactDiff(artifact.id, a, b)
  if (newestFirst.length === 0)
    return (
      <EmptyState
        size='compact'
        icon={GitCommitVertical}
        title='No versions'
        description='This writing has no saved version.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <ol className='flex min-w-0 flex-col gap-1.5'>
        <Paged
          items={newestFirst}
          initial={VERSIONS_SHOWN}
          as='li'
          noun={['version', 'versions']}
        >
          {(item) => (
            <li key={item.version}>
              <Button
                variant='outline'
                size='tile'
                aria-pressed={viewing === item.version}
                onClick={() =>
                  onView(viewing === item.version ? null : item.version)
                }
                className={cn(viewing === item.version && 'border-primary')}
              >
                <GitCommitVertical />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='semibold'>
                    {item.version === artifact.current_version
                      ? `Version ${String(item.version)}, the current one`
                      : `Version ${String(item.version)}`}
                  </Text>
                  <Muted as='span' variant='caption' truncate={2}>
                    {[
                      formatDateTime(item.created_at),
                      plural(item.characters, 'character'),
                      item.cycle_id === null ? 'by hand' : 'from an exchange',
                      item.summary,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </Muted>
                </span>
              </Button>
            </li>
          )}
        </Paged>
      </ol>
      {viewing !== null && (
        <div className='flex min-w-0 flex-col gap-2'>
          {version.isPending ? (
            <LoadingBlock label='Loading the version' />
          ) : version.isError ? (
            <Text tone='destructive' role='alert'>
              {version.error.message}
            </Text>
          ) : (
            <>
              <Label>
                {[
                  `Version ${String(version.data.version)}`,
                  formatDateTime(version.data.created_at),
                  version.data.cycle_id === null
                    ? ''
                    : 'written in an exchange',
                  version.data.summary,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </Label>
              <ArtifactPreview
                format={artifact.format}
                body={version.data.body}
                title={`${artifact.title}, version ${String(version.data.version)}`}
              />
            </>
          )}
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-3 rounded-md surface-well px-3 py-3'>
        <Label className='flex items-center gap-1.5'>
          <ArrowLeftRight aria-hidden='true' className='size-icon-xs' />
          Compare two versions
        </Label>
        {newestFirst.length < 2 ? (
          <Muted variant='caption'>
            A second version is needed to compare.
          </Muted>
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
              {(
                [
                  ['Older', a, setA],
                  ['Newer', b, setB],
                ] as const
              ).map(([label, value, set]) => (
                <FormRow key={label} label={label}>
                  {(id) => (
                    <Select
                      value={value === null ? '' : String(value)}
                      onValueChange={(next) => set(Number(next))}
                    >
                      <SelectTrigger id={id} className='w-full'>
                        <SelectValue placeholder='Choose a version' />
                      </SelectTrigger>
                      <SelectContent>
                        {newestFirst.map((item) => (
                          <SelectItem
                            key={item.version}
                            value={String(item.version)}
                          >
                            {`Version ${String(item.version)}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </FormRow>
              ))}
            </div>
            {a === b ? (
              <Muted variant='caption'>Choose two different versions.</Muted>
            ) : diff.isPending ? (
              <LoadingBlock label='Comparing the versions' />
            ) : diff.isError ? (
              <Text tone='destructive' role='alert'>
                {diff.error.message}
              </Text>
            ) : (
              <div className='flex min-w-0 flex-col gap-2'>
                <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Badge size='sm' variant='outline'>
                    {`Version ${String(diff.data.a)} to ${String(diff.data.b)}`}
                  </Badge>
                  <Badge size='sm' variant='success'>
                    {`+${formatInteger(diff.data.added)}`}
                  </Badge>
                  <Badge size='sm' variant='destructive'>
                    {`−${formatInteger(diff.data.removed)}`}
                  </Badge>
                </div>
                <DiffView text={diff.data.text} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function Details({ found }: { found: WillArtifact }) {
  const artifact = found.artifact
  const mode = MODE_LOOK[artifact.mode]
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KeyValueList
        items={[
          { key: 'kind', label: 'Kind', value: KIND_LOOK[artifact.kind].label },
          {
            key: 'category',
            label: 'Shelf',
            value: CATEGORY_LOOK[KIND_LOOK[artifact.kind].category].label,
          },
          {
            key: 'status',
            label: 'Status',
            value: STATUS_LOOK[artifact.status].label,
          },
          {
            key: 'format',
            label: 'Format',
            value: FORMAT_LOOK[artifact.format].label,
          },
          {
            key: 'language',
            label: 'Language',
            value: artifact.language || 'Not named',
          },
          { key: 'mode', label: 'Written in', value: `${mode.label} mode` },
          {
            key: 'version',
            label: 'Current version',
            value: String(artifact.current_version),
          },
          {
            key: 'characters',
            label: 'Length',
            value: plural(artifact.characters, 'character'),
          },
          {
            key: 'created',
            label: 'Written',
            value: formatDateTime(artifact.created_at),
          },
          {
            key: 'updated',
            label: 'Last revised',
            value: formatDateTime(artifact.updated_at),
          },
          {
            key: 'cycle',
            label: 'Made',
            value:
              artifact.created_cycle_id === null
                ? 'By hand'
                : 'In an exchange with the Divine Will',
          },
          {
            key: 'tags',
            label: 'Tags',
            value: artifact.tags.length > 0 ? artifact.tags.join(', ') : 'None',
          },
        ]}
      />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label>Subjects</Label>
        {artifact.subjects.length === 0 ? (
          <Muted variant='caption'>This writing names no subject.</Muted>
        ) : (
          <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
            <Paged items={artifact.subjects} noun={['subject', 'subjects']}>
              {(subject) => (
                <NodeRef
                  key={subject.node_id}
                  id={subject.node_id}
                  name={subject.name}
                />
              )}
            </Paged>
          </div>
        )}
      </div>
    </div>
  )
}

export function ArtifactDetail({
  artifactId,
  onDeleted,
  compact = false,
}: {
  artifactId: number
  onDeleted: () => void
  compact?: boolean
}) {
  const query = useArtifact(artifactId)
  const remove = useDeleteArtifact()
  const revise = useReviseArtifact()
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [viewing, setViewing] = useState<number | null>(null)
  if (query.isPending) return <LoadingBlock label='Opening the writing' />
  if (query.isError)
    return (
      <EmptyState
        icon={FileX2}
        title='The writing could not be opened'
        description={query.error.message}
        action={
          <Button
            variant='outline'
            size='sm'
            onClick={() => void query.refetch()}
          >
            <RefreshCw />
            Try again
          </Button>
        }
      />
    )
  const found = query.data
  const artifact = found.artifact
  const kind = KIND_LOOK[artifact.kind]
  const KindIcon = kind.icon
  const tone = CATEGORY_LOOK[kind.category].tone
  const block = isReadOnly() ? READ_ONLY_MESSAGE : null
  return (
    <article
      data-domain='artifact-detail'
      aria-label={artifact.title}
      className='flex min-w-0 flex-col gap-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={kind.icon} tone={tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold' className='text-gilded font-display'>
            {artifact.title}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant='secondary'>
              <KindIcon />
              {kind.label}
            </Badge>
            <Badge size='sm' variant={STATUS_LOOK[artifact.status].badge}>
              {STATUS_LOOK[artifact.status].label}
            </Badge>
            {artifact.language && (
              <Badge size='sm' variant='outline'>
                <Languages />
                {artifact.language}
              </Badge>
            )}
            <Badge size='sm' variant='outline'>
              <CalendarClock />
              {`Version ${String(found.version)} of ${String(artifact.current_version)}`}
            </Badge>
            {artifact.tags.map((tag) => (
              <Badge key={tag} size='sm' variant='outline'>
                <Tag />
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      </div>
      <ShareToggle
        kind='writing'
        id={artifact.id}
        shared={artifact.owner.shared}
        mine={artifact.owner.mine}
        author={artifact.owner.author_name}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={block !== null}
          disabledReason={block ?? undefined}
          onClick={() => revise(artifact)}
        >
          <Sparkles />
          Ask the Divine Will to revise
        </Button>
        <ExportMenu artifact={artifact} version={viewing} />
        <Button
          variant='outline'
          size='sm'
          disabled={block !== null}
          disabledReason={block ?? undefined}
          onClick={() => setEditing(true)}
        >
          <PencilLine />
          Edit details
        </Button>
        <Button
          act={remove}
          variant='ghost'
          size='sm'
          disabled={block !== null || remove.isPending}
          disabledReason={block ?? 'Deleting the writing.'}
          onClick={() => setDeleting(true)}
        >
          <Trash2 />
          Delete
        </Button>
      </div>
      <Tabs
        defaultValue={artifact.plan_id === null ? 'read' : 'plan'}
        className='flex min-w-0 flex-col gap-3'
      >
        <TabsList
          aria-label='The writing'
          className={compact ? 'w-full' : 'w-full md:w-fit'}
        >
          <TabsTrigger value='read'>
            <BookOpenText />
            Read
          </TabsTrigger>
          <TabsTrigger value='versions'>
            <GitCommitVertical />
            Versions
          </TabsTrigger>
          <TabsTrigger value='details'>
            <Tag />
            Details
          </TabsTrigger>
          {artifact.plan_id !== null && (
            <TabsTrigger value='plan'>
              <ListChecks />
              Plan
            </TabsTrigger>
          )}
        </TabsList>
        <TabsContent value='read'>
          <ArtifactPreview
            format={artifact.format}
            body={found.body}
            title={artifact.title}
          />
        </TabsContent>
        <TabsContent value='versions'>
          <Versions found={found} viewing={viewing} onView={setViewing} />
        </TabsContent>
        <TabsContent value='details'>
          <Details found={found} />
        </TabsContent>
        {artifact.plan_id !== null && (
          <TabsContent value='plan'>
            <PlanCard planId={artifact.plan_id} />
          </TabsContent>
        )}
      </Tabs>
      <MetaDialog
        artifact={artifact}
        open={editing}
        onOpenChange={setEditing}
      />
      <ConfirmDialog
        act={remove}
        open={deleting}
        onOpenChange={setDeleting}
        title='Delete this writing?'
        desc={`“${artifact.title}” leaves the Library with all its versions and exports. The exchanges that made it stay in the record of the Divine Will.`}
        confirmText='Delete the writing'
        destructive
        isLoading={remove.isPending}
        handleConfirm={() =>
          remove.mutate(artifact.id, {
            onSuccess: () => {
              setDeleting(false)
              toast.success('The writing is deleted.')
              onDeleted()
            },
            onError: (error) => toast.error(error.message),
          })
        }
      />
    </article>
  )
}
