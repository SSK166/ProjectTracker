const originalFetch = window.fetch;
window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    if (response.url && response.url.includes('msg=')) {
        const urlObj = new URL(response.url);
        window.location.href = `/${urlObj.search}`;
        return response;
    }
    if (response.status === 403) {
        window.location.href = '/?msg=Access+Denied:+Insufficient+permissions+for+Growth+Tracker.';
        return response;
    }
    return response;
};
const STATUS_COLS = [
    "KLD Status",
    "Artwork Status",
    "Sampling Status",
    "Commercial Ordering Status",
    "Connectivity Status"
]

const FREE_TEXT_COLS=["Project Status"]

const ALLOWED_VALUES = {
    "KLD Status": [
        "Not Shared",
        "KLD Shared",
        "In Progress"
    ],
    "Artwork Status": [
        "Received",
        "Not Received"
    ],

    "Sampling Status":[
        "Completed",
        "In Progress"
    ],

    "Commercial Ordering Status": [
        "Completed",
        "In Progress"
    ],
    "Connectivity Status":[
        "Connected",
        "In Progress"
    ]
}

const GREEN_VALUES = ["Received", "Connected", "Completed", "KLD Shared"]
const RED_VALUES = ["In Progress", "Not Received"]

let currentRowId = null
let currentProjectRows = []

//for search matching
function normalize(str) {
    return str
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
}

async function loadProjects() {
    const res = await fetch("/growth/api/projects")
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
        const filter = normalize(searchBox.value)
        let matchedProject = null

        projectElements.forEach(item => {
            const normname=normalize(item.name)
            if (normname.includes(filter)) {
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

    const res = await fetch(`/growth/api/projects/${encodeURIComponent(name)}`)
    const rows = await res.json()
    const alertsProject=await fetch(`/growth/api/alerts/${encodeURIComponent(name)}`)
    const alerts=await alertsProject.json()
    const dueRes=await fetch(`/growth/api/due-today/${encodeURIComponent(name)}`)
    const dues=await dueRes.json()
    currentProjectRows = rows
    //to make the alerts and due today for the projects visible on selection
    document.getElementById("project-alerts").style.display = "flex"
    document.getElementById("project-alerts-table").style.display = "table"
    document.getElementById("project-today").style.display = "flex"
    document.getElementById("project-today-table").style.display = "table"
    renderTable(rows)
    renderAlerts(alerts)
    renderDueToday(dues)
}

function isFullyGreen(row) {
    const val = row["Project Status"]
    return val != null && val.trim().toLowerCase() === "completed"
}

function toTitleCase(str) {
    if (str == null || str === "") return str
    str = String(str)  // coerce numbers etc. to string
    return str.split(' ').filter(s => s !== '').map(s => {
        if (s === s.toUpperCase()) return s  // preserve fully caps words like "KLD"
        return s[0].toUpperCase() + s.slice(1).toLowerCase()
    }).join(" ")
}


function renderTable(rows) {
    if (rows.length === 0) return
    // Build headers from first row keys
    const allKeys = Object.keys(rows[0]).filter(k=>k!="_health" && k!="red_cols" && k!="yellow_cols")
    const head = document.getElementById("table-head")
    const body = document.getElementById("table-body")
    head.innerHTML = `<tr>${allKeys.map(k => `<th>${k}</th>`).join("")}</tr>`
    body.innerHTML = ""
    
    const TOT_COLS = new Set(STATUS_COLS.concat(FREE_TEXT_COLS))

    rows.forEach(row => {
        const tr = document.createElement("tr")
        tr.className = "clickable"
        tr.onclick = () => openPanel(row)
        const fullyGreen=isFullyGreen(row)
        if(fullyGreen) tr.style.backgroundColor="#7bff8f"
        allKeys.forEach(key => {
            const td = document.createElement("td")
            const val = row[key]
            if (row.red_cols && row.red_cols.includes(key)) {
                td.style.backgroundColor = "#fd5a5a"
            }
            if(row.yellow_cols && row.yellow_cols.includes(key)){
                td.style.backgroundColor="#ffed69"
            }
            const display = (val == null || val === "") ? "—" : val
            td.textContent = TOT_COLS.has(key) ? toTitleCase(String(display)) : display

            tr.appendChild(td)
        })

        body.appendChild(tr)
    })
}

function renderAlerts(alerts){

    const alertsBody = document.getElementById("project-alerts-body")
    const alertCount = document.getElementById("projects-alert-count")

    alertsBody.innerHTML = ""

    if (alerts.length === 0){
        alertCount.textContent = ""
        alertsBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#888;padding:16px">No overdue items</td></tr>`
        return
    }

    alertCount.textContent = `(${alerts.length})`

    const keys = Object.keys(alerts[0]).filter(k => k !== "project_id")

    alerts.forEach(a => {

        const tr = document.createElement("tr")
        tr.className = "clickable"
        tr.onclick = () => openPanelById(a.project_id)

        keys.forEach(k => {

            const td = document.createElement("td")
            const alertVal = a[k]

            td.textContent =
                (alertVal == null || alertVal === "")
                ? "—"
                : alertVal

            tr.appendChild(td)
        })

        alertsBody.appendChild(tr)
    })
}

function renderDueToday(dues){
    const duesBody = document.getElementById("project-today-body")
    const dueCount = document.getElementById("project-due-today")

    duesBody.innerHTML = ""

    if (dues.length === 0){
        dueCount.textContent = ""
        duesBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#888;padding:16px">No tasks due today</td></tr>`
        return
    }

    dueCount.textContent = `(${dues.length})`

    const keys = Object.keys(dues[0]).filter(k => k !== "project_id")

    dues.forEach(d => {

        const tr = document.createElement("tr")
        tr.className = "clickable"
        tr.onclick = () => openPanelById(d.project_id)

        keys.forEach(k => {

            const td = document.createElement("td")
            const dueVal = d[k]

            td.textContent =
                (dueVal == null || dueVal === "")
                ? "—"
                : dueVal

            tr.appendChild(td)
        })

        duesBody.appendChild(tr)
    })
}


// function badgeClass(val) {
//     if (GREEN_VALUES.includes(val))  return "badge-green"
//     if (YELLOW_VALUES.includes(val)) return "badge-yellow"
//     if (RED_VALUES.includes(val))    return "badge-red"
//     return "badge-gray"
// }

async function openPanel(row) {
    currentRowId = row.id
    document.getElementById("panel-title").textContent =
        `${row.project_name} — ${row.packaging_type} — ${row.packaging_option}`

    // fetch status and deadlines
    const [statusRes, deadlineRes] = await Promise.all([
        fetch(`/growth/api/status/${row.id}`),
        fetch(`/growth/api/deadlines/${row.id}`)
    ])
    const statusData = await statusRes.json()
    const deadlineData = await deadlineRes.json()

    // build lookup maps
    const statusMap = {}
    const completionMap = {}
    statusData.forEach(s => {
        statusMap[s.column_name] = s.current_value ? s.current_value.trim() : ""
        completionMap[s.column_name] = s.completion_date ?? ""
    })
    const deadlineMap = {}
    deadlineData.forEach(d => deadlineMap[d.column_name] = d.deadline)

    const today = new Date().toISOString().split("T")[0]

    let html =`<div class="section-title">Status & Deadlines</div>`

    const TOT_COLS=STATUS_COLS.concat(FREE_TEXT_COLS)
    TOT_COLS.forEach(col => {
        const currentVal = statusMap[col] ?? ""
        const deadline = deadlineMap[col] ?? ""
        let submittedOnTime=true;
        let hint = ""
        if (completionMap[col]) {
            const completedOnTime = deadline ? completionMap[col] <= deadline : true
            if (completedOnTime) {
                hint = `<div class="on-time">✓ Completed on time — ${completionMap[col]}</div>`
            } else {
                hint = `<div class="overdue">⚠ Completed late — ${completionMap[col]} (deadline was ${deadline})</div>`
            }
        } else if (deadline && today > deadline) {
            hint = `<div class="overdue">⚠ Overdue — deadline was ${deadline}</div>`
        }
        else if(deadline && deadline==today){
            hint = `<div class="overdue">➜ To be completed today</div>`
        }

        if (STATUS_COLS.includes(col)){
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
                ${hint}
            </div>`
        }
        else if(col==="Project Status"){
            html += `<div class="field-group">
                <div class="field-label">${col}</div>
                <input type="text" id="status_${col}" value="${currentVal}" 
                    style="width:100%;padding:8px 10px;border:1px solid #e0e0e0;border-radius:6px;font-size:13px">
                <input type="date" id="deadline_${col}" value="${deadline}" style="margin-top:6px">
                ${hint}
            </div>`
        }
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
    const TOT_COLS = STATUS_COLS.concat(FREE_TEXT_COLS)
    TOT_COLS.forEach(col => {
        const statusEl = document.getElementById(`status_${col}`)
        const deadlineEl = document.getElementById(`deadline_${col}`)
        if (statusEl) statusUpdates[col] = statusEl.value
        if (deadlineEl) deadlineUpdates[col] = deadlineEl.value
    })

    await Promise.all([
        fetch(`/growth/api/status/${currentRowId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(statusUpdates)
        }),
        fetch(`/growth/api/deadlines/${currentRowId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(deadlineUpdates)
        })
    ])

    closePanel()

    // refresh table
    const activeProject = document.querySelector(".project-item.active")
    if (activeProject) {
        const res = await fetch(`/growth/api/projects/${encodeURIComponent(activeProject.textContent)}`)
        const rows = await res.json()
        const alertsRes = await fetch(`/growth/api/alerts/${encodeURIComponent(activeProject.textContent)}`)
        const alerts=await alertsRes.json()
        const duesRes = await fetch(`/growth/api/due-today/${encodeURIComponent(activeProject.textContent)}`)
        const dues=await duesRes.json()
        renderTable(rows)
        renderAlerts(alerts)
        renderDueToday(dues)
    }

    await loadAlerts();
    await loadDueToday();//to load the due today and alerts tab on saving because there can be changes
}


function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"))
    document.getElementById("tab-tracker").style.display = "none"
    document.getElementById("tab-alerts").style.display = "none"
    document.getElementById("add-project-tab").style.display = "none"
    document.getElementById("download-excel-tab").style.display="none"
    document.getElementById("due-today-tab").style.display = "none"
    document.getElementById("import-excel-tab").style.display = "none"
    document.getElementById("project-alerts").style.display="none"
    document.getElementById("project-alerts-table").style.display="none"
    document.getElementById("project-today").style.display="none"
    document.getElementById("project-today-table").style.display="none"


    if (tab === "tracker") {
        document.getElementById("tab-tracker").style.display = "flex"
        document.querySelector(".tab-btn:first-child").classList.add("active")
        const hasProject = document.querySelector(".project-item.active")
        if (hasProject) {
            document.getElementById("project-alerts").style.display = "flex"
            document.getElementById("project-alerts-table").style.display = "table"
            document.getElementById("project-today").style.display = "flex"
            document.getElementById("project-today-table").style.display = "table"
        }//only display if a project is active
    } 
    else if(tab=="add-project-tab") {
        document.getElementById("add-project-tab").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(2)").classList.add("active")
    }
    else if(tab==="download-excel-tab"){
        document.getElementById("download-excel-tab").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(3)").classList.add("active")
    }
    else if(tab=="alerts") {
        document.getElementById("tab-alerts").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(4)").classList.add("active")
        loadAlerts()
    } 
    else if (tab === "due-today-tab") {
        document.getElementById("due-today-tab").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(5)").classList.add("active")
        loadDueToday()
    }
    else if (tab === "import-excel-tab") {
        document.getElementById("import-excel-tab").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(6)").classList.add("active")
    }
}

async function loadAlerts() {
    const res = await fetch("/growth/api/alerts")
    const alerts = await res.json()
    const body = document.getElementById("alerts-body")
    const overdueCount = document.getElementById("overdue-count")
    const overdueCountBtn = document.getElementById("overdue-count-btn")
    overdueCount.textContent = alerts.length > 0 ? `(${alerts.length})` : ""
    overdueCountBtn.textContent = alerts.length > 0 ? `(${alerts.length})` : ""

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
                <td>${(a.current_value==null || a.current_value==="") ? "—":a.current_value}</td>
                <td style="color:#791F1F;font-weight:500">${a.deadline}</td>
            </tr>
        `).join("")
}

async function openPanelById(projectId) {
    const res = await fetch(`/growth/api/projects/id/${projectId}`)
    const row = await res.json()
    openPanel(row)
}

async function addProject(){
    const nameInput = document.getElementById("new-project-name")    
    const typeInput = document.getElementById("new-packaging-type")
    const optionInput = document.getElementById("new-packaging-option")
    const today = new Date().toISOString().split("T")[0]
    const name = nameInput.value    
    const packagingType = typeInput.value
    const packagingOption = optionInput.value

    if(!name || !packagingType || !packagingOption){
        alert("Please fill all the fields")
        return
    }

    const res = await fetch("/growth/api/projects", { // Added leading absolute slash
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            project_name: name,
            packaging_type: packagingType,
            packaging_option: packagingOption
        })
    })

    if(res.ok) {
        alert("Project added successfully!")
        nameInput.value = ""
        typeInput.value = ""
        optionInput.value = ""

        await loadProjects()

        switchTab('tracker')
    } else {
        alert("Server error occurred while adding project.")
    }
}

async function deleteProject(){
    
    // Add a confirmation fallback so users don't drop rows by mistake
    const confirmDelete = confirm("Are you sure you want to delete this packaging component row? This cannot be undone.")
    if (!confirmDelete) return

    //Delete the current project
    const res = await fetch(`/growth/api/projects/${currentRowId}`, { 
        method: "DELETE" 
    })
    
    if(res.ok){
        alert("Project component successfully deleted")
        closePanel()
        
        //loadProjects - changes the left panel
        await loadProjects()
        const activeProject = document.querySelector(".project-item.active")
        //if there is still an active project under the same name then display it in the center grid else clear the grid and display "Select Project"
        if (activeProject) {
            const refreshRes = await fetch(`/growth/api/projects/${encodeURIComponent(activeProject.textContent)}`)
            //to get active projects
            const rows = await refreshRes.json()
            const alertsRes = await fetch(`/growth/api/alerts/${encodeURIComponent(activeProject.textContent)}`)
            const alerts=await alertsRes.json()
            const duesRes = await fetch(`/growth/api/due-today/${encodeURIComponent(activeProject.textContent)}`)
            const dues=await duesRes.json()
            renderTable(rows)
            renderAlerts(alerts)
            renderDueToday(dues)
        } else {
            document.getElementById("table-head").innerHTML = ""
            document.getElementById("table-body").innerHTML = ""
            document.getElementById("selected-project-name").textContent = "Select a project"
        }
        //load the left panel again to reflect changes (also the alerts and duetoday)
        await loadAlerts()
        await loadDueToday()
    }
    else{
        alert("Server error occurred while deleting project")
    }
}


async function downloadExcel(){
    const nameIp = document.getElementById("file-name");
    const fileName = nameIp.value;

    if(!fileName){
        alert("Please enter a file name")
        return
    }

    const res = await fetch(`/growth/api/download/${encodeURIComponent(fileName)}`);

    if(res.ok){

        // converts response to blob - immutable file object
        const blob = await res.blob();

        // Save as dialog for compatible browsers
        if (window.showSaveFilePicker) {
            const handle = await window.showSaveFilePicker({
                suggestedName: `${fileName}.xlsx`,
                types: [{
                    description: "Excel File",
                    accept: {
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"]
                    }
                }]
            });

            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();

            alert("File saved successfully!");
        }

       //alternative for incompatible browsers
        else {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${fileName}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            alert("File downloaded successfully! Check your downloads folder");
        }

    }
    else{
        alert("Server error in downloading file. Please try again")
    }
    switchTab('tracker')
}

async function importExcel() {
    const fileInput = document.getElementById("import-file")
    const file = fileInput.files[0]

    if (!file) {
        alert("Please select an Excel file first")
        return
    }
    const confirmed = confirm(`Import "${file.name}" into the tracker? This will add all rows from the file.`)
    if (!confirmed) return

    const formData = new FormData()
    formData.append("file", file)

    const res = await fetch("/growth/api/import", {
        method: "POST",
        body: formData
    })

    if (res.ok) {
        const result = await res.json()
        alert(`Import successful! ${result.rows_imported} rows added.`)
        fileInput.value = ""
        await loadProjects()
        switchTab("tracker")
    } else {
        const err = await res.json()
        alert(`Import failed: ${err.detail ?? "Server error"}`)
    }
}

async function loadDueToday() {
    const res = await fetch("/growth/api/due-today")
    const items = await res.json()

    const body = document.getElementById("due-today-body")
    const count = document.getElementById("due-today-count")
    const countBtn = document.getElementById("due-today-count-btn")
    
    if (items.length === 0) {
        count.textContent = ""
        countBtn.textContent=""
        body.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#888;padding:24px">No tasks due today</td></tr>`
        return
    }

    count.textContent = `(${items.length})`
    countBtn.textContent = `(${items.length})`
    body.innerHTML = items.map(a => `
        <tr class="clickable" onclick="openPanelById(${a.project_id})">
            <td>${a.project_name}</td>
            <td>${a.packaging_type}</td>
            <td>${a.packaging_option}</td>
            <td>${a.column_name}</td>
            <td>${(a.current_value==null || a.current_value==="") ? "—":a.current_value}</td>
            <td style="color:#633806;font-weight:500">${a.deadline}</td>
        </tr>
    `).join("")
    // (val == null || val === "") ? "—" : val
}

const logout = async () => {
    const log=await fetch('/auth/logout',{credentials:'include'})
    if(log.ok){
      const logRes= await log.json();
      window.location.assign("/")
    }
    else{
      const errData = await log.json();
      alert(`Error: ${errData.detail || "Failed to logout."}`);
    }
}

const switchTracker = async (tracker) => {
    const trackerChooser=document.getElementById("trackers")
    trackerChooser.value=tracker;
    if(tracker!="admin/summary") window.location.assign(`/${tracker}`)
    else{
        const res = await fetch(`/${tracker}`, { credentials: "include" });
        if (!res.ok) {
            alert("Permission denied.");
            return;
        }
        if (res.status === 307 || res.status === 401) {
            alert("No user logged in.");
            window.location.assign("/");
            return;
        }
        window.location.assign("/admin")
    }
}

loadProjects()
loadAlerts()
loadDueToday()