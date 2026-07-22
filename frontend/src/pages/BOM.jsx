import { Link } from 'react-router-dom'
import { FaClipboardList } from 'react-icons/fa6'

export default function BOM() {
  return (
    <section className="card border-0 shadow-sm text-center app-empty-state"><div className="card-body p-5">
      <FaClipboardList className="text-success mb-3" size="2.5rem" aria-hidden="true" />
      <h1 className="h2">Bill of Materials</h1>
      <p className="text-secondary mx-auto">BOM previews belong to individual estimates. Choose an estimate to review its backend-calculated materials.</p>
      <Link className="btn btn-success" to="/estimates">Choose an estimate</Link>
    </div></section>
  )
}
