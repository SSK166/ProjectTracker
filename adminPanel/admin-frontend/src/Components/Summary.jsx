import { useEffect, useState } from "react";
import {NavLink } from "react-router-dom";
import "../../../static/style.css"; 

export default function Summary() {
    const [summary, setSummary] = useState({});
    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const summaryRes = await fetch('/admin/summary', { credentials: "include" });
                const summaryData = await summaryRes.json();
                setSummary(summaryData);
            } catch (error) {
                console.error("Error fetching summary:", error);
            }
        }
        fetchSummary();
    }, []);

    // Clean loading shell leveraging external CSS
    if (!summary.trackers) {
        return (
            <div className="loading-container">
                <p>Querying upstream data infrastructure cluster status...</p>
            </div>
        );
    }

    return (
        <div className="admin-workspace">
            <div className="dashboard-container">
                
                {/* Clean Header Area */}
                <header className="dashboard-header">
                    <h2>Central Summary Tracker</h2>
                    <p>Metrics from Cross Monitoring of Different Trackers.</p>
                </header>

                {/* Grid Mapping Engine */}
                <div className="tracker-grid">
                    {Object.keys(summary.trackers).map((trackerKey, id) => {
                        console.log(`Tracker Key: ${trackerKey}`)
                        const tracker = summary.trackers[trackerKey];
                        const hasAlerts = tracker.alerts > 0;
                        const hasDueToday=tracker["due_today"]>0;
                        const hasCompletedToday=tracker["completed_today"]>0;

                        return (
                            <NavLink to={`/detailed/${trackerKey}`} 
                                key={id} 
                                style={{ textDecoration: 'none', color: 'inherit' }}>
                                <div className="metric-card">
                                    <h3>{tracker.name}</h3>
                                    
                                    <div className="metric-row">
                                        <span className="metric-label">Total Tasks</span>
                                        <span className="metric-value">{tracker.total}</span>
                                    </div>

                                    <div className="metric-row">
                                        <span className="metric-label">Overdue</span>
                                        {hasAlerts ? (
                                            <span className="badge alert">{tracker.alerts} Overdue</span>
                                        ) : (
                                            <span className="badge nominal">No Alerts</span>
                                        )}
                                    </div>
                                    <div className="metric-row">
                                        <span className="metric-label">Due Today</span>
                                        {hasDueToday ? (
                                            <span className="badge alert">{tracker["due_today"]} Due Today</span>
                                        ) : (
                                            <span className="badge nominal">No Due Today</span>
                                        )}
                                    </div>
                                    <div className="metric-row">
                                        <span className="metric-label">Completed Today</span>
                                        {hasCompletedToday ? (
                                            <span className="badge nominal">{tracker["completed_today"]} Completed Today</span>                                        
                                        ) : (
                                            <span className="badge normal">0 Completed Today</span>
                                        )}
                                    </div>
                                </div>
                            </NavLink>
                        );
                    })}
                </div>

            </div>
        </div>
    );
}