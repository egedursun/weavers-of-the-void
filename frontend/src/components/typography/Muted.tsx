import { Text, type TextProps } from './Text'

export function Muted(props: Omit<TextProps, 'tone'>) {
  return <Text {...props} tone='muted' />
}
