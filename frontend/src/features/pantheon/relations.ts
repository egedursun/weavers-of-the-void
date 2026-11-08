type Lookup = (path: string) => number | undefined

export function relationLabel(value: number, rule: Lookup): string {
  const sibling = rule('core_rules.relation_sibling')
  const close = rule('core_rules.relation_close_friend')
  const friend = rule('core_rules.relation_friend')
  const cold = rule('core_rules.relation_cold')
  const enemy = rule('core_rules.relation_enemy')
  const blood = rule('core_rules.relation_blood_enemy')
  if (sibling !== undefined && value >= sibling) return 'Kinship'
  if (close !== undefined && value >= close) return 'Close friendship'
  if (friend !== undefined && value >= friend) return 'Friendship'
  if (blood !== undefined && value <= -blood) return 'Blood enmity'
  if (enemy !== undefined && value <= -enemy) return 'Enmity'
  if (cold !== undefined && value <= -cold) return 'Coldness'
  return 'Distance'
}

export function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}
