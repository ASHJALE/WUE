import { Outlet } from 'react-router-dom'
import Footer from '../components/Footer.jsx'
import Navbar from '../components/Navbar.jsx'
import RouteTitle from '../components/RouteTitle.jsx'

function MainLayout() {
  return (
    <div className="app-shell">
      <RouteTitle />
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <Navbar />
      <main className="container flex-grow-1 py-4 py-lg-5" id="main-content">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

export default MainLayout
