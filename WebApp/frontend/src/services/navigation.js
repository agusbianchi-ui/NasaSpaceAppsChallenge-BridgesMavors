import {
  BrainCircuit,
  Compass,
  FlaskConical,
  LayoutDashboard,
  Mountain,
  Route,
  Wind,
} from 'lucide-react'

export const NAV_ITEMS = [
  {
    path: '/',
    label: 'Mission Overview',
    description: 'Operational summary and simulated telemetry.',
    icon: LayoutDashboard,
    end: true,
  },
  {
    path: '/explorer',
    label: 'Mars Explorer',
    description: 'Surface reference and exploration points.',
    icon: Compass,
  },
  {
    path: '/terrain',
    label: 'Terrain Analysis',
    description: 'Simulated terrain hazards and traversability.',
    icon: Mountain,
  },
  {
    path: '/routes',
    label: 'Route Planner',
    description: 'Simulated traverse corridors and waypoints.',
    icon: Route,
  },
  {
    path: '/targets',
    label: 'Scientific Targets',
    description: 'Target catalogue and analysis status.',
    icon: FlaskConical,
  },
  {
    path: '/ai',
    label: 'AI Systems',
    description: 'Planned analysis and planning modules.',
    icon: BrainCircuit,
  },
  {
    path: '/aeolian',
    label: 'Aeolian Dynamics',
    description: 'Real Mars dataset metadata and observed dune migration.',
    icon: Wind,
  },
]

NAV_ITEMS.push({ path: '/kanban', label: 'Mission Tasks', description: 'Mission planning task board.', icon: Wind })

export function getSectionByPath(pathname) {
  return (
    NAV_ITEMS.find((item) => item.path === pathname) ??
    NAV_ITEMS.find(
      (item) => item.path !== '/' && pathname.startsWith(item.path),
    ) ??
    NAV_ITEMS[0]
  )
}
