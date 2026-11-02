export function epochScopeText(
  waiting: number,
  mortalAgents: number | null
): string {
  const mortals =
    mortalAgents === null
      ? 'the mortal agents'
      : `${mortalAgents} mortal agents`
  return `Completing runs ${waiting} son turns, ${mortals}, the world engine, then Fate and the chronicler; growth, faith and essence follow.`
}
