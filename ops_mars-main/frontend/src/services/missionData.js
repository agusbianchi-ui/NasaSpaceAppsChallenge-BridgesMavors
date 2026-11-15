export const SIMULATION_NOTICE =
  'Simulated demonstration data. No human mission is currently active at Jezero Crater.'

export const missionProfile = {
  name: 'MARS OPS',
  missionId: 'SIM-01',
  phase: 'Pre-mission planning',
  location: 'Jezero Crater',
  region: 'Northeast Syrtis Major, Mars',
  timeZone: 'UTC',
}

export const overviewMetrics = [
  {
    id: 'status',
    label: 'Mission Status',
    value: 'Pre-mission planning',
    meta: 'Simulated operations profile',
    tone: 'accent',
  },
  {
    id: 'area',
    label: 'Exploration Area',
    value: 'Jezero Crater',
    meta: '18.38° N · 77.58° E',
  },
  {
    id: 'targets',
    label: 'Scientific Targets',
    value: '8',
    meta: '4 analyzed · 2 in review · 2 pending',
  },
  {
    id: 'risk',
    label: 'Terrain Risk',
    value: 'Moderate',
    meta: 'Simulated hazard index 2.4 / 5',
    tone: 'warning',
  },
  {
    id: 'progress',
    label: 'Mission Progress',
    value: '42%',
    meta: 'Planning phase · simulated',
    tone: 'progress',
  },
]

export const missionProgress = {
  value: 42,
  label: 'Simulated planning progress',
  phases: [
    { id: 'phase-1', label: 'Site characterization', value: 72 },
    { id: 'phase-2', label: 'Target review', value: 48 },
    { id: 'phase-3', label: 'Traverse planning', value: 31 },
    { id: 'phase-4', label: 'Systems readiness', value: 18 },
  ],
}

export const exploration = {
  area: 'Jezero Crater',
  region: 'Northeast Syrtis Major, Mars',
  coordinates: [
    { label: 'Latitude', value: '18.38° N' },
    { label: 'Longitude', value: '77.58° E' },
    { label: 'Reference', value: 'JZ-REF-001' },
  ],
  pointSummary: [
    { label: 'Mapped points', value: '8' },
    { label: 'Analyzed', value: '4' },
    { label: 'Queued', value: '2' },
  ],
  points: [
    { id: 'JZ-001', label: 'Delta Front', x: 62, y: 44 },
    { id: 'JZ-003', label: 'Western Fan', x: 38, y: 58 },
    { id: 'JZ-005', label: 'North Rim', x: 52, y: 24 },
    { id: 'JZ-008', label: 'Clay Unit', x: 30, y: 40 },
  ],
  note: 'Marker positions are illustrative and are not georeferenced.',
}

export const surfaceVisualization = {
  title: 'MARS SURFACE',
  subtitle: 'TERRAIN EXPLORATION',
  indicator: 'VISUALIZATION',
  description:
    'A simulated traverse links science waypoints across the Jezero Crater terrain, illustrating how exploration planning could connect surface targets for interface demonstration.',
  note: 'Illustrative · Not an operational route',
  alt: 'Animated illustration of the Martian surface with a simulated exploration route crossing rocky terrain toward science waypoints.',
}

export const telemetryMetrics = [
  {
    id: 'temperature',
    label: 'Temperature',
    value: '−63',
    unit: '°C',
    trend: '−2.4 vs previous sample',
  },
  {
    id: 'pressure',
    label: 'Atmospheric Pressure',
    value: '610',
    unit: 'Pa',
    trend: '+3.1 vs previous sample',
  },
  {
    id: 'wind',
    label: 'Wind Speed',
    value: '14',
    unit: 'm/s',
    trend: '+1.8 vs previous sample',
  },
  {
    id: 'elevation',
    label: 'Elevation',
    value: '−2,600',
    unit: 'm',
    trend: 'Stable reference value',
  },
]

export const telemetrySeries = {
  label: 'Simulated temperature trend',
  unit: '°C',
  labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
  values: [-71, -70, -68, -63, -58, -61, -66, -69],
}

export const scientificTargets = [
  {
    id: 'JZ-001',
    name: 'Delta Front Outcrop',
    type: 'Sedimentary',
    status: 'Analyzed',
    confidence: 'High',
  },
  {
    id: 'JZ-002',
    name: 'Rim Carbonate Vein',
    type: 'Mineral',
    status: 'In review',
    confidence: 'Medium',
  },
  {
    id: 'JZ-003',
    name: 'Western Fan Deposit',
    type: 'Sedimentary',
    status: 'Analyzed',
    confidence: 'High',
  },
  {
    id: 'JZ-004',
    name: 'Olivine Ridge',
    type: 'Geologic',
    status: 'Pending',
    confidence: 'Low',
  },
  {
    id: 'JZ-005',
    name: 'North Rim Scarp',
    type: 'Geologic',
    status: 'Analyzed',
    confidence: 'Medium',
  },
  {
    id: 'JZ-006',
    name: 'Clay-Bearing Unit',
    type: 'Mineral',
    status: 'In review',
    confidence: 'Medium',
  },
  {
    id: 'JZ-007',
    name: 'Paleochannel Bed',
    type: 'Sedimentary',
    status: 'Pending',
    confidence: 'Low',
  },
  {
    id: 'JZ-008',
    name: 'Ejecta Margin',
    type: 'Geologic',
    status: 'Analyzed',
    confidence: 'High',
  },
]

export const missionActivity = [
  {
    id: 'ACT-1042',
    time: '10:42 UTC',
    title: 'Terrain raster simulation refreshed',
    detail: 'Jezero Crater sector JZ-NE updated in the demo environment.',
    status: 'Complete',
  },
  {
    id: 'ACT-1041',
    time: '10:18 UTC',
    title: 'Target JZ-003 queued for spectral review',
    detail: 'Simulated analysis pipeline accepted the request.',
    status: 'Running',
  },
  {
    id: 'ACT-1040',
    time: '09:55 UTC',
    title: 'Route corridor candidate generated',
    detail: 'Demo planner produced a 4.2 km corridor near the delta front.',
    status: 'Complete',
  },
  {
    id: 'ACT-1039',
    time: '09:31 UTC',
    title: 'Comms window simulation completed',
    detail: 'Relay availability window logged for planning purposes.',
    status: 'Complete',
  },
  {
    id: 'ACT-1038',
    time: '09:04 UTC',
    title: 'Terrain hazard index recalculated',
    detail: 'Simulated index moved from 2.2 to 2.4 / 5.',
    status: 'Warning',
  },
]

export const operationsStatus = [
  { id: 'planning', label: 'Planning pipeline', value: 'Nominal', tone: 'ok' },
  { id: 'link', label: 'Simulation link', value: 'Standby', tone: 'accent' },
  { id: 'queue', label: 'Analysis queue', value: '2 active', tone: 'accent' },
]

export const terrainMetrics = [
  {
    id: 'slope',
    label: 'Mean Slope',
    value: '6.8°',
    detail: 'Simulated surface average',
  },
  {
    id: 'hazard',
    label: 'Hazard Index',
    value: '2.4 / 5',
    detail: 'Simulated composite score',
  },
  {
    id: 'corridor',
    label: 'Traversable Corridor',
    value: '68%',
    detail: 'Simulated route coverage',
  },
  {
    id: 'rocks',
    label: 'Rock Density',
    value: 'Moderate',
    detail: 'Simulated surface category',
  },
]

export const terrainRiskSeries = {
  label: 'Simulated hazard score',
  labels: ['Slope', 'Rocks', 'Dunes', 'Thermal', 'Visibility'],
  values: [38, 54, 27, 62, 43],
  note: 'Scores are synthetic and intended only for interface demonstration.',
}

export const routeSummary = [
  { id: 'length', label: 'Route Length', value: '4.2 km' },
  { id: 'duration', label: 'Estimated Duration', value: '3.5 h' },
  { id: 'hazard', label: 'Maximum Hazard', value: 'Moderate' },
]

export const routeWaypoints = [
  {
    id: 'WP-01',
    name: 'Landing Zone Alpha',
    coordinates: '18.44° N · 77.45° E',
    distance: '0.0 km',
    risk: 'Low',
  },
  {
    id: 'WP-02',
    name: 'Delta Approach',
    coordinates: '18.41° N · 77.52° E',
    distance: '1.8 km',
    risk: 'Low',
  },
  {
    id: 'WP-03',
    name: 'Western Fan Shelf',
    coordinates: '18.39° N · 77.58° E',
    distance: '3.1 km',
    risk: 'Moderate',
  },
  {
    id: 'WP-04',
    name: 'Clay Unit Sample',
    coordinates: '18.37° N · 77.61° E',
    distance: '4.2 km',
    risk: 'Moderate',
  },
]

export const routeNote =
  'Simulated traverse plan. Coordinates, distances, and risk levels are illustrative only.'

export const aiSystems = [
  {
    id: 'AI-01',
    name: 'Terrain Classifier',
    description:
      'Classifies simulated surface units from demonstration imagery.',
    status: 'Prototype',
    mode: 'Not connected',
  },
  {
    id: 'AI-02',
    name: 'Route Optimizer',
    description:
      'Scores candidate corridors against simulated terrain hazards.',
    status: 'Design',
    mode: 'Not connected',
  },
  {
    id: 'AI-03',
    name: 'Target Prioritizer',
    description:
      'Ranks scientific targets using synthetic planning heuristics.',
    status: 'Concept',
    mode: 'Not connected',
  },
  {
    id: 'AI-04',
    name: 'Anomaly Monitor',
    description:
      'Flags unusual patterns in simulated telemetry streams.',
    status: 'Prototype',
    mode: 'Not connected',
  },
]
