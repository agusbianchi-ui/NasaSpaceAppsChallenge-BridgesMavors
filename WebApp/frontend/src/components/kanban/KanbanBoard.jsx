import { useState, useEffect } from 'react'
import { API_BASE_URL } from '../../services/marsApi.js'

const COLUMNS = ['BACKLOG', 'TO_DO', 'IN_PROGRESS', 'DONE']

export default function KanbanBoard() {
  const [tasks, setTasks] = useState([])
  const [dragging, setDragging] = useState(null)
  const [, setOverColumn] = useState(null)
  const [editing, setEditing] = useState(null)
  const [showForm, setShowForm] = useState(false)

  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'Medium',
    status: 'BACKLOG',
    targetId: '',
    dueDate: '',
  })

  const [formTitle, setFormTitle] = useState('Nueva Tarea')

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API_BASE_URL}/api/v1/tasks/`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Failed to load tasks'); return response.json() })
      .then(setTasks).catch(error => { if (error.name !== 'AbortError') console.error(error) })
    return () => controller.abort()
  }, [])

  const API_BASE = API_BASE_URL

  // Fetch tasks from backend
  async function fetchTasks() {
    const res = await fetch(`${API_BASE}/api/v1/tasks/`)
    if (!res.ok) throw new Error('Failed to fetch tasks')
    return res.json()
  }

  // Create a new task
  async function createTaskAPI(task) {
    const res = await fetch(`${API_BASE}/api/v1/tasks/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(task),
    })
    if (!res.ok) throw new Error('Failed to create task')
    return res.json()
  }

  // Update a task
  async function updateTaskAPI(taskId, updates) {
    const res = await fetch(`${API_BASE}/api/v1/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (!res.ok) throw new Error('Failed to update task')
    return res.json()
  }

  // Delete a task
  async function deleteTaskAPI(taskId) {
    const res = await fetch(`${API_BASE}/api/v1/tasks/${taskId}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error('Failed to delete task')
    return res.json()
  }

  const loadTasks = async () => {
    try {
      const data = await fetchTasks()
      setTasks(data)
    } catch (error) {
      console.error('Error fetching tasks:', error)
      setTasks([])
    }
  }

  const columnClasses = {
    BACKLOG: 'kanban-column kanban-backlog',
    TO_DO: 'kanban-column kanban-todo',
    IN_PROGRESS: 'kanban-column kanban-in-progress',
    DONE: 'kanban-column kanban-done',
  }


  const statusClasses = {
    BACKLOG: 'status-backlog',
    TO_DO: 'status-todo',
    IN_PROGRESS: 'status-in-progress',
    DONE: 'status-done',
  }

  const handleDragStart = (event, task, column) => {
    setDragging({ task, column })
    event.target.style.opacity = '0.5'
  }

  const handleDragOver = (event) => {
    event.preventDefault()
    setOverColumn(event.target.closest('.kanban-column')?.id || null)
  }

  const handleDragLeave = () => {
    setOverColumn(null)
  }

  const handleDrop = (event, task, targetColumnId) => {
    event.preventDefault()
    setDragging(null)
    setOverColumn(null)
    const taskColumn = dragging?.column
    if (taskColumn !== targetColumnId) {
      updateTaskAPI(task.id, { status: targetColumnId }).then(() => {
        loadTasks()
      })
    }
    event.target.style.opacity = ''
  }

  const handleDelete = async (taskId) => {
    if (confirm('¿Estás seguro de eliminar esta tarea?')) {
      await deleteTaskAPI(taskId)
      loadTasks()
    }
  }

  const handleEdit = (task) => {
    setEditing(task.id)
    setFormTitle('Editar Tarea')
    setNewTask({
      title: task.title,
      description: task.description,
      priority: task.priority,
      status: task.status,
      targetId: task.target_id || '',
      dueDate: task.due_date || '',
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    if (editing) {
      await updateTaskAPI(editing, {
        title: newTask.title,
        description: newTask.description,
        priority: typeof newTask.priority === 'number' ? newTask.priority : ({ Low: 1, Medium: 2, High: 3, Critical: 4 }[newTask.priority] || 2),
        status: newTask.status,
        target_id: newTask.targetId || undefined,
        due_date: newTask.dueDate || undefined,
      })
      setEditing(null)
    } else {
      await createTaskAPI({
        title: newTask.title,
        description: newTask.description,
        priority: typeof newTask.priority === 'number' ? newTask.priority : ({ Low: 1, Medium: 2, High: 3, Critical: 4 }[newTask.priority] || 2),
        status: newTask.status,
        target_id: newTask.targetId || undefined,
        due_date: newTask.dueDate || undefined,
      })
    }
    setShowForm(false)
    setNewTask({
      title: '',
      description: '',
      priority: 'Medium',
      status: 'BACKLOG',
      targetId: '',
      dueDate: '',
    })
    loadTasks()
  }

  return (
    <div className="kanban-board">
      <div className="kanban-header">
        <h2>Kanban Board</h2>
        <button className="btn-new-task" onClick={() => setShowForm(true)}>
          + Nueva Tarea
        </button>
      </div>

      <div className="kanban-columns">
        {COLUMNS.map((column) => (
          <div
            key={column}
            className={columnClasses[column]}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className="kanban-column-header">
              <span>{column}</span>
              <span className="task-count">
                {tasks.filter((t) => t.status === column).length}
              </span>
            </div>

            <div className="kanban-cards">
              {tasks
                .filter((t) => t.status === column || (dragging && dragging.column === column))
                .map((task) => (
                  <div
                    key={task.id}
                    className={`kanban-card ${statusClasses[task.status]}`
                    }
                    onDragStart={(e) => handleDragStart(e, task, column)}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, task, column)}
                  >
                    <div className="kanban-card-header">
                      <span className="kanban-card-title">{task.title}</span>
                      <span className="kanban-card-priority ${priorityClasses[task.priority]}"
                        >{task.priority}</span
                      >
                    </div>
                    <div className="kanban-card-body">
                      <p className="kanban-card-description">{task.description}</p>
                      {task.targetId && task.targetId !== '' && (
                        <p className="kanban-card-target">
                          <strong>Objetivo Científico:</strong> ID: {task.targetId}
                        </p>
                        )}
                      <p className="kanban-card-due">Vence: {task.dueDate || 'Sin fecha'}</p>
                    </div>
                    <div className="kanban-card-actions">
                      <button
                        className="btn-action-small"
                        onClick={() => handleEdit(task)}
                        title="Editar"
                      />
                      <button
                        className="btn-action-small danger"
                        onClick={() => handleDelete(task.id)}
                        title="Eliminar"
                      />
                    </div>
                  </div>
                ))}
              {dragging && dragging.column && (
                <div
                  className="kanban-card drag-preview"
                  style={{
                    opacity: 0.8,
                    background: 'rgba(255,255,255,0.1)',
                    borderColor: 'var(--accent)',
                  }}
                >
                  <span>Arrastrando tarea...</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="kanban-form-overlay">
          <div className="kanban-form-card">
            <h3>{formTitle}</h3>
            <form
              onSubmit={async (e) => {
                e.preventDefault()
                await handleSave()
              }}
            >
              <div className="form-group">
                <label>Título de la tarea</label>
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) =>
                    setNewTask({ ...newTask, title: e.target.value })
                  }
                  placeholder="Describir la tarea"
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Prioridad</label>
                  <select
                    value={newTask.priority}
                    onChange={(e) =>
                      setNewTask({ ...newTask, priority: e.target.value })
                    }
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                    <option value="Critical">Critical</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Estado</label>
                  <select
                    value={newTask.status}
                    onChange={(e) =>
                      setNewTask({ ...newTask, status: e.target.value })
                    }
                  >
                    <option value="BACKLOG">Backlog</option>
                    <option value="TO_DO">To Do</option>
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="DONE">Done</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Objetivo Científico</label>
                <select
                  value={newTask.targetId || ''}
                  onChange={(e) =>
                    setNewTask({ ...newTask, targetId: e.target.value || '' })
                  }
                >
                  <option value="">Ningún objetivo</option>
                  <option value="JZ-001">JZ-001 - Delta Front Outcrop</option>
                  <option value="JZ-002">JZ-002 - Rim Carbonate Vein</option>
                  <option value="JZ-003">JZ-003 - Western Fan Deposit</option>
                  <option value="JZ-004">JZ-004 - Olivine Ridge</option>
                  <option value="JZ-005">JZ-005 - North Rim Scarp</option>
                </select>
              </div>
              <div className="form-group">
                <label>Fecha límite</label>
                <input
                  type="date"
                  value={newTask.dueDate || ''}
                  onChange={(e) =>
                    setNewTask({ ...newTask, dueDate: e.target.value || '' })
                  }
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-submit">
                  {editing ? 'Actualizar' : 'Crear Tarea'}
                </button>
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setShowForm(false)}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}