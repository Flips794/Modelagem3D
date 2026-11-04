import './App.css';

import { HeaderPage } from './pages/headerpage/HeaderPage';
import { LeftPage } from './pages/leftpage/LeftPage';
import { Page2D } from './pages/2dpage/2dpage';
import { Page3D } from './pages/3dpage/3dpage';
import { ThreeLeftPage } from './pages/3leftpage/3Leftpage';

function App() {
  return (
    <div className="workbench-layout">
      <header className="layout-header">
        <HeaderPage />
      </header>

      <aside className="layout-left">
        <LeftPage />
      </aside>

      <main className="layout-main2d">
        <Page2D />
      </main>

      <aside className="layout-left3d">
        <ThreeLeftPage />
      </aside>

      <section className="layout-main3d">
        <Page3D />
      </section>
    </div>
  );
}

export default App;

