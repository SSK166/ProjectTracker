import { useEffect, useState } from "react";
import { useParams, NavLink } from "react-router-dom";
import "../../../static/style.css"; 


export default function TrackerDetail() {
    const { trackerId } = useParams(); 

    const trackerTitles = {
        project_tracker: "project_tracker",
        growth_tracker: "growth_tracker",
        ve_tracker: "ve_tracker"
    };

    const trackerNames = {
        project_tracker: "Project Architecture Tracker",
        growth_tracker: "Business Growth Pipeline",
        ve_tracker: "Value Engineering Optimizations"
    };

    const baseUrls = {
        project_tracker: "http://127.0.0.1:8000/track",
        growth_tracker: "http://127.0.0.1:8000/growth",
        ve_tracker: "http://127.0.0.1:8000/value"
    };

    const title = trackerTitles[trackerId];
    const baseUrl = baseUrls[trackerId];
    const displayTitle = trackerNames[trackerId] || "Unknown Workspace";

    const [overDues, setoverDues] = useState([]); 
    const [dueToday, setDueToday] = useState([]);
    const [upcoming, setUpcoming] = useState([]);
    const [summaryInfo, setSummaryInfo] = useState(null);
    const [worst,setWorst] = useState([]);
    const [completedLast7Days,setcompletedLast7Days] = useState([]);
    const [tasksCompletedToday,setTasksCompletedToday] = useState([]);

    if (!baseUrl) {
        return (
            <div style={{ padding: "40px", textAlign: "center" }}>
                <h3>Error: Invalid tracker context requested.</h3>
                <NavLink to="/" className="normal-tab">Return to Dashboard Summary</NavLink>
            </div>
        );
    }

    // fetching alerts
    useEffect(() => {
        const fetchOverDues = async () => {
            try {
                const alertsRes = await fetch(`${baseUrl}/api/alerts`, { credentials: "include" });
                const alerts = await alertsRes.json();
                setoverDues(alerts);
                setWorst([...alerts]
                .sort((a, b) => a.deadline.localeCompare(b.deadline))
                .slice(0, 5));
            } catch (err) {
                console.error("Error in fetching backlogs:", err);
            }
        };
        fetchOverDues();
    }, [baseUrl]);

    // fetching due todays
    useEffect(() => {
        const fetchDueToday = async () => {
            try {
                const duesRes = await fetch(`${baseUrl}/api/due-today`, { credentials: "include" });
                const dues = await duesRes.json();
                setDueToday(dues);
            } catch (err) {
                console.error("Error in fetching tasks that are due today:", err);
            }
        };
        fetchDueToday();
    }, [baseUrl]);

    // getting count of tasks due in next seven days
    useEffect(() => {
        const fetchUpcoming = async () => {
            try {
                const upcomingRes = await fetch(`http://127.0.0.1:8000/admin/upcoming/${title}`, { credentials: "include" });
                const upcomingSeven = await upcomingRes.json();
                setUpcoming(upcomingSeven);
            } catch (err) {
                console.error("Error in fetching upcoming deadlines:", err);
            }
        };
        fetchUpcoming();
    }, [title]);

    // get summary info for tracker health and stuff
    useEffect(() => {
        const fetchSummaryData = async () => {
            try {
                const summaryRes = await fetch("http://127.0.0.1:8000/admin/summary", { credentials: "include" });
                const summaryData = await summaryRes.json();
                setSummaryInfo(summaryData);
            } catch (err) {
                console.error("Error in connecting to basic summary endpoint:", err);
            }
        };
        fetchSummaryData();
        
    }, [trackerId]);

    // get summary info for tracker health and stuff
    useEffect(() => {
        const fetchcompletedLast7Days = async () => {
            try {
                const compLast7DaysRes = await fetch(`http://127.0.0.1:8000/admin/last-7-days-complete-projects/${title}`, { credentials: "include" });
                const compLast7DaysData = await compLast7DaysRes.json();
                setcompletedLast7Days(compLast7DaysData?compLast7DaysData.tasks:[]);
            } catch (err) {
                console.error("Error in fetching the projects completed in last 7 days:", err);
            }
        };
        fetchcompletedLast7Days();
        
    }, [title]);

    useEffect(() => {
        const fetchTasksCompletedToday = async () => {
            try {
                const compTodayRes = await fetch(`http://127.0.0.1:8000/admin/today-complete-tasks/${title}`, { credentials: "include" });
                const compTodayData = await compTodayRes.json();
                setTasksCompletedToday(compTodayData?compTodayData.tasks:[]);
            } catch (err) {
                console.error("Error in fetching the tasks completed today:", err);
            }
        };
        fetchTasksCompletedToday();
        
    }, [title]);

    const trackerStats = summaryInfo?.trackers?.[trackerId] || {};
    const totalTasks = trackerStats.total || 0;
    const completedTodayCount = trackerStats.completed_today || 0;
    const completedTasks = trackerStats.completed || 0;
    const healthScorePercentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

    return (
        <div className="admin-workspace">
            <div className="dashboard-container detailed-view">

                <NavLink to="/" className="back-link">← Back to central summary</NavLink>

                <header className="dashboard-header">
                    <h2>{displayTitle} — Detailed Summary</h2>
                    <p>Overview of upcoming activities and existing deadlines for {displayTitle}.</p>
                </header>

                <div className="metrics-grid">

                    <div className="panel-form-card metric-card-full">
                        <div className="card-label">Completion Score</div>
                        <div className={`stat-num ${healthScorePercentage > 25 ? "nominal-text" : "alert-text"}`}>
                            {healthScorePercentage}%
                        </div>
                        <div className="stat-sub">Projects Completed</div>
                        <div className="progress-container">
                            <div className="progress-bar-bg">
                                <div
                                    className={`progress-bar-fill ${healthScorePercentage > 25 ? "nominal" : "alert"}`}
                                    style={{ width: `${healthScorePercentage}%` }}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="panel-form-card metric-card-full">
                        <div className="card-label">Overdue tasks</div>
                        <div className="stat-num alert-text">
                            {overDues.length}
                        </div>
                        <div className="stat-sub">
                            {overDues.length <= 1 ? "Task" : "Tasks"} currently overdue
                        </div>
                    </div>

                    <div className="panel-form-card metric-card-full">
                        <div className="card-label">Tasks Completed today</div>
                        <div className="stat-num nominal-text">
                            {completedTodayCount}
                        </div>
                        <div className="stat-sub">Individual tasks finished today</div>
                    </div>

                    <div className="panel-form-card metric-card-full">
                        <div className="card-label">Projects Completed last 7 days</div>
                        <div className="stat-num nominal-text">
                            {completedLast7Days !== null ? completedLast7Days.length : "—"}
                        </div>
                        <div className="stat-sub">
                            {completedLast7Days !== null
                                ? `${completedLast7Days.length === 1 ? "Project" : "Projects"} finished this week`
                                : "Calculating..."}
                        </div>
                        <p className="developer-footnote">
                            Tracks full projects finished over the last week.
                        </p>
                    </div>

                </div>

                <div className="panel-form-card metric-card-full">
                    <div className="card-label">Long overdue tasks</div>
                    <div className="worst-list">
                        {worst.length === 0 ? (
                            <div className="stat-sub">No long overdue tasks</div>
                        ) : (
                            worst.map((w, idx) => (
                                <div className="worst-item" key={idx}>
                                    <div className="worst-item-title">{w.project_name}</div>
                                    <div className="worst-item-meta">
                                        <span>Task: {w.column_name}</span>
                                        <span>Status: {(!w.current_value||w.current_value==="")?"NIL":w.current_value}</span>
                                        <span className="deadline-badge">Due: {w.deadline}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="panel-form-card metric-card-full">
                    <div className="card-label">Tasks Due Today</div>
                    <div className="due-today-list">
                        {dueToday.length === 0 ? (
                            <div className="stat-sub">No tasks due today</div>
                        ) : (
                            dueToday.map((d, idx) => (
                                <div className="due-today-item" key={idx}>
                                    <div className="due-today-item-title">{d.project_name}</div>
                                    <div className="due-today-item-meta">
                                        <span>Task: {d.column_name}</span>
                                        <span>Status: {(!d.current_value||d.current_value==="")?"NIL":d.current_value}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="panel-form-card metric-card-full">
                    <div className="card-label">Upcoming Tasks(for next 7 days)</div>
                    <div className="due-today-list">
                        {upcoming.length === 0 ? (
                            <div className="stat-sub">No Tasks due for next 7 days</div>
                        ) : (
                            upcoming.map((u, idx) => (
                                <div className="due-today-item" key={idx}>
                                    <div className="due-today-item-title">{u.project_name}</div>
                                    <div className="due-today-item-meta">
                                        <span>Task: {u.column_name}</span>
                                        <span>Status: {u.current_value}</span>
                                        <span>Deadline: {u.deadline}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="panel-form-card metric-card-full">
                    <div className="card-label">Projects Completed in Last 7 Days</div>
                    <div className="due-today-list">
                        {completedLast7Days.length === 0 ? (
                            <div className="stat-sub">No Projects Completed in Last 7 Days</div>
                        ) : (
                            completedLast7Days.map((c, idx) => (
                                <div className="due-today-item" key={idx}>
                                    <div className="due-today-item-title">{c.project_name}</div>
                                    <div className="due-today-item-meta">Completion Date: {c.comp_date}</div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="panel-form-card metric-card-full">
                    <div className="card-label">Tasks completed today</div>
                    <div className="due-today-list">
                        {tasksCompletedToday.length === 0 ? (
                            <div className="stat-sub">No Tasks Completed today</div>
                        ) : (
                            tasksCompletedToday.map((c, idx) => (
                                <div className="due-today-item" key={idx}>
                                    <div className="due-today-item-title">{c.project_name}</div>
                                    <div className="due-today-item-meta">
                                        <span>Task: {c.column_name}</span>
                                        <span>Status: {c.current_value}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <button className="cta-btn" onClick={() => window.location.assign(baseUrl)}>
                    Go to Tracker →
                </button>

            </div>
        </div>
    );
}