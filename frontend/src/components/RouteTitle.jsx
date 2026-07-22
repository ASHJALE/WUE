import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

function titleForPath(pathname) {
  if (pathname === '/') return 'Wood U Estimate'
  if (pathname === '/login') return 'Login'
  if (pathname === '/register') return 'Register'
  if (pathname === '/dashboard') return 'Dashboard'
  if (pathname === '/estimates/new') return 'Create Estimate'
  if (/^\/estimates\/[^/]+\/bom$/.test(pathname)) return 'BOM Preview'
  if (/^\/estimates\/[^/]+$/.test(pathname)) return 'Estimate Detail'
  if (pathname === '/estimates') return 'Estimates'
  if (pathname === '/bom') return 'Bill of Materials'
  if (pathname === '/quotations/new') return 'Create Quotation'
  if (/^\/quotations\/[^/]+$/.test(pathname)) return 'Quotation Detail'
  if (pathname === '/quotations') return 'Quotations'
  return 'Page Not Found'
}

export default function RouteTitle() {
  const { pathname } = useLocation()
  useEffect(() => {
    document.title = `${titleForPath(pathname)} | WUE`
  }, [pathname])
  return null
}
