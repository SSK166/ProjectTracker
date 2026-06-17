import { useState,useEffect } from 'react';

export default function RemoveUsers() {
    const [username, setUsername] = useState("");
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

            const deleteRes = await fetch('/admin/user', { 
                method: "DELETE",
                credentials: "include",
                body: payload 
            });

            if (deleteRes.ok) {
                alert("User deleted successfully!");
                setUsername("");
                getAllUsers();
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