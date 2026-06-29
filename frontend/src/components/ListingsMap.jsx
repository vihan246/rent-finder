import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// react-leaflet's default marker icon paths break under Vite's bundling unless
// re-pointed at the bundled asset URLs.
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const locationIcon = L.divIcon({
  className: 'location-marker',
  html: '<div class="location-marker-dot"></div>',
  iconSize: [16, 16],
})

const DEFAULT_CENTER = [37.7749, -122.4194]

function ListingsMap({ listings, locations }) {
  const points = [
    ...locations.filter((l) => l.lat != null && l.lng != null).map((l) => [l.lat, l.lng]),
    ...listings.filter((l) => l.lat != null && l.lng != null).map((l) => [l.lat, l.lng]),
  ]

  const bounds = points.length > 0 ? L.latLngBounds(points) : null
  const center = points.length > 0 ? points[0] : DEFAULT_CENTER

  return (
    <MapContainer
      center={center}
      zoom={13}
      style={{ height: '420px', width: '100%' }}
      {...(bounds ? { bounds } : {})}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      {locations
        .filter((loc) => loc.lat != null && loc.lng != null)
        .map((loc) => (
          <Marker key={loc.id} position={[loc.lat, loc.lng]} icon={locationIcon}>
            <Popup>
              <strong>{loc.label}</strong>
              <br />
              {loc.address}
            </Popup>
          </Marker>
        ))}
      {listings
        .filter((listing) => listing.lat != null && listing.lng != null)
        .map((listing) => (
          <Marker key={listing.id} position={[listing.lat, listing.lng]}>
            <Popup>
              <strong>{listing.rent != null ? `$${listing.rent.toLocaleString()}/mo` : 'Listing'}</strong>
              <br />
              {listing.address}
            </Popup>
          </Marker>
        ))}
    </MapContainer>
  )
}

export default ListingsMap
