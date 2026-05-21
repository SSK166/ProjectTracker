const STATUS_COLS = [
    "KLD Status",
    "Artwork Status", 
    "Artwork to Vendor Status",
    "Dispatch Status",
    "Cost Closure Status",
    "Project Status",
    "Connectivity Status",
    "PDF Approved"
]

const ALLOWED_VALUES = {
    "KLD Status": [
        "KLD Shared",
        "KLD Pending",
        "Approved"
    ],
    "Artwork Status": [
        "Received",
        "Not Received"
    ],

    "Cost Closure Status": [
        "Closed",
        "Initiated",
        "Pending"
    ],
    "Dispatch Status":[
        "Partial",
        "Yes",
        "No"
    ],

    "Project Status": [
        "Not Started",
        "In Progress",
        "Under Testing",
        "Approved",
        "On Hold"
    ],

    "Connectivity Status":[
        "Partial",
        "Yes",
        "No"
    ],
    "PDF Approved":[
        "Yes",
        "No",
        "Pending"
    ],
    "Artwork to Vendor Status":[
        "Delayed",
        "Correction",
        "Dispatched"
    ]
}

const GREEN_VALUES = ["Approved", "Closed", "Dispatched"]
const YELLOW_VALUES = ["In Progress", "KLD Shared", "Initiated"]
const RED_VALUES = ["Rejected", "Delayed", "Correction", "Not Received"]

let currentRowId = null
let currentProjectRows = []

async function loadProjects() {
    const res = await fetch("/api/projects")
    const projects = await res.json()

    const list = document.getElementById("project-list")
    list.innerHTML = ""
    
    // Create a container wrapper for the search layout
    const searchContainer = document.createElement("div")
    searchContainer.className = "search-container"
    
    const searchBox = document.createElement("input")
    searchBox.type = "text"
    searchBox.placeholder = "Search Project"
    searchBox.classList.add("search-box")
    
    const searchButton = document.createElement("button")
    searchButton.textContent = "Search"
    searchButton.classList.add("search-btn")

    // Append items together beautifully inside the container
    searchContainer.appendChild(searchBox)
    searchContainer.appendChild(searchButton)
    list.appendChild(searchContainer)

    const projectElements = []

    projects.forEach(name => {
        const div = document.createElement("div")
        div.className = "project-item"
        div.textContent = name
        div.onclick = () => {selectProject(name, div);
            switchTab('tracker')
        }
        
        list.appendChild(div)
        
        projectElements.push({ name: name.toLowerCase(), element: div, rawName: name })
    })

    const performSearch = () => {
        const filter = searchBox.value.toLowerCase()
        let matchedProject = null

        projectElements.forEach(item => {
            if (item.name.includes(filter)) {
                item.element.style.display = "" // Show it
                if (!matchedProject) {
                    matchedProject = item 
                }
            } else {
                item.element.style.display = "none" 
            }
        })

        if (matchedProject && filter.trim() !== "") {
            selectProject(matchedProject.rawName, matchedProject.element)
        }
    }

    searchBox.oninput = performSearch
    searchButton.onclick = performSearch
}

async function selectProject(name, el) {
    // highlight active
    document.querySelectorAll(".project-item").forEach(i => i.classList.remove("active"))
    el.classList.add("active")

    document.getElementById("selected-project-name").textContent = name

    const res = await fetch(`/api/projects/${encodeURIComponent(name)}`)
    const rows = await res.json()
    currentProjectRows = rows
    rows.forEach(r=>console.log(r["_health"]))
    renderTable(rows)
}

function renderTable(rows) {
    if (rows.length === 0) return

    // Build headers from first row keys
    const allKeys = Object.keys(rows[0]).filter(k=>k!="_health")
    const head = document.getElementById("table-head")
    const body = document.getElementById("table-body")

    head.innerHTML = `<tr>${allKeys.map(k => `<th>${k}</th>`).join("")}</tr>`
    body.innerHTML = ""

    rows.forEach(row => {
        const tr = document.createElement("tr")
        tr.className = "clickable"
        tr.onclick = () => openPanel(row)
        if(row._health=="red") tr.style.backgroundColor="#fd5a5a"
        allKeys.forEach(key => {
            const td = document.createElement("td")
            const val = row[key]
            td.textContent = val ?? "—"
            tr.appendChild(td)
        })

        body.appendChild(tr)
    })
}

function badgeClass(val) {
    if (GREEN_VALUES.includes(val))  return "badge-green"
    if (YELLOW_VALUES.includes(val)) return "badge-yellow"
    if (RED_VALUES.includes(val))    return "badge-red"
    return "badge-gray"
}

async function openPanel(row) {
    currentRowId = row.id
    document.getElementById("panel-title").textContent =
        `${row.project_name} — ${row.packaging_type} — ${row.packaging_option}`

    // fetch status and deadlines
    const [statusRes, deadlineRes] = await Promise.all([
        fetch(`/api/status/${row.id}`),
        fetch(`/api/deadlines/${row.id}`)
    ])
    const statusData = await statusRes.json()
    const deadlineData = await deadlineRes.json()

    // build lookup maps
    const statusMap = {}
    statusData.forEach(s => statusMap[s.column_name] = s.current_value ? s.current_value.trim() : "")
    const deadlineMap = {}
    deadlineData.forEach(d => deadlineMap[d.column_name] = d.deadline)

    const today = new Date().toISOString().split("T")[0]

    let html = `<div class="section-title">Read-only Info</div>`

    // show non-status fields as read only
    const skipKeys = ["id", "project_name","_health", "packaging_type", "packaging_option", ...STATUS_COLS]
    Object.entries(row).forEach(([key, val]) => {
        if (!skipKeys.includes(key)) {
            html += `<div class="field-group">
                <div class="field-label">${key}</div>
                <div class="field-readonly">${val ?? "—"}</div>
            </div>`
        }
    })

    html += `<div class="section-title">Status & Deadlines</div>`

    STATUS_COLS.forEach(col => {
        const currentVal = statusMap[col] ?? ""
        const deadline = deadlineMap[col] ?? ""

        let deadlineHint = ""
        if (deadline) {
            const isGreen = GREEN_VALUES.includes(currentVal)
            const isOverdue = today > deadline
            if (isOverdue && !isGreen) {
                deadlineHint = `<div class="overdue">⚠ Overdue — deadline was ${deadline}</div>`
            } else if (!isOverdue && isGreen) {
                deadlineHint = `<div class="on-time">✓ Completed on time</div>`
            }
        }

        const options = ALLOWED_VALUES[col] ?? []
        const optionHtml = options.map(o =>
            `<option value="${o}" ${o.toLowerCase() === currentVal.toLowerCase() ? "selected" : ""}>${o}</option>`
        ).join("")//create the dropdown options with each allowed value for the particular column
        //if the value is the current selected value add the selected attribute to the option

        html += `<div class="field-group">
            <div class="field-label">${col}</div>
            <select id="status_${col}" data-col="${col}">
                <option value="">— select —</option>
                ${optionHtml}
            </select>
            <input type="date" id="deadline_${col}" value="${deadline}" style="margin-top:6px">
            ${deadlineHint}
        </div>`
    })

    document.getElementById("panel-body").innerHTML = html
    document.getElementById("side-panel").classList.add("open")
    document.getElementById("overlay").classList.add("active")
}

function closePanel() {
    document.getElementById("side-panel").classList.remove("open")
    document.getElementById("overlay").classList.remove("active")
    currentRowId = null
}

async function savePanel() {
    const statusUpdates = {}
    const deadlineUpdates = {}

    STATUS_COLS.forEach(col => {
        const statusEl = document.getElementById(`status_${col}`)
        const deadlineEl = document.getElementById(`deadline_${col}`)
        if (statusEl) statusUpdates[col] = statusEl.value
        if (deadlineEl) deadlineUpdates[col] = deadlineEl.value
    })

    await Promise.all([
        fetch(`/api/status/${currentRowId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(statusUpdates)
        }),
        fetch(`/api/deadlines/${currentRowId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(deadlineUpdates)
        })
    ])

    closePanel()

    // refresh table
    const activeProject = document.querySelector(".project-item.active")
    if (activeProject) {
        const res = await fetch(`/api/projects/${encodeURIComponent(activeProject.textContent)}`)
        const rows = await res.json()
        renderTable(rows)
    }
}

async function loadAlerts() {
    const res = await fetch("/api/alerts")
    const alerts = await res.json()

    const bar = document.getElementById("alerts-bar")
    const list = document.getElementById("alerts-list")

    if (alerts.length === 0) {
        bar.style.display = "none"
        return
    }

    bar.style.display = "block"
    list.innerHTML = alerts.map(a =>
        `<div class="alert-item">
            ${a.project_name} — ${a.packaging_type} / ${a.packaging_option} — ${a.column_name} — deadline was ${a.deadline}
        </div>`
    ).join("")
}

function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"))
    document.getElementById("tab-tracker").style.display = "none"
    document.getElementById("tab-alerts").style.display = "none"

    if (tab === "tracker") {
        document.getElementById("tab-tracker").style.display = "flex"
        document.querySelector(".tab-btn:first-child").classList.add("active")
    } else {
        document.getElementById("tab-alerts").style.display = "flex"
        document.querySelector(".tab-btn:last-child").classList.add("active")
        loadAlerts()
    }
}

async function loadAlerts() {
    const res = await fetch("/api/alerts")
    const alerts = await res.json()

    const body = document.getElementById("alerts-body")

    if (alerts.length === 0) {
        body.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#888;padding:24px">No overdue items</td></tr>`
        return
    }

    body.innerHTML = alerts
        .sort((a, b) => a.deadline.localeCompare(b.deadline))
        .map(a => `
            <tr class="clickable" onclick="openPanelById(${a.project_id})">
                <td>${a.project_name}</td>
                <td>${a.packaging_type}</td>
                <td>${a.packaging_option}</td>
                <td>${a.column_name}</td>
                <td>${a.current_value ?? "—"}</td>
                <td style="color:#791F1F;font-weight:500">${a.deadline}</td>
            </tr>
        `).join("")
}

async function openPanelById(projectId) {
    const res = await fetch(`/api/projects/id/${projectId}`)
    const row = await res.json()
    openPanel(row)
}

loadProjects()
loadAlerts()


//do switchTab('tracker')