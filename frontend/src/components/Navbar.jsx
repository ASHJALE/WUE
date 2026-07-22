import { NavLink } from 'react-router-dom'
import { FaCouch } from 'react-icons/fa'

const links = [
  ['/', 'Home'],
  ['/dashboard', 'Dashboard'],
  ['/estimates', 'Estimates'],
  ['/bom', 'BOM'],
  ['/quotations', 'Quotations'],
]

function Navbar() {
  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark" aria-label="Main navigation">
      <div className="container">
        <NavLink className="navbar-brand d-flex align-items-center gap-2" to="/">
          <FaCouch aria-hidden="true" />
          WUE
        </NavLink>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#mainNavbar"
          aria-controls="mainNavbar"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon" />
        </button>
        <div className="collapse navbar-collapse" id="mainNavbar">
          <ul className="navbar-nav ms-auto align-items-lg-center gap-lg-1">
            {links.map(([path, label]) => (
              <li className="nav-item" key={path}>
                <NavLink
                  className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                  end={path === '/'}
                  to={path}
                >
                  {label}
                </NavLink>
              </li>
            ))}
            <li className="nav-item ms-lg-2">
              <NavLink className="btn btn-outline-light btn-sm" to="/login">
                Login
              </NavLink>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
