export const APP_BASE = import.meta.env.BASE_URL || '/'

export function withBasePath(path: string): string {
  if (!path) {
    return APP_BASE
  }
  const base = APP_BASE.endsWith('/') ? APP_BASE.slice(0, -1) : APP_BASE
  const normalized = path.startsWith('/') ? path : `/${path}`
  if (!base) {
    return normalized
  }
  return `${base}${normalized}`
}
