import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DomainIcon } from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { Muted, Text } from '@/components/typography'
import { type EntitySummary } from '@/features/entity/api/types'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import { Highlight } from './Highlight'
import { type AtlasSort } from './atlasSearch'

const ATLAS_PAGE_SIZE = 40

type AtlasListProps = {
  items: EntitySummary[]
  sort: AtlasSort
  descending: boolean
  onSort: (sort: AtlasSort) => void
  page: number
  onPage: (page: number) => void
  selected: number | null
  onSelect: (entity: EntitySummary) => void
  typeLabel: (key: string) => string
  locationName: (id: number | null) => string | null
  query: string
}

function SortHead({
  label,
  column,
  sort,
  descending,
  onSort,
}: {
  label: string
  column: AtlasSort
  sort: AtlasSort
  descending: boolean
  onSort: (sort: AtlasSort) => void
}) {
  const active = sort === column
  const Icon = !active ? ArrowUpDown : descending ? ArrowDown : ArrowUp
  return (
    <TableHead
      aria-sort={active ? (descending ? 'descending' : 'ascending') : 'none'}
    >
      <Button variant='ghost' size='sm' onClick={() => onSort(column)}>
        {label}
        <Icon />
      </Button>
    </TableHead>
  )
}

export function AtlasList({
  items,
  sort,
  descending,
  onSort,
  page,
  onPage,
  selected,
  onSelect,
  typeLabel,
  locationName,
  query,
}: AtlasListProps) {
  const offset = (page - 1) * ATLAS_PAGE_SIZE
  const shown = items.slice(offset, offset + ATLAS_PAGE_SIZE)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='min-w-0 overflow-x-auto'>
        <Table>
          <TableHeader>
            <TableRow>
              <SortHead
                label='Name'
                column='name'
                sort={sort}
                descending={descending}
                onSort={onSort}
              />
              <SortHead
                label='Kind'
                column='type'
                sort={sort}
                descending={descending}
                onSort={onSort}
              />
              <SortHead
                label='Epoch'
                column='epoch'
                sort={sort}
                descending={descending}
                onSort={onSort}
              />
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((entity) => {
              const where = locationName(entity.location_id)
              return (
                <TableRow
                  key={entity.id}
                  data-state={selected === entity.id ? 'selected' : undefined}
                  aria-selected={selected === entity.id}
                  tabIndex={0}
                  onClick={() => onSelect(entity)}
                  onKeyDown={(event) =>
                    event.key === 'Enter' && onSelect(entity)
                  }
                  className='cursor-pointer'
                >
                  <TableCell className='max-w-0 min-w-40'>
                    <div className='flex min-w-0 items-center gap-2.5'>
                      <NodeAvatar
                        id={entity.id}
                        name={entity.name}
                        size='sm'
                        shape='square'
                      />
                      <div className='flex min-w-0 flex-col'>
                        <Text as='span' weight='medium' truncate>
                          <Highlight text={entity.name} query={query} />
                        </Text>
                        <Muted as='span' variant='caption' truncate>
                          {[entity.subtype, where]
                            .filter(Boolean)
                            .join(' · ') || typeLabel(entity.entity_type)}
                        </Muted>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className='flex min-w-0 items-center gap-1.5'>
                      <DomainIcon
                        vocabulary='entity-type'
                        value={entity.entity_type}
                        className='text-primary'
                      />
                      <Text as='span' variant='caption'>
                        {typeLabel(entity.entity_type)}
                      </Text>
                    </span>
                  </TableCell>
                  <TableCell>
                    <Text as='span' variant='caption'>
                      {formatInteger(entity.birth_epoch)}
                    </Text>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      <PageControls
        offset={offset}
        limit={ATLAS_PAGE_SIZE}
        total={items.length}
        onChange={(next) => onPage(Math.floor(next / ATLAS_PAGE_SIZE) + 1)}
        label='Atlas pages'
      />
    </div>
  )
}
