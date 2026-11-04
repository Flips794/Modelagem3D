# Tabela de treino da IA micelar

Este pacote cria a tabela PostgreSQL:

```txt
micelium_ai_training_samples
```

Ela guarda amostras para treino/validação da IA de CMC, HLB, HLB efetivo, CPP e morfologia preferencial.

## Criar tabela e inserir dados iniciais

```powershell
cd D:\1projetos\Modelagem3D\backend
python -m app.modules.micelium.IA.training.create_ai_training_table
```

## Conferir dados

```powershell
python -m app.modules.micelium.IA.training.check_ai_training_table
```

## Conferir no DBeaver

```sql
SELECT
  common_name,
  surfactant_class,
  solvent,
  temperature_k,
  cmc_mmol_l,
  quality_status,
  confidence_score
FROM micelium_ai_training_samples
ORDER BY surfactant_class, common_name;
```

## Observação importante

Alguns valores foram marcados como `needs_review`, principalmente Tween 80, DDAB e AOT, porque:
- Tween 80 é mistura comercial/polidispersa.
- DDAB e AOT dependem muito de pureza, solvente, sal e método.
- Antes de treino real definitivo, esses registros devem ser revisados com fonte experimental específica.

Use inicialmente apenas `quality_status = 'approved'` para treino mais seguro.


