export function HeaderPage() {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '100%', padding: '0 1.5rem', backgroundColor: 'var(--bg-panel)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <h1 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
          Molecular Micelle Engine
        </h1>
        <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', backgroundColor: 'var(--bg-panel-light)', border: '1px solid var(--border-color)' }}>
          ⌬ Molécula Atual: Não Salva
        </span>
      </div>
      
      <div style={{ display: 'flex', gap: '1rem' }}>
        <button style={{ background: 'transparent', color: 'var(--text-main)', border: '1px solid var(--border-color)', padding: '0.4rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>
          Salvar Projeto
        </button>
        <button style={{ background: 'var(--accent-cyan)', color: '#000', border: 'none', padding: '0.4rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>
          Modo Predição
        </button>
      </div>
    </div>
  );
}

