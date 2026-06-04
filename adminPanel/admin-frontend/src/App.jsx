import { BrowserRouter, Route, Routes, NavLink } from 'react-router-dom';
import Summary from './Components/Summary';
import SwitchRoles from './Components/SwitchRoles';
import Detailed from './Components/TrackerDetail';
import TrackerDetail from './Components/TrackerDetail';
function App() {
  return (
    <BrowserRouter>
      <nav className="nav-container">
        <NavLink to='/' className={({ isActive }) => isActive ? "active-tab" : "normal-tab"}>Home Summary</NavLink>
        <NavLink to='/switch' className={({ isActive }) => isActive ? "active-tab" : "normal-tab"}>Switch Roles</NavLink>
      </nav>
      <Routes>
        <Route path='/' element={<Summary/>}/>
        <Route path='/switch' element={<SwitchRoles/>}/>
        <Route path='/detailed/:trackerId' element={<TrackerDetail/>}/>
      </Routes>
    </BrowserRouter>
  )
}
export default App