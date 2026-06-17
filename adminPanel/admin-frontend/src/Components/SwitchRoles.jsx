import { useState,useEffect } from 'react';

export default function SwitchRoles() {
    const [username, setUsername] = useState("");
    const [newRole, setNewRole] = useState("");
    const [users,setUsers] = useState([]);
    const getAllUsers = async () => {
        try {
            const userRes = await fetch('/admin/all-users', { credentials: 'include' });
            if (userRes.ok) {
                const userData = await userRes.json();
                setUsers(userData.users); // backend returns {status, users}, so unwrap it
            } else {
                const errData = await userRes.json();
                alert(`Error: ${errData.detail || "Failed to fetch users."}`);
            }
        } catch (error) {
            console.error("Network Error :", error);
            alert("Permission Denied.");
        }
    };
 
    useEffect(() => {
        getAllUsers();
    }, []);

    const updateRoles = async (targetUser, targetRole) => {
        if (!targetUser.trim() || !targetRole.trim()) {
            alert("Please fill out both the username and target role fields.");
            return;
        }

        if (!["admin", "user", "manager12", "manager34"].includes(targetRole.trim())) {
            alert("Please select a valid role.");
            return;
        }

        const proceed = confirm(`Do you want to update the role for the user "${targetUser}" to "${targetRole}"?`);
        if (!proceed) return; 

        try {
            const payload = new FormData();
            payload.append("username", targetUser.trim());
            payload.append("role", targetRole.trim());

            const updateRes = await fetch('/admin/role', { 
                method: "PUT",
                credentials: "include",
                body: payload 
            });

            if (updateRes.ok) {
                alert("Role updated successfully!");
                setUsername("");
                setNewRole("");
            } else {
                const errData = await updateRes.json();
                alert(`Error: ${errData.detail || "Failed to update role."}`);
            }

        } catch (error) {
            console.error("Network Error :", error);
            alert("Permission Denied.");
        }
    }

     return (
        <div className="panel-form-card">
            <h3>Switch Roles</h3>
 
            <div className="field-group">
                <label htmlFor="uname" className="field-label">Username</label>
                <select
                    id="uname"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                >
                    <option value="" disabled>-- Select User --</option>
                    {users.map((u) => (
                        <option key={u.name} value={u.name}>
                            {u.name}
                        </option>
                    ))}
                </select>
            </div>
 
            <div className="field-group">
                <label htmlFor="newrole" className="field-label">New Role</label>
                <select
                    id="newrole"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                >
                    <option value="" disabled>-- Select Target Role --</option>
                    <option value="user">User</option>
                    <option value="manager12">Manager 1 & 2</option>
                    <option value="manager34">Manager 3 & 4</option>
                    <option value="admin">Admin</option>
                </select>
            </div>
 
            <button
                type="button"
                className="auth-btn"
                onClick={() => updateRoles(username, newRole)}
            >
                Update Role
            </button>
        </div>
    );
}