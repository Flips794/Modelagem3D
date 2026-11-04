import React from 'react';

import './app.css';

import { HeaderPage } from '../pages/headerpage/HeaderPage';
import { LeftPage } from '../pages/leftpage/LeftPage';
import { Page2D } from '../pages/2dpage/2dpage';
import { Page3D } from '../pages/3dpage/3dpage';
import { ThreeLeftPage } from '../pages/3leftpage/3Leftpage';


type WorkbenchErrorBoundaryProps = {
  area: string;
  children: React.ReactNode;
};

type WorkbenchErrorBoundaryState = {
  hasError: boolean;
  message: string;
};

class WorkbenchErrorBoundary extends React.Component<
  WorkbenchErrorBoundaryProps,
  WorkbenchErrorBoundaryState
> {
  state: WorkbenchErrorBoundaryState = {
    hasError: false,
    message: "",
  };

  static getDerivedStateFromError(error: unknown): WorkbenchErrorBoundaryState {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : String(error),
    };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    console.error(`[Modelagem3D] Falha no bloco ${this.props.area}:`, error, info);
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div
        style={{
          minHeight: "100%",
          display: "grid",
          placeItems: "center",
          padding: "18px",
          color: "#e5e7eb",
          background:
            "radial-gradient(circle at center, rgba(248, 113, 113, 0.12), transparent 42%), rgba(15, 23, 42, 0.88)",
          border: "1px solid rgba(248, 113, 113, 0.28)",
          borderRadius: "18px",
          fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        <div style={{ display: "grid", gap: "8px", textAlign: "center", maxWidth: "520px" }}>
          <strong style={{ color: "#fecaca" }}>
            Erro controlado no bloco: {this.props.area}
          </strong>
          <span style={{ color: "#cbd5e1", fontSize: "0.82rem", lineHeight: 1.5 }}>
            A tela inteira foi preservada. Use Ctrl + F5 depois de aplicar a correção.
          </span>
          <code
            style={{
              whiteSpace: "pre-wrap",
              color: "#fca5a5",
              fontSize: "0.75rem",
              background: "rgba(15, 23, 42, 0.95)",
              borderRadius: "10px",
              padding: "10px",
            }}
          >
            {this.state.message}
          </code>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, message: "" })}
            style={{
              justifySelf: "center",
              border: "1px solid rgba(125, 211, 252, 0.35)",
              borderRadius: "999px",
              padding: "8px 14px",
              background: "rgba(14, 165, 233, 0.18)",
              color: "#e0f2fe",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Tentar renderizar novamente
          </button>
        </div>
      </div>
    );
  }
}


export function App() {
  return (
    <div className="workbench-layout">
      <header className="layout-header">
        <WorkbenchErrorBoundary area="Cabeçalho">
          <HeaderPage />
        </WorkbenchErrorBoundary>
      </header>

      <aside className="layout-left">
        <section className="layout-left-primary" aria-label="Molécula isolada">
          <WorkbenchErrorBoundary area="Painel 2D esquerdo">
            <LeftPage />
          </WorkbenchErrorBoundary>
        </section>

        <section className="layout-left-secondary" aria-label="Conjunto de moléculas">
          <WorkbenchErrorBoundary area="Painel de mistura 3D">
            <ThreeLeftPage />
          </WorkbenchErrorBoundary>
        </section>
      </aside>

      <main className="layout-main2d">
        <WorkbenchErrorBoundary area="Editor 2D">
          <Page2D />
        </WorkbenchErrorBoundary>
      </main>

      <section className="layout-main3d" aria-label="Ambiente 3D molecular">
        <WorkbenchErrorBoundary area="Ambiente 3D">
          <Page3D />
        </WorkbenchErrorBoundary>
      </section>
    </div>
  );
}

export default App;


