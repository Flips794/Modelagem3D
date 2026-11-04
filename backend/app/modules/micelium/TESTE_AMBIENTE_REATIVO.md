# Testes do ambiente reativo

Rode:

```powershell
cd D:\1projetos\Modelagem3D\backend
python -m app.modules.micelium.dynamic_morphology_smoke_test
```

Casos adicionados:
- SDS em água: meio polar, dielétrica alta, micelização clássica.
- SDS em etanol: cossolvente menos polar, agregação mais frouxa/lenta.
- Micela inversa: meio apolar, dielétrica baixa.
- Cilíndrica/wormlike e lamelar por CPP.

Payloads para Swagger/Postman:
`backend/app/modules/micelium/test_payloads_dynamic_morphologies.json`.

Regra:
- Reagente usa quantidade real em mmol.
- Solvente usa excesso do meio, sem mol/mmol editável.
- pH, dielétrica, polaridade, volume e velocidade são parâmetros do ambiente, não mudam a molécula.


