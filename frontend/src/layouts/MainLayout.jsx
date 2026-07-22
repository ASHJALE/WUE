import { Outlet } from 'react-router-dom'
import Footer from '../components/Footer.jsx'
import Navbar from '../components/Navbar.jsx'

function MainLayout() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="container flex-grow-1 py-5">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

export default MainLayout
