// Prefer linking the agent's name to their site, falling back to email/phone if
// that's all RentCast gave us for this listing.
function agentNameHref(agent) {
  if (agent.website) return agent.website
  if (agent.email) return `mailto:${agent.email}`
  if (agent.phone) return `tel:${agent.phone}`
  return null
}

function ListingCard({ listing }) {
  const agent = listing.agent
  const agentHref = agent ? agentNameHref(agent) : null

  return (
    <div className="listing-card">
      <div className="listing-card-header">
        <span className="listing-rent">
          {listing.rent != null ? `$${listing.rent.toLocaleString()}/mo` : 'Rent unknown'}
        </span>
        {listing.is_new && <span className="tag tag-new">New</span>}
        <span className="listing-beds">
          {listing.beds != null ? `${listing.beds} bd` : ''}
          {listing.baths != null ? ` / ${listing.baths} ba` : ''}
        </span>
      </div>
      <div className="listing-address">{listing.address}</div>
      <div className="listing-tags">
        {(listing.near_locations ?? []).map((loc) => (
          <span key={loc.id} className="tag">
            {loc.walk_minutes} min from {loc.label}
          </span>
        ))}
      </div>
      {agent && (agent.name || agent.phone || agent.email) && (
        <div className="listing-agent">
          {agent.name &&
            (agentHref ? (
              <a href={agentHref} target="_blank" rel="noreferrer">
                {agent.name}
              </a>
            ) : (
              <span>{agent.name}</span>
            ))}
          {agent.phone && (
            <a className="agent-contact" href={`tel:${agent.phone}`}>
              {agent.phone}
            </a>
          )}
          {agent.email && (
            <a className="agent-contact" href={`mailto:${agent.email}`}>
              {agent.email}
            </a>
          )}
        </div>
      )}
      {listing.url && (
        <a href={listing.url} target="_blank" rel="noreferrer">
          View listing
        </a>
      )}
    </div>
  )
}

export default ListingCard
