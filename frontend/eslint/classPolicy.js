export const CLASS_FUNCTIONS = new Set(['cn', 'clsx', 'cva', 'twMerge'])

export const CONTROL_COMPONENTS = new Set([
  'Button',
  'Input',
  'Textarea',
  'SelectTrigger',
  'Toggle',
  'ToggleGroup',
  'ToggleGroupItem',
  'TabsList',
  'TabsTrigger',
  'Badge',
  'Switch',
  'Checkbox',
  'RadioGroupItem',
  'Kbd',
  'CommandInput',
  'Progress',
])

const TEXT_SIZE =
  /^text-(xs|sm|base|lg|xl|[2-9]xl|display|title|body|prose|caption|overline|kpi|control)$/
const TYPE_TUNING =
  /^(font-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)|leading-.+|tracking-.+)$/
const MARGIN = /^(m|mx|my|mt|mb|ms|me|ml|mr)-(?!auto$).+$|^space-[xy]-.+$/
const Z_INDEX = /^z-.+$/
const NUMERIC_SIZE = /^size-\d/
const CONTROL_BOX =
  /^(h|min-h|max-h|size|p|px|py|pt|pb|ps|pe|pl|pr|rounded|rounded-[a-z]+)(-.+)?$/

export function utilityOf(token) {
  const withoutVariants = token.split(':').at(-1) ?? token
  return withoutVariants.replace(/^!/, '').replace(/!$/, '').replace(/^-/, '')
}

export function classViolation(token, onControl) {
  if (token.includes('[')) return 'arbitrary'
  const utility = utilityOf(token)
  if (TEXT_SIZE.test(utility)) return 'textSize'
  if (TYPE_TUNING.test(utility)) return 'typeTuning'
  if (MARGIN.test(utility)) return 'margin'
  if (Z_INDEX.test(utility)) return 'zIndex'
  if (onControl && CONTROL_BOX.test(utility)) return 'controlBox'
  if (NUMERIC_SIZE.test(utility)) return 'numericSize'
  return null
}

export function tokensOf(text) {
  return text.split(/\s+/).filter(Boolean)
}
