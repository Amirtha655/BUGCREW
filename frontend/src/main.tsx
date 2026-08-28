import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import "./index.css";
import App from "./App";
import { SystemProvider } from "./state/SystemProvider";

import Overview from "./pages/Overview";
import Markets from "./pages/Markets";
import Agents from "./pages/Agents";
import Portfolio from "./pages/Portfolio";
import Risk from "./pages/Risk";
import Decisions from "./pages/Decisions";
import Execution from "./pages/Execution";
import Adaptation from "./pages/Adaptation";
import Activity from "./pages/Activity";
import Settings from "./pages/Settings";

const router = createHashRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Overview /> },
      { path: "markets", element: <Markets /> },
      { path: "agents", element: <Agents /> },
      { path: "portfolio", element: <Portfolio /> },
      { path: "risk", element: <Risk /> },
      { path: "decisions", element: <Decisions /> },
      { path: "execution", element: <Execution /> },
      { path: "adaptation", element: <Adaptation /> },
      { path: "activity", element: <Activity /> },
      { path: "settings", element: <Settings /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SystemProvider>
      <RouterProvider router={router} />
    </SystemProvider>
  </StrictMode>
);
