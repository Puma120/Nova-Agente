import { useState } from "react";
import { AppProvider, useApp } from "./context/AppContext";
import AuthScreen from "./components/AuthScreen";
import Sidebar from "./components/Sidebar";
import ChatView from "./components/ChatView";
import DocsPanel from "./components/DocsPanel";
import IntegrationsPanel from "./components/IntegrationsPanel";

function Shell() {
  const { token, setActiveConvId } = useApp();
  const [view, setView] = useState("chat");

  if (!token) return <AuthScreen />;

  const newChat = () => {
    setActiveConvId(null);
    setView("chat");
  };

  return (
    <div className="aurora flex h-screen overflow-hidden">
      <Sidebar view={view} setView={setView} onNewChat={newChat} />
      <main className="flex-1 flex flex-col min-w-0 min-h-0">
        {view === "chat" && <ChatView />}
        {view === "docs" && <DocsPanel />}
        {view === "integrations" && <IntegrationsPanel />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
