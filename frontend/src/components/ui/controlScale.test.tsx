import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { Badge } from './badge'
import { Button } from './button'
import { CONTROL_SIZES, type ControlSize } from './control-size'
import { Input } from './input'
import { Select, SelectTrigger, SelectValue } from './select'
import { Tabs, TabsList, TabsTrigger } from './tabs'
import { Toggle } from './toggle'
import { ToggleGroup, ToggleGroupItem } from './toggle-group'

const ICON_SIZE = { sm: 'icon-sm', default: 'icon', lg: 'icon-lg' } as const

function Controls({ size }: { size: ControlSize }) {
  return (
    <div className='flex gap-2'>
      <Button size={size}>Summon</Button>
      <Button size={ICON_SIZE[size]} variant='outline' aria-label='Settings'>
        <svg viewBox='0 0 24 24' />
      </Button>
      <Input size={size} aria-label='Name' />
      <Select defaultValue='rare'>
        <SelectTrigger size={size} aria-label='Rarity'>
          <SelectValue placeholder='Rarity' />
        </SelectTrigger>
      </Select>
      <Toggle size={size} aria-label='Bold'>
        B
      </Toggle>
      <ToggleGroup type='single' size={size}>
        <ToggleGroupItem value='a'>A</ToggleGroupItem>
      </ToggleGroup>
      <Tabs defaultValue='a'>
        <TabsList size={size}>
          <TabsTrigger value='a'>Sons</TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  )
}

function measure(size: ControlSize) {
  return Array.from(
    document.querySelectorAll(`[data-control-size="${size}"]`)
  ).map((element) => ({
    slot: element.getAttribute('data-slot'),
    height: element.getBoundingClientRect().height,
    fontSize: getComputedStyle(element).fontSize,
  }))
}

describe('control size scale', () => {
  for (const size of CONTROL_SIZES) {
    it(`gives every ${size} control one height and one font size`, async () => {
      await render(<Controls size={size} />)
      const measured = measure(size)
      expect(measured.map((item) => item.slot).sort()).toEqual(
        [
          'button',
          'button',
          'input',
          'select-trigger',
          'tabs-list',
          'toggle',
          'toggle-group-item',
        ].sort()
      )
      expect(new Set(measured.map((item) => item.height)).size).toBe(1)
      expect(new Set(measured.map((item) => item.fontSize)).size).toBe(1)
    })
  }

  it('orders the sizes from small to large', async () => {
    await render(
      <>
        {CONTROL_SIZES.map((size) => (
          <Button key={size} size={size}>
            {size}
          </Button>
        ))}
      </>
    )
    const heights = CONTROL_SIZES.map((size) => measure(size)[0].height)
    expect([...heights].sort((a, b) => a - b)).toEqual(heights)
    expect(new Set(heights).size).toBe(CONTROL_SIZES.length)
  })

  it('sizes icons by the control, not by the icon', async () => {
    await render(
      <Button size='lg'>
        <svg data-testid='icon' className='size-10' viewBox='0 0 24 24' />
        Summon
      </Button>
    )
    const icon = document.querySelector('[data-testid="icon"]') as SVGElement
    expect(icon.getBoundingClientRect().height).toBeLessThan(24)
  })

  it('gives badges of one size one height', async () => {
    await render(
      <>
        <Badge>Ready</Badge>
        <Badge variant='outline'>
          <svg viewBox='0 0 24 24' />
          Mythic
        </Badge>
      </>
    )
    const heights = Array.from(
      document.querySelectorAll('[data-badge-size="default"]')
    ).map((element) => element.getBoundingClientRect().height)
    expect(new Set(heights).size).toBe(1)
  })
})

describe('Button', () => {
  it('explains why it is disabled and stays focusable', async () => {
    const screen = await render(
      <Button disabled disabledReason='Not enough divine essence'>
        Bless
      </Button>
    )
    const button = screen.getByRole('button', { name: 'Bless' })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
    await expect.element(button).not.toHaveAttribute('disabled')
    await expect
      .element(button)
      .toHaveAttribute('aria-description', 'Not enough divine essence')
  })

  it('truncates long text instead of overflowing', async () => {
    const screen = await render(
      <div className='w-40'>
        <Button>
          {'Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin'}
        </Button>
      </div>
    )
    const button = screen.getByRole('button').element()
    expect(button.getBoundingClientRect().width).toBeLessThanOrEqual(160)
  })
})
