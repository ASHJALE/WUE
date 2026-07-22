import { FaCompass } from 'react-icons/fa'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/AppFeedback.jsx'

export default function NotFound() {
  return (
    <EmptyState
      action={<Link className="btn btn-success" to="/">Return home</Link>}
      description="The page may have moved, or the address may be incorrect."
      icon={FaCompass}
      title="Page not found"
    />
  )
}
