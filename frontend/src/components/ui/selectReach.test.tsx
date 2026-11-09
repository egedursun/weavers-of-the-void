import { useState } from 'react'
import '@/styles/index.css'
import { expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { page } from 'vitest/browser'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './select'

const ENDLESS = `Mirevast, the Drowned ${'Vaelorithanquedusk'.repeat(8)}`

function Chooser() {
  const [value, setValue] = useState('void')
  return (
    <div className='p-4'>
      <Select value={value} onValueChange={setValue}>
        <SelectTrigger aria-label='Where'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value='void'>In the void</SelectItem>
          <SelectItem value='long'>{ENDLESS}</SelectItem>
          <SelectItem value='short'>Oru</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}

it('keeps every option on screen and choosable beside a name longer than the screen', async () => {
  await page.viewport(360, 640)
  const screen = await render(<Chooser />)
  await screen.getByRole('combobox', { name: 'Where' }).click()
  const long = screen.getByRole('option', { name: ENDLESS })
  await expect.element(long).toBeVisible()
  await expect
    .poll(() => long.element().getBoundingClientRect().right)
    .toBeLessThanOrEqual(window.innerWidth)
  await expect
    .poll(() => screen.getByRole('listbox').element().scrollWidth)
    .toBeLessThanOrEqual(window.innerWidth)
  await screen.getByRole('option', { name: 'Oru' }).click()
  await expect
    .element(screen.getByRole('combobox', { name: 'Where' }))
    .toHaveTextContent('Oru')
})
