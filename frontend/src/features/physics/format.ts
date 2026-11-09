export function fixed(value: number, digits = 2): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(digits)
}

export function kelvinText(kelvin: number): string {
  return `${Math.round(kelvin)} K (${Math.round(kelvin - 273)} °C)`
}
