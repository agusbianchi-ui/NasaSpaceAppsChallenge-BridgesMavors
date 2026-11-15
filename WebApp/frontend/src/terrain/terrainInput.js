// Two-touch rotation uses the change in finger angle, not a two-finger drag.
export function touchDelta(previous, current) {
  const pair = (p) => ({ x: (p[0].x + p[1].x) / 2, y: (p[0].y + p[1].y) / 2,
    distance: Math.hypot(p[1].x - p[0].x, p[1].y - p[0].y),
    angle: Math.atan2(p[1].y - p[0].y, p[1].x - p[0].x) })
  const a = pair(previous), b = pair(current)
  return { zoom: a.distance / Math.max(1, b.distance), twist: Math.atan2(Math.sin(b.angle - a.angle), Math.cos(b.angle - a.angle)), tilt: b.y - a.y }
}

export function bindTerrainInput(canvas, actions) {
  const touches = new Map(), starts = new Map()
  let previous = [], timer = null, multi = false, held = false
  const clearHold = () => { clearTimeout(timer); timer = null }
  const down = (event) => {
    starts.set(event.pointerId, { x: event.clientX, y: event.clientY, moved: false })
    if (event.pointerType !== 'touch') return
    event.preventDefault(); event.stopImmediatePropagation(); canvas.setPointerCapture(event.pointerId)
    touches.set(event.pointerId, { x: event.clientX, y: event.clientY })
    previous = [...touches.values()]
    if (touches.size === 1) { multi = false; held = false; timer = setTimeout(() => { held = true; actions.inspect?.(event.clientX, event.clientY) }, 550) }
    else { multi = true; clearHold() }
  }
  const move = (event) => {
    const start = starts.get(event.pointerId)
    if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 6) { start.moved = true; clearHold() }
    if (event.pointerType !== 'touch' || !touches.has(event.pointerId)) return
    event.preventDefault(); event.stopImmediatePropagation()
    touches.set(event.pointerId, { x: event.clientX, y: event.clientY })
    const current = [...touches.values()]
    if (!held && current.length === previous.length) {
      if (current.length === 1 && start?.moved) actions.pan(current[0].x - previous[0].x, current[0].y - previous[0].y)
      else if (current.length === 2) actions.gesture(touchDelta(previous, current))
    }
    previous = current
  }
  const up = (event) => {
    const start = starts.get(event.pointerId)
    const cancelled = event.type === 'pointercancel'
    if (event.pointerType === 'touch') {
      event.preventDefault(); event.stopImmediatePropagation(); clearHold()
      touches.delete(event.pointerId); previous = [...touches.values()]
      if (!cancelled && !multi && !held && start && !start.moved) actions.place?.(event.clientX, event.clientY)
    } else if (!cancelled && start && !start.moved) {
      if (event.button === 2) actions.inspect?.(event.clientX, event.clientY)
      if (event.button === 0) actions.place?.(event.clientX, event.clientY)
    }
    starts.delete(event.pointerId)
  }
  const context = (event) => event.preventDefault()
  const listeners = [['pointerdown', down], ['pointermove', move], ['pointerup', up], ['pointercancel', up], ['contextmenu', context]]
  for (const [type, fn] of listeners) canvas.addEventListener(type, fn, { capture: true, passive: false })
  return () => { clearHold(); for (const [type, fn] of listeners) canvas.removeEventListener(type, fn, { capture: true }); touches.clear(); starts.clear() }
}
