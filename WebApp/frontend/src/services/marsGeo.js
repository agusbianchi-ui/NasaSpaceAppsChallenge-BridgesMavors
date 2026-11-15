export const MARS_RADIUS_METERS = 3396190

const DEGREES_TO_RADIANS = Math.PI / 180

function toRadians(value) {
  return value * DEGREES_TO_RADIANS
}

export function geodesicDistanceMeters(from, to) {
  const latitude1 = toRadians(from.latitude)
  const latitude2 = toRadians(to.latitude)
  const latitudeDelta = latitude2 - latitude1
  const longitudeDelta = toRadians(to.longitude - from.longitude)

  const haversine =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(latitude1) *
      Math.cos(latitude2) *
      Math.sin(longitudeDelta / 2) ** 2

  return 2 * MARS_RADIUS_METERS * Math.asin(Math.sqrt(haversine))
}

export function geodesicLengthMeters(points) {
  let total = 0

  for (let index = 1; index < points.length; index += 1) {
    total += geodesicDistanceMeters(points[index - 1], points[index])
  }

  return total
}
