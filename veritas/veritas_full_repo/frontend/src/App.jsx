import { BrowserRouter } from "react-router-dom";

import LoginGate from "./components/LoginGate.jsx";
import VeritasApp from "./VeritasProduct.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <LoginGate>
        {({ currentUser, onLogout }) => (
          <VeritasApp currentUser={currentUser} onLogout={onLogout} />
        )}
      </LoginGate>
    </BrowserRouter>
  );
}
