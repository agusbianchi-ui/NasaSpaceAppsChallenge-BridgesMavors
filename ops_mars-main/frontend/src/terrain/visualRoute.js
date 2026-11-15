// Exact grid-line traversal; no smoothing or interpolation of terrain heights.
export function traceVisualSegment(grid, start, end, clearance = 8) {
  const { cellSize, originX, originZ, rows, columns } = grid.metadata
  if (!grid.isValidTerrainPosition(start.x,start.z) || !grid.isValidTerrainPosition(end.x,end.z)) return { vertices: [], error: 'A route point is outside valid terrain.' }
  const startHeight=grid.boundaryHeight(start.x,start.z),endHeight=grid.boundaryHeight(end.x,end.z)
  if(startHeight===null||endHeight===null)return {vertices:[],error:'A route endpoint touches an invalid edge or corner.'}
  const dx=end.x-start.x, dz=end.z-start.z, length=Math.hypot(dx,dz)
  if (length < 1e-9) return { vertices:[[start.x,grid.getVisualElevation(start.x,start.z)+clearance,start.z]], error:null }
  const cuts=[0,1]
  for (const [a,d,origin,count] of [[start.x,dx,originX,columns],[start.z,dz,originZ,rows]]) {
    if (Math.abs(d)<1e-12) continue
    for(let k=1;k<count;k++){const t=(origin+k*cellSize-a)/d;if(t>1e-10&&t<1-1e-10)cuts.push(t)}
  }
  cuts.sort((a,b)=>a-b)
  const ts=cuts.filter((t,i)=>!i||t-cuts[i-1]>1e-9), intervals=[]
  for(let i=0;i<ts.length-1;i++){
    const a=ts[i],b=ts[i+1],t=(a+b)/2,h=grid.boundaryHeight(start.x+t*dx,start.z+t*dz)
    if(h===null) return build(intervals,`Route interrupted at an invalid cell (section ${i+1}).`)
    const boundary=i ? grid.boundaryHeight(start.x+a*dx,start.z+a*dz) : h
    if(boundary===null)return build(intervals,'Route interrupted at an invalid edge or corner.')
    intervals.push({a,b,h,boundary})
  }
  return build(intervals,null)
  function build(intervals,error){
    const vertices=[]
    const add=(t,h)=>{const p=[start.x+t*dx,h+clearance,start.z+t*dz];const last=vertices.at(-1);if(!last||p.some((v,i)=>v!==last[i]))vertices.push(p)}
    intervals.forEach((cell,i)=>{
      if(!i){
        add(cell.a,Math.max(cell.h,startHeight))
        if(startHeight>cell.h){const eps=Math.min(1/length,(cell.b-cell.a)/4);add(cell.a+eps,startHeight);add(cell.a+eps,cell.h)}
      }
      if(i){
        const previous=intervals[i-1],eps=Math.min(1/length,(previous.b-previous.a)/4,(cell.b-cell.a)/4)
        const high=Math.max(previous.h,cell.h,cell.boundary)
        add(cell.a-eps,previous.h);add(cell.a-eps,high);add(cell.a+eps,high);add(cell.a+eps,cell.h)
      }
      if(i===intervals.length-1){
        if(!error && endHeight>cell.h){const eps=Math.min(1/length,(cell.b-cell.a)/4);add(cell.b-eps,cell.h);add(cell.b-eps,endHeight);add(cell.b,endHeight)}
        else add(cell.b,cell.h)
      }
    })
    return {vertices,error}
  }
}
export function buildVisualRoute(grid, points) {
  const vertices=[]
  for(let i=1;i<points.length;i++){
    const segment=traceVisualSegment(grid,points[i-1],points[i]);vertices.push(...segment.vertices)
    if(segment.error)return {vertices,error:`Segment ${i}: ${segment.error}`}
  }
  return {vertices,error:null}
}
export function importPreliminaryRoute(data, grid) {
  if(data.source!=='MapaMarteN.glb'||!Array.isArray(data.points)||data.points.length<2)throw new Error('Unsupported preliminary route source.')
  return data.points.map((p,i)=>{
    const y=grid.getVisualElevation(p.x,p.z)
    if(y===null||!Number.isFinite(p.y)||Math.abs(y-p.y)>0.01)throw new Error(`Preliminary point ${i+1} does not match the visual surface.`)
    return {id:`reference-${i+1}`,label:`Reference ${i+1}`,type:i===0?'Start':i===data.points.length-1?'Destination':'Waypoint',x:p.x,y,z:p.z}
  })
}
