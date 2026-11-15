import { ArrowLeft, Satellite } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="not-found">
      <Satellite size={32} aria-hidden="true" />
      <p className="page-heading__eyebrow">Signal lost</p>
      <h1>Section not found</h1>
      <p>
        The requested operations screen does not exist in this simulation
        environment.
      </p>
      <Link className="button-link" to="/">
        <ArrowLeft size={16} aria-hidden="true" />
        Return to Mission Overview
      </Link>
    </div>
  )
}
