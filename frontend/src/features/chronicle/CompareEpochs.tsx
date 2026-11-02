import { useState } from 'react'
import { ArrowLeftRight, HandHeart } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ChangeChip, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  HARMFUL_STATS,
  type NumericStat,
  STAT_ICON,
} from '@/features/overview/statFields'
import { type EpochListItem, type EpochStatistics } from './api'
import { DELTA_FIELDS, DELTA_LABEL, sonFaithTotal } from './statDelta'

type CompareEpochsProps = {
  stats: EpochStatistics[]
  epochs: EpochListItem[]
}

const MIN_SNAPSHOTS = 2

function EpochSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: number
  options: EpochStatistics[]
  onChange: (epoch: number) => void
}) {
  return (
    <Select
      value={String(value)}
      onValueChange={(next) => onChange(Number(next))}
    >
      <SelectTrigger aria-label={label} size='sm'>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((item) => (
          <SelectItem key={item.epoch} value={String(item.epoch)}>
            {item.live ? `Epoch ${item.epoch} (now)` : `Epoch ${item.epoch}`}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function CompareEpochs({ stats, epochs }: CompareEpochsProps) {
  const sorted = [...stats].sort((left, right) => left.epoch - right.epoch)
  const [first, setFirst] = useState<number | null>(null)
  const [second, setSecond] = useState<number | null>(null)
  if (sorted.length < MIN_SNAPSHOTS) return null
  const a =
    sorted.find((item) => item.epoch === first) ?? sorted[sorted.length - 2]
  const b =
    sorted.find((item) => item.epoch === second) ?? sorted[sorted.length - 1]
  const summary = (epoch: number) =>
    epochs.find((item) => item.epoch === epoch)?.summary
  const rows = [
    ...DELTA_FIELDS.map((field) => ({
      key: field,
      label: DELTA_LABEL[field],
      icon: STAT_ICON[field as NumericStat],
      harmful: HARMFUL_STATS.has(field as NumericStat),
      a: a.data[field],
      b: b.data[field],
    })),
    {
      key: 'faith',
      label: 'Faith of all sons',
      icon: HandHeart,
      harmful: false,
      a: sonFaithTotal(a),
      b: sonFaithTotal(b),
    },
  ]
  return (
    <Section
      id='chronicle-compare'
      title='Compare two epochs'
      description='How the world changed between two snapshots.'
      level={3}
      actions={
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <EpochSelect
            label='First epoch'
            value={a.epoch}
            options={sorted}
            onChange={setFirst}
          />
          <Button
            variant='ghost'
            size='icon-sm'
            aria-label='Swap the epochs'
            onClick={() => {
              setFirst(b.epoch)
              setSecond(a.epoch)
            }}
          >
            <ArrowLeftRight />
          </Button>
          <EpochSelect
            label='Second epoch'
            value={b.epoch}
            options={sorted}
            onChange={setSecond}
          />
        </div>
      }
    >
      <div className='min-w-0 overflow-x-auto'>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Measure</TableHead>
              <TableHead>{`Epoch ${a.epoch}`}</TableHead>
              <TableHead>{`Epoch ${b.epoch}`}</TableHead>
              <TableHead>Change</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.key}>
                <TableCell>
                  <span className='flex min-w-0 items-center gap-2'>
                    <row.icon
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                    <Text as='span'>{row.label}</Text>
                  </span>
                </TableCell>
                <TableCell>
                  <Text as='span'>{formatInteger(row.a)}</Text>
                </TableCell>
                <TableCell>
                  <Text as='span'>{formatInteger(row.b)}</Text>
                </TableCell>
                <TableCell>
                  <ChangeChip value={row.b - row.a} harmful={row.harmful} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {(summary(a.epoch) || summary(b.epoch)) && (
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          {[a.epoch, b.epoch].map((epoch) => (
            <div key={epoch} className='flex min-w-0 flex-col gap-1'>
              <Muted variant='caption'>{`Epoch ${epoch}`}</Muted>
              <Text>{summary(epoch) ?? 'No summary.'}</Text>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
