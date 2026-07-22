import { Route, Routes } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout.jsx'
import ProtectedRoute from '../components/ProtectedRoute.jsx'
import PublicOnlyRoute from '../components/PublicOnlyRoute.jsx'
import BOM from '../pages/BOM.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import Estimates from '../pages/Estimates.jsx'
import EstimateCreate from '../pages/EstimateCreate.jsx'
import EstimateDetail from '../pages/EstimateDetail.jsx'
import Home from '../pages/Home.jsx'
import Login from '../pages/Login.jsx'
import NotFound from '../pages/NotFound.jsx'
import Quotations from '../pages/Quotations.jsx'
import Register from '../pages/Register.jsx'

function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route element={<PublicOnlyRoute />}>
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Register />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="estimates" element={<Estimates />} />
          <Route path="estimates/new" element={<EstimateCreate />} />
          <Route path="estimates/:id" element={<EstimateDetail />} />
          <Route path="bom" element={<BOM />} />
          <Route path="quotations" element={<Quotations />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
