import { useState, useEffect } from 'react'

// Task storage (in-memory, persists to localStorage via hook)
let missionTasks = []

// Core exported functions matching what MissionOverview.jsx expects
export function getBySol(solNumber) {
  return missionTasks.filter((t) => t.sol === solNumber)
}

export function getAllTasks() {
  return [...missionTasks]
}

export function getTaskById(taskId) {
  return missionTasks.find((t) => t.id === taskId) || null
}

// React hook for task management in the UI
export function useTasks(initialTasks = []) {
  const [tasks, setTasks] = useState(() => {
    const stored = localStorage.getItem('missionTasks')
    return stored ? JSON.parse(stored) : initialTasks
  })

  useEffect(() => {
    localStorage.setItem('missionTasks', JSON.stringify(tasks))
  }, [tasks])

  // MissionOverview.jsx expects these exact function names
  const reload = () => setTasks(prev => prev)
  const addTask = (task) => {
    const id = `TASK-${String(Date.now()).padStart(4, '0')}`
    missionTasks.push({ id, sol: task.sol ?? 0, ...task })
    setTasks([...tasks, { id, sol: task.sol ?? 0, ...task }])
  }
  const update = (taskId, updates) => {
    const index = missionTasks.findIndex((t) => t.id === taskId)
    if (index === -1) return
    missionTasks[index] = { ...missionTasks[index], ...updates }
    setTasks(prev => prev.map(t => t.id === taskId ? { ...prev[tasks.findIndex(t2 => t2.id === taskId)] , ...updates } : t))
  }
  const remove = (taskId) => {
    const index = missionTasks.findIndex((t) => t.id === taskId)
    if (index === -1) return
    missionTasks.splice(index, 1)
    setTasks(prev => prev.filter(t => t.id !== taskId))
  }

  return {
    tasks,
    reload,
    create: addTask,
    update,
    remove,
    getBySol,
  }
}

// Default export for React component compatibility
export default function UseTasksProvider() {
  const { tasks, reload, getBySol } = useTasks()
  return { tasks, reload, getBySol }
}
