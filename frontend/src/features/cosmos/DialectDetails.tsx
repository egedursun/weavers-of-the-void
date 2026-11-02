import { Badge } from '@/components/ui/badge'
import { KeyValueList } from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { type Phonology, dialectRows, dialectSummary } from './model/dialect'

export function DialectDetails({ phonology }: { phonology: Phonology }) {
  return (
    <div data-dialect className='flex min-w-0 flex-col gap-3'>
      <Text>{dialectSummary(phonology)}</Text>
      <KeyValueList
        items={dialectRows(phonology).map((row) => ({
          label: row.label,
          value: row.value,
        }))}
      />
      {phonology.sample_names.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Label>Names born here</Label>
          {phonology.sample_names.map((name) => (
            <Badge key={name} variant='secondary'>
              {name}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
