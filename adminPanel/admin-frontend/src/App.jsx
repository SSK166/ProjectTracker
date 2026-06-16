import { BrowserRouter, Route, Routes, NavLink } from 'react-router-dom';
import Summary from './Components/Summary';
import SwitchRoles from './Components/SwitchRoles';
import TrackerDetail from './Components/TrackerDetail';
import RemoveUsers from './Components/RemoveUsers';

function App() {
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      //  Handle expired/missing sessions (307 Redirects)
      if (response.url && response.url.includes('msg=')) {
          const urlObj = new URL(response.url);
          window.location.href = `/${urlObj.search}`;
          return response;
      }
      // Handle insufficient permissions (403 Forbidden)
      if (response.status === 403) {
          // Automatically throw them back to the landing page with a clear notice
          window.location.href = '/?msg=Access+Denied:+Administrator+privileges+required.';
          return response;
      }
      return response;
  };
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

  return (
    <BrowserRouter basename="/admin">
      <nav className="nav-container">
        <NavLink to='/' className={({ isActive }) => isActive ? "active-tab" : "normal-tab"}>Home Summary</NavLink>
        <NavLink to='/switch' className={({ isActive }) => isActive ? "active-tab" : "normal-tab"}>Switch Roles</NavLink>
        <NavLink to='/remove' className={({ isActive }) => isActive ? "active-tab" : "normal-tab"}>Remove Users</NavLink>
        <NavLink onClick = {logout} className="logout-btn">Logout</NavLink>
      </nav>
      <Routes>
        <Route path='/' element={<Summary/>}/>
        <Route path='/switch' element={<SwitchRoles/>}/>
        <Route path='/remove' element={<RemoveUsers/>}/>
        <Route path='/detailed/:trackerId' element={<TrackerDetail/>}/>
      </Routes>
    </BrowserRouter>
  )
}
export default App