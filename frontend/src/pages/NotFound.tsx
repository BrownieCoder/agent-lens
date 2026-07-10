import { Link } from "react-router-dom";

export function NotFound() {
  return <section className="notice"><p className="eyebrow">404</p><h1>Page not found</h1><p>The requested Agent Lens page does not exist.</p><Link className="button" to="/">Return to dashboard</Link></section>;
}
