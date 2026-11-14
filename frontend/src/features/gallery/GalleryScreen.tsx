import { useMemo, useState } from 'react'
import { navItem } from '@/config/navigation'
import {
  Crown,
  Globe2,
  Grid2x2,
  Grid3x3,
  ImageOff,
  Images,
  Layers,
  Search,
  Upload,
  X,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  PageHeader,
  Section,
} from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Muted, Text } from '@/components/typography'
import { drawerKindOf } from '@/features/chronicle/linkTargets'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useWorldState } from '@/features/entity/api/queries'
import { BulkImageGenPanel } from '@/features/images/BulkImageGenPanel'
import { Lightbox } from '@/features/images/Lightbox'
import {
  type ImageListView,
  useImageGenStatus,
  useImages,
} from '@/features/images/api'
import { useImageGenEvents } from '@/features/images/imageGenState'
import { type GalleryDensity, GalleryGrid } from './GalleryGrid'
import { MissingImages } from './MissingImages'
import {
  CATEGORY_ICON,
  DIVINE_KINDS,
  EVERY,
  FALLBACK_ICON,
  type GallerySort,
  SORTS,
  SORT_LABEL,
  categoryLabel,
  categoryOf,
  countBy,
  divineRank,
  sortImages,
} from './galleryModel'

const ITEM = navItem('gallery')
const PAGE = { roomy: 48, dense: 96 } as const
const CHIP_LIMIT = 10
const VEILED_TYPE = 'outer_being'

type Opened = { list: 'hall' | 'grid'; index: number }

export function GalleryScreen() {
  useImageGenEvents()
  const images = useImages(null)
  const status = useImageGenStatus()
  const state = useWorldState()
  const drawers = useDrawerStack()
  const [category, setCategory] = useState<string>(EVERY)
  const [world, setWorld] = useState<string>(EVERY)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<GallerySort>('newest')
  const [density, setDensity] = useState<GalleryDensity>('roomy')
  const [shown, setShown] = useState<number>(PAGE.roomy)
  const [opened, setOpened] = useState<Opened | null>(null)
  const all = useMemo(() => images.data ?? [], [images.data])
  const worlds = useMemo(() => state.data?.worlds ?? [], [state.data?.worlds])
  const worldNames = useMemo(
    () => new Map(worlds.map((item) => [item.id, item.name])),
    [worlds]
  )
  const hall = useMemo(
    () =>
      all
        .filter((item) => DIVINE_KINDS.has(item.target_kind ?? ''))
        .sort(
          (left, right) =>
            divineRank(left) - divineRank(right) ||
            (left.target_name ?? '').localeCompare(right.target_name ?? '')
        ),
    [all]
  )
  const categories = useMemo(() => countBy(all, categoryOf), [all])
  const needle = query.trim().toLowerCase()
  const filtered = useMemo(
    () =>
      sortImages(
        all.filter(
          (item) =>
            (category === EVERY || categoryOf(item) === category) &&
            (world === EVERY || String(item.target_world_id) === world) &&
            (!needle || (item.target_name ?? '').toLowerCase().includes(needle))
        ),
        sort
      ),
    [all, category, world, needle, sort]
  )
  const page = filtered.slice(0, shown)
  const list = opened?.list === 'hall' ? hall : page
  const current = opened ? list[opened.index] : undefined
  const readOnly = state.data?.read_only ? READ_ONLY_REASON : null
  const veiled = (item: ImageListView) => item.target_type === VEILED_TYPE
  const worldOf = (item: ImageListView) =>
    item.target_world_id !== null
      ? (worldNames.get(item.target_world_id) ?? null)
      : null
  const missing = status.data?.missing ?? 0
  const picturedWorlds = new Set(
    all.map((item) => item.target_world_id).filter((id) => id !== null)
  ).size
  const filtering = category !== EVERY || world !== EVERY || needle !== ''
  const chips = categories.slice(0, CHIP_LIMIT)
  const rest = categories.slice(CHIP_LIMIT)
  const reset = (next: () => void) => {
    next()
    setShown(PAGE[density])
  }
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        meta={
          <Badge variant='outline'>{`${plural(all.length, 'image', 'images')}`}</Badge>
        }
        actions={
          <Button
            variant='outline'
            size='sm'
            onClick={() => drawers.open({ kind: 'creator' })}
          >
            <Upload />
            Upload for the god or a world
          </Button>
        }
      />
      {images.isError && <Text tone='destructive'>{images.error.message}</Text>}
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5'>
        <MiniStat icon={Images} label='Images' value={all.length} tone='gold' />
        <MiniStat
          icon={Layers}
          label='Kinds pictured'
          value={categories.length}
          tone='verdigris'
        />
        <MiniStat
          icon={Crown}
          label='Divine portraits'
          value={hall.length}
          tone='gold'
          hint='The Creator, the children, foreign gods and worlds'
        />
        <MiniStat
          icon={Globe2}
          label='Worlds pictured'
          value={picturedWorlds}
          tone='info'
        />
        <MiniStat
          icon={ImageOff}
          label='Still bare'
          value={missing}
          tone={missing > 0 ? 'warning' : 'success'}
          hint='Important records that have no image yet'
        />
      </div>
      {images.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : all.length === 0 ? (
        <EmptyState
          icon={Images}
          title='No images yet'
          description="Open a record's page and upload or generate an image there."
        />
      ) : (
        <>
          {hall.length > 0 && (
            <Section
              id='gallery-hall'
              title='Hall of the divine'
              description='The Creator, the children, the foreign gods and the worlds.'
              level={3}
            >
              <GalleryGrid
                items={hall}
                density='roomy'
                veiledOf={veiled}
                worldOf={worldOf}
                onOpen={(index) => setOpened({ list: 'hall', index })}
                readOnlyReason={readOnly}
              />
            </Section>
          )}
          <Section
            id='gallery-all'
            title='Every likeness'
            description={
              filtering
                ? `${formatInteger(filtered.length)} of ${plural(all.length, 'image', 'images')} match.`
                : `${plural(all.length, 'image', 'images')}.`
            }
            level={3}
          >
            <div className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <div className='min-w-0 flex-1'>
                  <Input
                    type='search'
                    leadingIcon={Search}
                    placeholder='Find by name'
                    aria-label='Find by name'
                    value={query}
                    onChange={(event) =>
                      reset(() => setQuery(event.target.value))
                    }
                  />
                </div>
                {worlds.length > 1 && (
                  <Select
                    value={world}
                    onValueChange={(value) => reset(() => setWorld(value))}
                  >
                    <SelectTrigger aria-label='World' size='sm'>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={EVERY}>Every world</SelectItem>
                      {worlds.map((item) => (
                        <SelectItem key={item.id} value={String(item.id)}>
                          {item.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                <Select
                  value={sort}
                  onValueChange={(value) =>
                    reset(() => setSort(value as GallerySort))
                  }
                >
                  <SelectTrigger aria-label='Order' size='sm'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SORTS.map((key) => (
                      <SelectItem key={key} value={key}>
                        {SORT_LABEL[key]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <ToggleGroup
                  type='single'
                  variant='outline'
                  size='sm'
                  value={density}
                  onValueChange={(value) => {
                    if (!value) return
                    const next = value as GalleryDensity
                    setDensity(next)
                    setShown(PAGE[next])
                  }}
                  aria-label='Tile size'
                >
                  <ToggleGroupItem value='roomy' aria-label='Large tiles'>
                    <Grid2x2 />
                  </ToggleGroupItem>
                  <ToggleGroupItem value='dense' aria-label='Small tiles'>
                    <Grid3x3 />
                  </ToggleGroupItem>
                </ToggleGroup>
              </div>
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Button
                  size='sm'
                  variant={category === EVERY ? 'secondary' : 'ghost'}
                  aria-pressed={category === EVERY}
                  onClick={() => reset(() => setCategory(EVERY))}
                >
                  <Images />
                  {`All · ${formatInteger(all.length)}`}
                </Button>
                {chips.map(([key, count]) => {
                  const Icon = CATEGORY_ICON[key] ?? FALLBACK_ICON
                  return (
                    <Button
                      key={key}
                      size='sm'
                      variant={category === key ? 'secondary' : 'ghost'}
                      aria-pressed={category === key}
                      onClick={() => reset(() => setCategory(key))}
                    >
                      <Icon />
                      {`${categoryLabel(key)} · ${formatInteger(count)}`}
                    </Button>
                  )
                })}
                {rest.length > 0 && (
                  <Select
                    value={
                      rest.some(([key]) => key === category) ? category : ''
                    }
                    onValueChange={(value) => reset(() => setCategory(value))}
                  >
                    <SelectTrigger aria-label='More kinds' size='sm'>
                      <SelectValue placeholder={`${rest.length} more kinds`} />
                    </SelectTrigger>
                    <SelectContent>
                      {rest.map(([key, count]) => (
                        <SelectItem key={key} value={key}>
                          {`${categoryLabel(key)} · ${formatInteger(count)}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {filtering && (
                  <Button
                    size='sm'
                    variant='ghost'
                    onClick={() =>
                      reset(() => {
                        setCategory(EVERY)
                        setWorld(EVERY)
                        setQuery('')
                      })
                    }
                  >
                    <X />
                    Clear
                  </Button>
                )}
              </div>
            </div>
            {filtered.length === 0 ? (
              <EmptyState
                size='compact'
                icon={ImageOff}
                title='Nothing matches'
                description='Loosen the filters to see more likenesses.'
              />
            ) : (
              <GalleryGrid
                items={page}
                density={density}
                veiledOf={veiled}
                worldOf={worldOf}
                onOpen={(index) => setOpened({ list: 'grid', index })}
                readOnlyReason={readOnly}
              />
            )}
            {filtered.length > shown && (
              <div className='flex min-w-0 flex-wrap items-center gap-3'>
                <Button
                  variant='outline'
                  onClick={() => setShown((value) => value + PAGE[density])}
                >
                  {`Show ${formatInteger(Math.min(PAGE[density], filtered.length - shown))} more`}
                </Button>
                <Muted variant='caption'>
                  {`${formatInteger(shown)} of ${formatInteger(filtered.length)} shown`}
                </Muted>
              </div>
            )}
          </Section>
        </>
      )}
      <Lightbox
        images={list.map((item) => item.image)}
        index={opened?.index ?? null}
        onIndexChange={(index) =>
          setOpened(index === null || !opened ? null : { ...opened, index })
        }
        title={current?.target_name ?? 'Image'}
        veiled={current ? veiled(current) : false}
        readOnlyReason={readOnly}
        extra={() => {
          if (!current) return null
          const drawer = drawerKindOf(current.target_kind ?? 'entity')
          const category = categoryOf(current)
          const Icon = CATEGORY_ICON[category] ?? FALLBACK_ICON
          return (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Badge size='sm' variant='secondary'>
                <Icon />
                {categoryLabel(category)}
              </Badge>
              {worldOf(current) && (
                <Badge size='sm' variant='outline'>
                  <Globe2 />
                  {worldOf(current)}
                </Badge>
              )}
              {drawer ? (
                <EntityLink
                  kind={drawer}
                  id={
                    drawer === 'creator'
                      ? undefined
                      : String(current.image.target_node_id)
                  }
                >
                  {`Open the page of ${current.target_name ?? 'the record'}`}
                </EntityLink>
              ) : (
                <Muted variant='caption'>
                  {current.target_name ?? 'Unknown record'}
                </Muted>
              )}
            </div>
          )
        }}
      />
      <MissingImages type={null} />
      <BulkImageGenPanel />
    </>
  )
}
