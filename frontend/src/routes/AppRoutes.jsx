import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout.jsx'
import ProtectedRoute from '../components/ProtectedRoute.jsx'
import PublicOnlyRoute from '../components/PublicOnlyRoute.jsx'
import { LoadingState } from '../components/AppFeedback.jsx'

const BOM = lazy(() => import('../pages/BOM.jsx'))
const BomPreview = lazy(() => import('../pages/BomPreview.jsx'))
const Dashboard = lazy(() => import('../pages/Dashboard.jsx'))
const Estimates = lazy(() => import('../pages/Estimates.jsx'))
const EstimateCreate = lazy(() => import('../pages/EstimateCreate.jsx'))
const EstimateDetail = lazy(() => import('../pages/EstimateDetail.jsx'))
const Home = lazy(() => import('../pages/Home.jsx'))
const Login = lazy(() => import('../pages/Login.jsx'))
const NotFound = lazy(() => import('../pages/NotFound.jsx'))
const Quotations = lazy(() => import('../pages/Quotations.jsx'))
const QuotationCreate = lazy(() => import('../pages/QuotationCreate.jsx'))
const QuotationDetail = lazy(() => import('../pages/QuotationDetail.jsx'))
const Register = lazy(() => import('../pages/Register.jsx'))

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingState label="Loading page…" />}>
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
          <Route path="estimates/:id/bom" element={<BomPreview />} />
          <Route path="bom" element={<BOM />} />
          <Route path="quotations" element={<Quotations />} />
          <Route path="quotations/new" element={<QuotationCreate />} />
          <Route path="quotations/:id" element={<QuotationDetail />} />
        </Route>
        <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default AppRoutes
