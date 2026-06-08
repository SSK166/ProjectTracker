import { useState } from 'react';
import '../../../static/style.css'

export default function RemoveUsers() {
    const [username, setUsername] = useState("");

    const remove = async (targetUser) => {
        if (!targetUser.trim()) {
            alert("Please fill out the username field.");
            return;
        }

        const proceed = confirm(`Do you want to delete the user ${targetUser.trim()}?`);
        if (!proceed) return; 

        try {
            const payload = new FormData();
            payload.append("username", targetUser.trim());

            const deleteRes = await fetch('http://127.0.0.1:8000/admin/user', { 
                method: "DELETE",
                credentials: "include",
                body: payload 
            });

            if (deleteRes.ok) {
                alert("User deleted successfully!");
                setUsername("");
            } else {
                const errData = await deleteRes.json();
                alert(`Error: ${errData.detail || "Failed to delete user."}`);
            }

        } catch (error) {
            console.error("Network Error :", error);
            alert("Permission Denied.");
        }
    }

    return (
        <div className="panel-form-card">
            <h3>Delete User</h3>
            
            <div className="field-group">
                <label htmlFor="uname" className="field-label">Username</label>
                <input 
                    type="text" 
                    id="uname"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)} 
                    placeholder="Username"
                />
            </div>

            <button 
                type="button"
                className="auth-btn" 
                onClick={() => remove(username)}
            >
                Remove User
            </button>
        </div>
    );
}