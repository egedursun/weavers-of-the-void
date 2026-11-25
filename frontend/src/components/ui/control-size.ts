export type ControlSize = 'sm' | 'default' | 'lg'

export const CONTROL_SIZES: readonly ControlSize[] = ['sm', 'default', 'lg']

export const controlHeight: Record<ControlSize, string> = {
  sm: 'h-control-sm',
  default: 'h-control-md',
  lg: 'h-control-lg',
}

export const controlMinHeight: Record<ControlSize, string> = {
  sm: 'min-h-control-sm',
  default: 'min-h-control-md',
  lg: 'min-h-control-lg',
}

export const controlSquare: Record<ControlSize, string> = {
  sm: 'size-control-sm',
  default: 'size-control-md',
  lg: 'size-control-lg',
}

export const controlIcon: Record<ControlSize, string> = {
  sm: '[&_svg:not([data-domain=sigil])]:size-icon-sm',
  default: '[&_svg:not([data-domain=sigil])]:size-icon-md',
  lg: '[&_svg:not([data-domain=sigil])]:size-icon-lg',
}

export const controlFieldPadding: Record<ControlSize, string> = {
  sm: 'px-2.5',
  default: 'px-3',
  lg: 'px-3.5',
}

export const controlText = 'text-control'
