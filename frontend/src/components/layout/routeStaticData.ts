import '@tanstack/react-router'

declare module '@tanstack/react-router' {
  interface StaticDataRouteOption {
    layout?: 'page' | 'canvas'
  }
}
