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
    const [sevenComplete, setSevenComplete] = useState(null);
    const [upcoming, setUpcoming] = useState([]);
    const [summaryInfo, setSummaryInfo] = useState(null);
    const [worst,setWorst] = useState([]);

    if (!baseUrl) {
        console.log(trackerId)
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
                .sort((a, b) => b.days_overdue - a.days_overdue)
                .slice(0, 5));
            } catch (err) {
                console.error("Error fetching overdue backlogs:", err);
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
                console.error("Error fetching today's queues:", err);
            }
        };
        fetchDueToday();
    }, [baseUrl]);

    // getting count of tasks completed last seven days
    useEffect(() => {
        const fetchLastSeven = async () => {
            try {
                const lastSevenRes = await fetch(`http://127.0.0.1:8000/admin/7-days-projects/${title}`, { credentials: "include" });
                const lastSeven = await lastSevenRes.json();
                setSevenComplete(lastSeven);
            } catch (err) {
                console.error("Error fetching rolling week streak metrics:", err);
            }
        };
        fetchLastSeven();
    }, [title]);

    // getting count of tasks due in next seven days
    useEffect(() => {
        const fetchUpcoming = async () => {
            try {
                const upcomingRes = await fetch(`http://127.0.0.1:8000/admin/upcoming/${title}`, { credentials: "include" });
                const upcomingSeven = await upcomingRes.json();
                setUpcoming(upcomingSeven);
            } catch (err) {
                console.error("Error fetching forward horizon schedule:", err);
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
                console.error("Error connecting to primary summary register:", err);
            }
        };
        fetchSummaryData();
    }, [trackerId]);

    const trackerStats = summaryInfo?.trackers?.[trackerId] || {};
    const totalTasks = trackerStats.total || 0;
    const completedTodayCount = trackerStats.completed_today || 0;
    const healthScorePercentage = totalTasks > 0 ? Math.round((completedTodayCount / totalTasks) * 100) : 0;

    return (
        <div className="admin-workspace">
            <div className="dashboard-container detailed-view">
                
                {/* <NavLink to="/" className="back-link">← Back to Central Summary</NavLink> */}
                
                <header className="dashboard-header">
                    <h2>{displayTitle} — Detailed Summary</h2>
                    <p>Overview of upcoming activities and existing deadlines for {displayTitle}.</p>
                </header>

                {/* Health Score Component */}
                <div className="panel-form-card metric-card-full">
                    <h3>Overall Tracker Health Score(In number of tasks)</h3>
                    <div className="progress-container">
                        <div className="progress-bar-bg">
                            <div 
                                className={`progress-bar-fill ${healthScorePercentage > 25 ? "nominal" : "alert"}`}
                                style={{ width: `${healthScorePercentage}%` }} 
                            />
                        </div>
                        <span className="progress-percentage">{healthScorePercentage}%</span>
                    </div>
                </div>

                {/* Completed Today Component */}
                <div className="panel-form-card metric-card-full">
                    <h3>Overdue tasks</h3>
                    <div className="stat-highlight alert-text">
                        {overDues.length} {overDues.length<=1?"Task":"Tasks"} Overdue
                    </div>
                </div>

                {/* Completed Today Component */}
                <div className="panel-form-card metric-card-full">
                    <h3>Overdue for long time</h3>
                    <div className="stat-highlight alert-text">
                        {worst.length} {worst.length<=1?"Task":"Tasks"} Overdue
                        <div>
                            {worst.map((w,idx)=>{
                                return(
                                    <div key={idx}>
                                        Project Name: {w.project_name}<br/>
                                        Task : {w.column_name}<br/>
                                        Current Status : {w.current_value}<br/>
                                        Deadline : {w.deadline}
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </div>

                {/* Completed Today Component */}
                <div className="panel-form-card metric-card-full">
                    <h3>Completed Today</h3>
                    <div className="stat-highlight nominal-text">
                        {completedTodayCount} Tasks completed today
                    </div>
                </div>
                

                <div className="panel-form-card metric-card-full">
                    <h3>Projects Completed in Last Seven Days</h3>
                    <div className="stat-highlight nominal-text">
                        {sevenComplete !== null ? (
                            <>
                                {sevenComplete.count} {sevenComplete.count === 1 ? "Project" : "Projects"} finished
                            </>
                        ) : (
                            "Calculating Projects Completed in last seven days"
                        )}
                    </div>
                    <p className="developer-footnote">
                        Tracks the total number of full projects finished over the last week.
                    </p>
                </div>

                <div>
                    <button className="auth-btn" onClick={()=>window.location.assign(baseUrl)}>Go to Tracker</button>
                </div>
                {/* Tables for overDues, dueToday, worstOffenders, and upcoming will mount down here */}

            </div>
        </div>
    );
}