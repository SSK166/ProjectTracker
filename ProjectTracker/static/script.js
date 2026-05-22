const STATUS_COLS = [
    "KLD Status",
    "Artwork Status", 
    "Artwork to Vendor Status",
    "Artwork to Vendor Status 2",
    "Dispatch Status",
    "Cost Closure Status",
    "Project Status",
    "Connectivity Status",
    "PDF Approved",
    "Dimensions", //because only status cols are rendered on the side panel
    "Code Creation", 
    "Specification", 
    "BOM", 
    "SOP"
]

const FREE_TEXT_COLS = ["Dimensions", "Code Creation", "Specification", "BOM", "SOP"]

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

    "Artwork to Vendor Status":[
        "Delayed",
        "Correction",
        "Dispatched"
    ],
    "Artwork to Vendor Status 2":[
        "Delayed",
        "Correction",
        "Dispatched"
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
    // console.log(`Rows:${JSON.stringify(rows)}`)
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
    console.log(`Keys: ${allKeys.toString()}`)
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
        if(col==="Artwork to Vendor Status 2"){
            console.log(`Processing ${statusMap[col]} with deadline ${deadlineMap[col]}`)
        }
        const currentVal = statusMap[col] ?? ""
        const deadline = deadlineMap[col] ?? ""

        if (FREE_TEXT_COLS.includes(col)) {
            // render as text input, no deadline picker
            html += `<div class="field-group">
                <div class="field-label">${col}</div>
                <input type="text" id="status_${col}" value="${currentVal}" 
                    style="width:100%;padding:8px 10px;border:1px solid #e0e0e0;border-radius:6px;font-size:13px">
            </div>`
            return
        }
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


function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"))
    document.getElementById("tab-tracker").style.display = "none"
    document.getElementById("tab-alerts").style.display = "none"
    document.getElementById("add-project-tab").style.display = "none"
    document.getElementById("download-excel-tab").style.display="none"


    if (tab === "tracker") {
        document.getElementById("tab-tracker").style.display = "flex"
        document.querySelector(".tab-btn:first-child").classList.add("active")
    } else if(tab=="alerts") {
        document.getElementById("tab-alerts").style.display = "flex"
        document.querySelector(".tab-btn:last-child").classList.add("active")
        loadAlerts()
    } else if(tab=="add-project-tab") {
        document.getElementById("add-project-tab").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(2)").classList.add("active")
    }
    else if(tab==="download-excel-tab"){
        document.getElementById("download-excel-tab").style.display = "flex"
        document.querySelector(".tab-btn:nth-child(3)").classList.add("active")
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
    const overdueCount=document.getElementById("overdue-count")
    overdueCount.textContent=`(${alerts.length})`
    const overdueCountBtn=document.getElementById("overdue-count-btn")
    overdueCountBtn.textContent=`(${alerts.length})`
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

async function addProject(){
    const nameInput = document.getElementById("new-project-name")    
    const typeInput = document.getElementById("new-packaging-type")
    const optionInput = document.getElementById("new-packaging-option")

    const name = nameInput.value    
    const packagingType = typeInput.value
    const packagingOption = optionInput.value

    if(!name || !packagingType || !packagingOption){
        alert("Please fill all the fields")
        return
    }

    const res = await fetch("/api/projects", { // Added leading absolute slash
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
    console.log(`Project ID:${currentRowId}`)
    
    // Add a confirmation fallback so users don't drop rows by mistake
    const confirmDelete = confirm("Are you sure you want to delete this packaging component row? This cannot be undone.")
    if (!confirmDelete) return

    //Delete the current project
    const res = await fetch(`/api/projects/${currentRowId}`, { 
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
            const refreshRes = await fetch(`/api/projects/${encodeURIComponent(activeProject.textContent)}`)
            //to get active projects
            const rows = await refreshRes.json()
            renderTable(rows)
        } else {
            document.getElementById("table-head").innerHTML = ""
            document.getElementById("table-body").innerHTML = ""
            document.getElementById("selected-project-name").textContent = "Select a project"
        }
        //load the left panel again to reflect changes
        await loadAlerts()
    }
    else{
        alert("Server error occurred while deleting project")
    }
}


async function downloadExcel(){
    const nameIp = document.getElementById("file-name");
    console.log(nameIp.value)
    const fileName = nameIp.value;

    if(!fileName){
        alert("Please enter a file name")
        return
    }

    const res = await fetch(`api/download/${encodeURIComponent(fileName)}`);

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

loadProjects()
loadAlerts()