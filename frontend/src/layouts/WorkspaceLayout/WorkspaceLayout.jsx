import AppNavigation from "../../components/navigation/AppNavigation";
import "./WorkspaceLayout.css";

function WorkspaceLayout({ title, subtitle, actions, children }) {
  return (
    <div className="workspace-layout">
      <aside className="workspace-layout__sidebar">
        <div className="workspace-layout__brand">
          <span>DG</span>
          <div><strong>AdGen AI</strong><small>Marketing Assistant</small></div>
        </div>
        <AppNavigation />
      </aside>
      <main className="workspace-layout__main">
        <header className="workspace-layout__header">
          <div>
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions && <div className="workspace-layout__actions">{actions}</div>}
        </header>
        <div className="workspace-layout__content">{children}</div>
      </main>
    </div>
  );
}

export default WorkspaceLayout;
