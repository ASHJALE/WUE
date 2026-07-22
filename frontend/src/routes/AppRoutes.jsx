import { Route, Routes } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout.jsx'
import BOM from '../pages/BOM.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import Estimates from '../pages/Estimates.jsx'
import Home from '../pages/Home.jsx'
import Login from '../pages/Login.jsx'
import NotFound from '../pages/NotFound.jsx'
import Quotations from '../pages/Quotations.jsx'

function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route path="login" element={<Login />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="estimates" element={<Estimates />} />
        <Route path="bom" element={<BOM />} />
        <Route path="quotations" element={<Quotations />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
