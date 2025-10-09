## search-classes — busca de salas disponíveis

> Pequeno utilitário Python que gera uma lista de salas disponíveis (JSON + XLSX).

Principais pontos
- Objetivo: executar uma busca/extração e produzir arquivos com salas disponíveis.
- Saída: arquivos gerados na pasta `output/` (ex.: `salas_disponiveis_YYYY-MM-DD_HH-MM-SS.json` / `.xlsx`).

Requisitos
- Python 3.10+ (recomenda-se usar virtualenv).
- Dependências em `requirements.txt`.

Como usar (rápido)
1. Abra um terminal PowerShell e entre na pasta do projeto:

```powershell
cd "c:\Users\gabri\OneDrive\INSPER\Projetos pessoais\search-classes\search_classes"
```

2. Crie/ative um ambiente virtual (opcional, recomendado):

```powershell
python -m venv env; .\env\Scripts\Activate.ps1
```

3. Instale dependências e execute:

```powershell
pip install -r requirements.txt
python main.py
```

Observações
- Os nomes de arquivos de saída incluem timestamp e ficam em `output/`.
- Presumi que o objetivo do projeto é localizar "salas disponíveis" a partir de alguma fonte/scraper — ajuste a descrição caso a finalidade seja diferente.

Contribuições / contato
- Abra uma issue ou PR no repositório.
- Adicione uma licença (`LICENSE`) se desejar permitir uso explícito.

