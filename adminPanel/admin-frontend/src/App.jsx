import { BrowserRouter, Route, Routes, NavLink } from 'react-router-dom';
import Summary from './Components/Summary';
import SwitchRoles from './Components/SwitchRoles';
import TrackerDetail from './Components/TrackerDetail';
import RemoveUsers from './Components/RemoveUsers';

function App() {
  const logout = async () => {
    const log=await fetch('http://127.0.0.1:8000/auth/logout',{credentials:'include'})
    if(log.ok){
      const logRes= await log.json();
      window.location.assign("http://127.0.0.1:8000")
    }
    else{
      const errData = await log.json();
      alert(`Error: ${errData.detail || "Failed to logout."}`);
    }
  }

  return (
    <BrowserRouter>
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