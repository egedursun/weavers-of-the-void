import {
  Bold,
  ChevronDown,
  Italic,
  Plus,
  Search,
  Settings,
  Underline,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { CONTROL_SIZES, type ControlSize } from '@/components/ui/control-size'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Label as FieldLabel } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Toggle } from '@/components/ui/toggle'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { FormRow, Section } from '@/components/domain'
import { Row, Specimen } from './Specimen'
import { LONG_NAME } from './fixtures'

const ICON_SIZE: Record<ControlSize, 'icon-sm' | 'icon' | 'icon-lg'> = {
  sm: 'icon-sm',
  default: 'icon',
  lg: 'icon-lg',
}

const SIZE_NAME: Record<ControlSize, string> = {
  sm: 'Small controls',
  default: 'Default controls',
  lg: 'Large controls',
}

function ControlRow({ size }: { size: ControlSize }) {
  return (
    <Specimen name={SIZE_NAME[size]}>
      <Row>
        <Button size={size}>
          <Plus />
          Summon
        </Button>
        <Button size={size} variant='outline'>
          Outline
        </Button>
        <Button size={size} variant='secondary'>
          Secondary
        </Button>
        <Button size={size} variant='ghost'>
          Ghost
        </Button>
        <Button size={size} variant='destructive'>
          Destroy
        </Button>
        <Button size={ICON_SIZE[size]} variant='outline' aria-label='Settings'>
          <Settings />
        </Button>
      </Row>
      <Row>
        <Input
          size={size}
          placeholder='Search the atlas'
          aria-label='Search the atlas'
          className='w-56'
        />
        <Select defaultValue='rare'>
          <SelectTrigger size={size} aria-label='Rarity' className='w-40'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value='common'>Common</SelectItem>
            <SelectItem value='rare'>Rare</SelectItem>
            <SelectItem value='mythic'>Mythic</SelectItem>
          </SelectContent>
        </Select>
        <Toggle size={size} variant='outline' aria-label='Bold'>
          <Bold />
        </Toggle>
        <ToggleGroup
          type='single'
          size={size}
          variant='outline'
          defaultValue='italic'
        >
          <ToggleGroupItem value='italic' aria-label='Italic'>
            <Italic />
          </ToggleGroupItem>
          <ToggleGroupItem value='underline' aria-label='Underline'>
            <Underline />
          </ToggleGroupItem>
        </ToggleGroup>
      </Row>
      <Tabs defaultValue='sons'>
        <TabsList size={size} aria-label={`${SIZE_NAME[size]} tabs`}>
          <TabsTrigger value='sons'>Sons</TabsTrigger>
          <TabsTrigger value='threads'>Threads</TabsTrigger>
          <TabsTrigger value='councils'>Councils</TabsTrigger>
        </TabsList>
      </Tabs>
    </Specimen>
  )
}

export function ControlSpecimens() {
  return (
    <Section
      title='Controls'
      description='Every control of one size shares one height, one font size and one icon size.'
      level={3}
    >
      {CONTROL_SIZES.map((size) => (
        <ControlRow key={size} size={size} />
      ))}
      <Specimen name='Long label'>
        <Row>
          <Button variant='outline' className='max-w-60'>
            {LONG_NAME}
          </Button>
          <Badge variant='secondary' className='max-w-40'>
            {LONG_NAME}
          </Badge>
        </Row>
      </Specimen>
      <Specimen name='Disabled with reason'>
        <Row>
          <Button disabled disabledReason='Not enough divine essence'>
            Bless
          </Button>
          <Button
            variant='outline'
            disabled
            disabledReason='An epoch is running'
          >
            Summon son
          </Button>
        </Row>
      </Specimen>
      <Specimen name='Form rows'>
        <FormRow label='World name' description='Shown in the header.'>
          {(id) => <Input id={id} defaultValue='Orvael' className='max-w-80' />}
        </FormRow>
        <FormRow label='Founding myth'>
          {(id) => (
            <Textarea
              id={id}
              defaultValue='A world made of salt; the seas are sweet, the soil is salty.'
            />
          )}
        </FormRow>
        <FormRow label='Fate judges'>
          {(id) => (
            <>
              <Switch id={id} defaultChecked />
              <FieldLabel htmlFor={id}>Every creation</FieldLabel>
            </>
          )}
        </FormRow>
        <FormRow label='Notify me'>
          {(id) => (
            <>
              <Checkbox id={id} defaultChecked />
              <FieldLabel htmlFor={id}>When a son dies</FieldLabel>
            </>
          )}
        </FormRow>
        <FormRow label='Lore language'>
          {(id) => (
            <RadioGroup
              id={id}
              defaultValue='english'
              className='flex flex-wrap gap-4'
            >
              <div className='flex items-center gap-2'>
                <RadioGroupItem id={`${id}-english`} value='english' />
                <FieldLabel htmlFor={`${id}-english`}>English</FieldLabel>
              </div>
              <div className='flex items-center gap-2'>
                <RadioGroupItem id={`${id}-turkish`} value='turkish' />
                <FieldLabel htmlFor={`${id}-turkish`}>Turkish</FieldLabel>
              </div>
            </RadioGroup>
          )}
        </FormRow>
      </Specimen>
      <Specimen name='Badges'>
        <Row>
          <Badge>Default</Badge>
          <Badge variant='secondary'>Secondary</Badge>
          <Badge variant='outline'>Outline</Badge>
          <Badge variant='success'>Ready</Badge>
          <Badge variant='warning'>Asleep</Badge>
          <Badge variant='destructive'>Exiled</Badge>
        </Row>
        <Row>
          <Badge size='sm'>Small</Badge>
          <Badge size='sm' variant='secondary'>
            Small
          </Badge>
          <Badge size='sm' variant='outline'>
            Small
          </Badge>
          <Kbd>Ctrl K</Kbd>
          <Kbd>?</Kbd>
        </Row>
      </Specimen>
      <Specimen name='Progress'>
        <Progress value={64} aria-label='Default progress' />
        <Progress
          value={32}
          tone='success'
          size='sm'
          aria-label='Small progress'
        />
        <Progress indeterminate aria-label='Indeterminate progress' />
      </Specimen>
      <Specimen name='Overlays'>
        <Row>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant='outline'>
                <Search />
                Hover for a tooltip
              </Button>
            </TooltipTrigger>
            <TooltipContent>Tooltips use the caption role.</TooltipContent>
          </Tooltip>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant='outline'>
                Menu
                <ChevronDown />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>Son</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Bless</DropdownMenuItem>
              <DropdownMenuItem>Exile</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Row>
      </Specimen>
    </Section>
  )
}
