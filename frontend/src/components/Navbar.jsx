import { NavLink, useNavigate } from 'react-router-dom'
import { FaCouch } from 'react-icons/fa'
import { useAuth } from '../context/AuthContext.jsx'

const authenticatedLinks = [
  ['/dashboard', 'Dashboard'],
  ['/estimates', 'Estimates'],
  ['/bom', 'BOM'],
  ['/quotations', 'Quotations'],
]

function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark" aria-label="Main navigation">
      <div className="container">
        <NavLink className="navbar-brand d-flex align-items-center gap-2" to="/">
          <FaCouch aria-hidden="true" />
          <span>WUE</span>
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
            {(isAuthenticated ? authenticatedLinks : [['/', 'Home']]).map(([path, label]) => (
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
            {isAuthenticated ? (
              <>
                <li className="nav-item ms-lg-2">
                  <span className="navbar-text text-light" aria-label={`Signed in as ${user.username}`}>{user.username}</span>
                </li>
                <li className="nav-item ms-lg-2">
                  <button className="btn btn-outline-light btn-sm" onClick={handleLogout} title="Sign out of WUE" type="button">Logout</button>
                </li>
              </>
            ) : (
              <>
                <li className="nav-item ms-lg-2"><NavLink className="nav-link" to="/login">Login</NavLink></li>
                <li className="nav-item"><NavLink className="btn btn-outline-light btn-sm" to="/register">Register</NavLink></li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
