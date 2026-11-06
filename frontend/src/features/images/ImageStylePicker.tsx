import { Check, PenLine } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { CUSTOM_STYLE_MAX, IMAGE_STYLES, type ImageStyle } from './imageStyles'

type ImageStylePickerProps = {
  value: ImageStyle
  custom: string
  onChange: (value: ImageStyle) => void
  onCustomChange: (custom: string) => void
}

export function ImageStylePicker({
  value,
  custom,
  onChange,
  onCustomChange,
}: ImageStylePickerProps) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div
        role='radiogroup'
        aria-label='Image style'
        className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'
      >
        {IMAGE_STYLES.map((option) => {
          const active = option.value === value
          return (
            <Button
              key={option.value}
              type='button'
              role='radio'
              aria-checked={active}
              variant='outline'
              size='card'
              onClick={() => onChange(option.value)}
              className={cn(active && 'border-primary/60 bg-primary/10')}
            >
              {option.sample ? (
                <img
                  src={option.sample}
                  alt={`${option.label} sample`}
                  loading='lazy'
                  className='aspect-square w-full rounded-md bg-muted object-cover'
                />
              ) : (
                <span className='flex aspect-square w-full items-center justify-center rounded-md border border-dashed bg-muted'>
                  <Medallion icon={PenLine} tone={active ? 'gold' : 'muted'} />
                </span>
              )}
              <span className='flex min-w-0 items-start gap-2'>
                <span className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='semibold' truncate>
                    {option.label}
                  </Text>
                  <Muted as='span' variant='caption' truncate={2}>
                    {option.hint}
                  </Muted>
                </span>
                {active && (
                  <Check
                    aria-hidden='true'
                    className='size-icon-sm shrink-0 text-primary'
                  />
                )}
              </span>
            </Button>
          )
        })}
      </div>
      {value === 'custom' && (
        <FormRow
          label='Custom style'
          description='How every image should look: medium, palette, era, artist movement.'
        >
          {(id) => (
            <div className='flex w-full min-w-0 flex-col gap-1'>
              <Textarea
                id={id}
                rows={3}
                maxLength={CUSTOM_STYLE_MAX}
                placeholder='For example: gouache poster art with flat shapes and a muted palette'
                value={custom}
                onChange={(event) => onCustomChange(event.target.value)}
              />
              <Muted variant='caption'>{`${custom.length} / ${CUSTOM_STYLE_MAX}`}</Muted>
            </div>
          )}
        </FormRow>
      )}
    </div>
  )
}
